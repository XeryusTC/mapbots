import logging
import math
from PIL import Image, ImageDraw
import xml.etree.ElementTree as ET

from osmreader.elements import Node, Way

logger = logging.getLogger('mapbots.osmreader.xmlreader')

class XMLReader:
    def __init__(self, filename=None):
        self.logger = logging.getLogger('mapbots.osmreader.xmlreader.XMLReader')
        if filename:
            self.load(filename)

    def load(self, filename):
        """Loads an XML file and stores the relevant OSM elements"""
        self.logger.info('Loading XML file %s (this might take a while)', filename)
        tree = ET.parse(filename)
        root = tree.getroot()

        # Get information about the document
        self.api_version = root.attrib['version']
        self.logger.info('Loaded XML file with OSM API version %s', self.api_version)

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
            w.nodes = [int(node.attrib['ref']) for node in way.findall('nd')]
            self.ways[int(way.attrib['id'])] = w
        self.logger.info('Number of ways found: %d', len(self.ways))

    def export_simple_image(self, filename='testexport.png'):
        """Exports the base OSM elements to a file"""
        self.logger.info('Exporting the current comain to %s', filename)
        IMAGE_MULTIPLIER = 50000
        width = math.ceil((self.max_longitude - self.min_longitude) * IMAGE_MULTIPLIER)
        height = math.ceil((self.max_latitude - self.min_latitude) * IMAGE_MULTIPLIER)
        im = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(im)

        # Draw all ways (in red)
        self.logger.info('Drawing the ways')
        for id, way in self.ways.items():
            coords = [ ((self.nodes[node].longitude - self.min_longitude) * IMAGE_MULTIPLIER,
                    (self.nodes[node].latitude - self.min_latitude) * IMAGE_MULTIPLIER) for node in way.nodes]
            draw.line(coords, fill=(255, 0, 0))

        # draw all nodes as points (in black)
        self.logger.info('Drawing the nodes')
        for id, node in self.nodes.items():
            draw.point( ((node.longitude - self.min_longitude) * IMAGE_MULTIPLIER,
                (node.latitude - self.min_latitude) * IMAGE_MULTIPLIER), fill=(0, 0, 0))

        im.transpose(Image.FLIP_TOP_BOTTOM).save(filename)

    def filter_ways(self):
        """Removes ways that are not marked as a highway/road"""
        self.logger.info('Removing ways that are not marked as \'highway\'')
        remove = []
        for id, way in self.ways.items():
            if 'highway' not in way.tags.keys():
                remove.append(id)

        for id in remove:
            del self.ways[id]
        self.logger.info('Removed %d ways', len(remove))

    def filter_nodes(self):
        """Removes nodes that are not referenced or do not contain any information"""
        self.logger.info('Removing unnecessary nodes')
        keep = set()
        # All nodes that are part of a way are marked to be kept
        for way in self.ways:
            keep.update(self.ways[way].nodes)

        # All nodes that contain information should be kept
        for id, node in self.nodes.items():
            if len(node.tags) > 0:
                keep.add(id)

        self.logger.info('Removing %d nodes', len(self.nodes) - len(keep))
        # Remove all nodes that are not marked to keep
        new = {}
        while keep:
            node = keep.pop()
            new[node] = self.nodes[node]
        self.nodes = new

    def _parse_tags(self, elem):
        return {tag.attrib['k']: tag.attrib['v'] for tag in elem.findall('tag')}
