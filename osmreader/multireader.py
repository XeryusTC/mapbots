import array
import logging
import logging.handlers
import multiprocessing as mp
import pygraph.classes.exceptions as graphexc
import queue
import xml.etree.cElementTree as ET
import time

from pygraph.classes.digraph import digraph
from osmreader.elements import Node, Way

logger = logging.getLogger('mapbots.osmreader.multireader')

def _xml_parser(logqueue, conn, filename):
    """Parses XML and puts it in a queue, ran as a subprocess

    Parses the OSM XML and puts the elements in a queue where they can
    be processed by other parts of the program.

    Params:
    logqueue - The queue where log records have to end up in
    conn - Connection where parsed elements end up in so they can be
           handled by the rest of the programs
    filename - The filename of the XML file to parse
    """
    # Use only a QueueHandler for the process that runs this code
    # This prevents the process to writing to the log file while the
    # main process also writes to the log file
    h = logging.handlers.QueueHandler(logqueue)
    root = logging.getLogger('mapbots')
    root.handlers = []
    root.addHandler(h)

    # The logger to use for this process
    logger = logging.getLogger('mapbots.osmreader.multireader._xml_parser')
    logger.info("Starting multiprocess XML parser")

    # Parse the root element of the XML
    try:
        it = ET.iterparse(filename, events=("start", "end"))
    except Exception:
        import traceback
        logger.error("Failed to load the XML file %s\n%s", filename, traceback.format_exc())
        conn.send(None)
        raise
    else:
        event, root = next(it)
        logger.info("Loaded XML file with OSM API version %s", root.attrib['version'])

        for event, elem in it:
            if event == "end":
                if elem.tag in ("bounds", "node", "way"):
                    conn.send(elem)

                root.clear()

    logger.info("Finished parsing XML, exiting parser subprocess")
    conn.send(None)

class MultiReader:
    """Uses multiprocessing to split XML parsing and parsing nodes."""
    def __init__(self, filename=None, *args, handle_log_interval=2,
                 max_elements_handled=10000):
        """Initialises the reader and optionally loads a file.

        Params:
        filename - Name of a file to load, should be a file on a
                   absolute or relative path. If the argument is None
                   (default) then you need to call the load method
                   yourself.
        handle_log_interval - Logs from subprocesses are handled every
                              once in a while. You can set the interval
                              (in seconds) here. Default is every 2
                              seconds.
        max_elements_handled - Amount of XML elements to parse before
                               moving on to other things. Is only
                               applicable when there are always elements
                               in the queue to handle. If the queue is
                               empty then the load function will move on
                               to doing other things.
        """
        self.logger = logging.getLogger('mapbots.osmreader.multireader.MultiReader')
        self.nodes = {}
        self.ways = {}
        self.junctions = array.array('q')
        self.graph = digraph()

        self.max_elements_handled = max_elements_handled

        # Set up logging
        self.logqueue = mp.Queue()
        self.log_interval = handle_log_interval
        self.log_last_handled = 0

        # If there is something in filename argument then load immediately
        if filename is not None:
            self.load(filename)

    def load(self, filename):
        """Parses data from an OSM file and stores it in memory.

        Starts a subprocess that reads the XML and parses. It is then
        passed back through a queue and handled. OSM Data gets stored in
        class members.

        Params:
        filename - The file which holds the OSM XML
        """
        if not isinstance(filename, str):
            raise TypeError("Filename must be the name of a file on an absolute or relative path")
        elif len(filename) == 0:
            raise ValueError("Filename must not be empty")

        # Create and start XML parser subprocess
        receive_conn, send_conn = mp.Pipe(duplex=False)
        parser = mp.Process(target=_xml_parser, args=(self.logqueue, send_conn, filename))
        parser.start()

        # Main loop
        self.logger.info("Starting multiprocess main loop")
        running = True
        while running:
            # Handle (all) queued log messages
            self._handle_log_queue()

            # Handle XML elements
            handled = 0
            while receive_conn.poll() and handled <= self.max_elements_handled:
                handled += 1
                # Get the next element in the XML file
                elem = receive_conn.recv()
                # Finish if there are no more elements to parse
                if elem is None:
                    running = False
                # Handle elements
                else:
                    if elem.tag == "bounds":
                        self.min_latitude = float(elem.attrib['minlat'])
                        self.max_latitude = float(elem.attrib['maxlat'])
                        self.min_longitude = float(elem.attrib['minlon'])
                        self.max_longitude = float(elem.attrib['maxlon'])
                        self.logger.info("Area of map is defined by (%.4f, %.4f), (%.4f, %.4f)",
                                         self.min_latitude, self.min_longitude,
                                         self.max_latitude, self.max_longitude)
                    elif elem.tag == "node":
                        n = self._parse_node(elem)
                        self.nodes[n.id] = n
                    elif elem.tag == "way":
                        try:
                            w = self._parse_way(elem)
                        except MultiReader.UnusedWayException:
                            # This way is not used so don't register it
                            pass
                        else:
                            self.ways[w.id] = w

        parser.join()
        self.logger.info("Finished multiprocess main loop")
        self.logger.info("Found %d nodes", len(self.nodes))
        self.logger.info("Found %d ways", len(self.ways))
        # Handle log one more time just to be sure
        self._handle_log_queue(True)

        # Filter the ways to remove those that can not be traveled by car
        self._filter_noncar_ways()

        # Add references from nodes to ways that reference those nodes
        self.logger.info("Adding back-references from nodes to ways")
        for way in self.ways:
            for node in self.ways[way].nodes:
                self.nodes[node].ways.append(way)

    def _handle_log_queue(self, ignore_timer=False):
        """Reads log records in queue and passes them on to be logged.

        Subprocesses log to a queue instead of directly to the log file,
        they do so to prevent similtanious writes to a file from
        multiple processes. This function handles records in the queue
        and logs them instead. This means that these log events will end
        up in the right log handlers here.

        This function handles logs every X seconds, the exact interval
        is configured in the ctor with the default being 2 seconds. If
        the interval has not passed this function does nothing. It is
        possible to override this timer. If this is done then the timer
        is still reset.

        Params:
        ignore_timer - Override the timer"""
        if not ignore_timer and self.log_last_handled + self.log_interval > time.time():
            return

        try:
            while True:
                record = self.logqueue.get_nowait()
                logger = logging.getLogger(record.name)
                logger.handle(record)
        except queue.Empty:
            pass
        self.log_last_handled = time.time()

    def _parse_node(self, elem):
        """Parses a node XML element to the Node class.

        Params:
        elem - an XML Element that has a node tag (does not check
               whether it is actually a node tag)
        """
        n = Node(elem.attrib['id'], elem.attrib['lat'], elem.attrib['lon'])
        n.tags = self._parse_tags(elem)
        return n

    def _parse_way(self, elem):
        """Parses a way XML element to the Way class.

        Raises an exception when a way is not a 'highway', buildings,
        fields, lakes and others are all described by ways but they are
        useless for pathfinding. The exception is meant to filter these.

        Params:
        elem - an XML Element that has a way tag (does not check whether
               it is actually a way tag)
        """
        w = Way(elem.attrib['id'])
        w.tags = self._parse_tags(elem)
        if 'highway' not in w.tags.keys():
            raise MultiReader.UnusedWayException
        w.nodes = [int(node.attrib['ref']) for node in elem.findall('nd')]
        return w

    def _parse_tags(self, elem):
        """Parses all 'tag' subtags of a XML Element

        Is given a XML Element and parses all children which are a tag.
        It tries to convert the value of the tag to int or float if
        possible.

        Params:
        elem - an XML Element that possibly contains one or more 'tag'
               child elements.
        """
        if elem.find("tag") == None:
            return {}
        ret = {}
        for tag in elem.findall("tag"):
            key = tag.attrib['k']
            value = tag.attrib['v']

            # Try to convert the tag to a boolean
            if value.lower in ('t', 'true', 'y', 'yes'):
                ret[key] = True
                continue
            elif value.lower in ('f', 'false', 'n', 'no'):
                ret[key] = False
                continue

            # Try to convert the tag to a integer
            if value.isdigit():
                ret[key] = int(value)
                continue
            try:
                ret[key] = float(value)
            except:
                ret[key] = value
        return ret

    def filter_unused_nodes(self, aggressive=False):
        """Removes certain nodes from the list.

        Keeps all nodes that are either used to describe a way or
        contain data in the form of tags.

        Params:
        aggressive - Remove nodes that are not in ways but do contain
                     data
        """
        self.logger.info("Removing unused nodes")
        keep = set()

        # All nodes that are part of a way should be kept
        for way in self.ways:
            keep.update(self.ways[way].nodes)

        if not aggressive:
            keep.update([node for node in self.nodes if len(self.nodes[node].tags) > 0])

        self.logger.info("Removing %d nodes", len(self.nodes) - len(keep))
        # Build a new dict out of the IDs stored in the set, then move
        # it to the class variable
        new = {}
        while keep:
            node = keep.pop()
            new[node] = self.nodes[node]
        self.nodes = new

    def _filter_noncar_ways(self):
        """Removes all ways that can't be travelled by car."""
        self.logger.info("Removing all non-car ways")
        remove = set()
        # Remove all cycleways
        for way_id, way in self.ways.items():
            if way.tags['highway'] == 'cycleway':
                remove.add(way_id)
        # Remove based on access restrictions
        restrictions = (False, 'agricultural', 'delivery', 'no')
        for way_id, way in self.ways.items():
            if ('access' in way.tags and way.tags['access'] in restrictions) or \
                    ('motorcar' in way.tags and way.tags['motorcar'] in restrictions) or \
                    ('motor_vehicle' in way.tags and way.tags['motor_vehicle'] in restrictions):
                remove.add(way_id)

        # Remove the ways
        while remove:
            way = remove.pop()
            del self.ways[way]

        self.logger.info("Removed %d ways that can't be travelled by car", len(remove))

    class UnusedWayException(Exception):
        """Used to indicate that a way element is useless for pathfinding."""
        pass
