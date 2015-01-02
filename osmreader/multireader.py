import logging
import logging.handlers
import multiprocessing as mp
import queue
import xml.etree.cElementTree as ET
import time

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
    def __init__(self, filename=None, *args, handle_log_interval=2):
        self.logger = logging.getLogger('mapbots.osmreader.multireader.MultiReader')
        self.nodes = {}
        self.ways = {}

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

        Logging from the subprocess is also handled here.

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
            try:
                # Get the next element in the XML file
                elem = receive_conn.recv()
            except queue.Empty:
                # Don't do anything if there are no elements to parse
                pass
            else:
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
            if value.isdigit():
                ret[key] = int(value)
            try:
                ret[key] = float(value)
            except:
                ret[key] = value
        return ret

    class UnusedWayException(Exception):
        """Used to indicate that a way element is useless for pathfinding."""
        pass
