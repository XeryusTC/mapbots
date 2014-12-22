import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger('mapbots.osmreader.xmlreader')

class XMLReader:
    def __init__(self):
        self.logger = logging.getLogger('mapbots.osmreader.xmlreader.XMLReader')

    def load(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()

        self.api_version = root.attrib['version']

        self.logger.info('Loading XML file with OSM API version %s', self.api_version)

        bounds = root.find('bounds')
        self.min_latitude = float(bounds.attrib['minlat'])
        self.max_latitude = float(bounds.attrib['maxlat'])
        self.min_longitude = float(bounds.attrib['minlon'])
        self.max_longitude = float(bounds.attrib['maxlon'])
        self.logger.info('Area of map is defined by (%f, %f), (%f, %f)', self.min_latitude, self.min_longitude, self.max_latitude, self.max_longitude)

