import logging
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw
from pydotplus import graphviz
from pygraph.classes.graph import graph
from pygraph.readwrite import dot as graphtodot
from osmreader.elements import Node, Way

logger = logging.getLogger('mapbots.osmreader.increader')

class IncrementalReader:
    """
    Reads the XML incrementally from a file and constructs a graph along the way.
    Should be fast and memory effecient.
    """
    def __init__(self, filename=None):
        """
        Params:
        filename - if set will call load() with this as argument
        """
        self.logger = logging.getLogger('mapbots.osmreader.increader.IncrementalReader')
        self.nodes = {}
        self.ways = {}
        if filename:
            self.load(filename)

    def load(self, filename):
        """
        Load from an .osm file on the map

        Params:
        filename - a .osm file (including extension)
        """
        if not isinstance(filename, str):
            raise TypeError("Filename should be a string of a relative or absolute file")
        if len(filename) == 0:
            raise ValueError("The filename can not be empty")

        logger.info("Starting to parse XML")
        it = ET.iterparse(filename, events=("start", "end"))
        event, root = next(it)

        # Get information about the document
        self.api_version = root.attrib['version']
        self.logger.info("Loaded XML file with OSM API version %s", self.api_version)

        # Parsing all other tags
        self.logger.info("Starting to parse the document")
        for event, elem in it:
            if event == "end":
                if elem.tag == "bounds":
                    self.min_latitude = float(elem.attrib['minlat'])
                    self.max_latitude = float(elem.attrib['maxlat'])
                    self.min_longitude = float(elem.attrib['minlon'])
                    self.max_longitude = float(elem.attrib['maxlon'])
                    self.logger.info("Area of map is defined by (%.4f, %.4f), (%.4f, %.4f)",
                        self.min_latitude, self.min_longitude, self.max_latitude, self.max_longitude)
                elif elem.tag == "node":
                    n = self.__parse_node(elem)
                    self.nodes[n.id] = n
                elif elem.tag == "way":
                    try:
                        w = self.__parse_way(elem)
                    except IncrementalReader.UnusedWayException:
                        pass  # Nothing much to do if we ignore a way
                    else:
                        self.ways[w.id] = w
                root.clear()
        self.logger.info("Found %d nodes", len(self.nodes))
        self.logger.info("Found %d ways", len(self.ways))

        # Add reference to each node that indicates which ways reference the node
        self.logger.info("Adding reverse node references")
        for way in self.ways:
            for node in self.ways[way].nodes:
                self.nodes[node].ways.append(way)

        # Don't log removing nodes beforehand as it barely takes any time (~1 sec on 61 sec runtime)
        self.nodes = {id: node for id, node in self.nodes.items() if node.ways or node.tags}
        self.logger.info("%d nodes remain after removing unused nodes" % len(self.nodes))

    def __parse_node(self, xml_node):
        n = Node(xml_node.attrib['id'], xml_node.attrib['lat'], xml_node.attrib['lon'])
        n.tags = self.__parse_tags(xml_node)
        return n

    def __parse_way(self, xml_way):
        w = Way(xml_way.attrib['id'])
        w.tags = self.__parse_tags(xml_way)
        if 'highway' not in w.tags.keys():
            raise IncrementalReader.UnusedWayException

        w.nodes = [int(node.attrib['ref']) for node in xml_way.findall("nd")]
        return w

    def __parse_tags(self, elem):
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

    class UnusedWayException(ValueError):
        """
        Exception raised if a way is parsed but it is not useful for building a
        route graph
        """
        pass


class IncrementalGraph:
    def __init__(self, nodes, ways):
        self.logger = logging.getLogger('mapbots.osmreader.increader.IncrementalGraph')
        self.nodes = nodes
        self.ways = ways
        self.graph = graph()

    def make_graph(self):
        self.logger.info("Starting to build a graph from %d nodes and %d ways", len(self.nodes), len(self.ways))
        # Build list of graph nodes
        for id, way in self.ways.items():
            self.graph.add_node(id, [('nodes', way.nodes), ('tags', way.tags)])

        # Build list of graph edges
        for way_id, way in self.ways.items():
            for node in way.nodes:
                for ref_way in self.nodes[node].ways:
                    if way_id != ref_way and not self.graph.has_edge((way_id, ref_way)):
                        self.graph.add_edge((way_id, ref_way))

    def graph_to_file(self, filename="graph.png"):
        """Exports the current graph as an image"""
        self.logger.info('Exporting graph to %s', filename)
        # convert graph to DOT language
        dot = graphtodot.write(self.graph)
        # convert DOT language to something we can export as an image
        gvgraph = graphviz.graph_from_dot_data(dot)
        gvgraph.write(filename, format='png')
