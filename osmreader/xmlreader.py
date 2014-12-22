import logging
import xml.etree.ElementTree as ET

from osmreader.elements import Node, Way

logger = logging.getLogger('mapbots.osmreader.xmlreader')

class XMLReader:
    def __init__(self):
        self.logger = logging.getLogger('mapbots.osmreader.xmlreader.XMLReader')

    def load(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()

        # Get information about the document
        self.api_version = root.attrib['version']
        self.logger.info('Loading XML file with OSM API version %s', self.api_version)

        # Get information about the map
        bounds = root.find('bounds')
        self.min_latitude = float(bounds.attrib['minlat'])
        self.max_latitude = float(bounds.attrib['maxlat'])
        self.min_longitude = float(bounds.attrib['minlon'])
        self.max_longitude = float(bounds.attrib['maxlon'])
        self.logger.info('Area of map is defined by (%f, %f), (%f, %f)', self.min_latitude, self.min_longitude, self.max_latitude, self.max_longitude)

        # Load all nodes
        self.nodes = {}
        for node in root.findall('node'):
            n = Node(node.attrib['id'], node.attrib['lat'], node.attrib['lon'])
            n.tags = self._parse_tags(node)  # Add the tags to the node (if there are any)
            self.nodes[int(node.attrib['id'])] = n
        self.logger.info('Number of nodes found: %d', len(self.nodes))

        # Load all ways
        self.ways = {}
        for way in root.findall('way'):
            w = Way(way.attrib['id'])
            w.tags = self._parse_tags(way)  # Add the tags to the way
            w.nodes = [node.attrib['ref'] for node in way.findall('nd')]
            self.ways[int(way.attrib['id'])] = w
        self.logger.info('Number of ways found: %d', len(self.ways))

    def _parse_tags(self, elem):
        return {tag.attrib['k']: tag.attrib['v'] for tag in elem.findall('tag')}
