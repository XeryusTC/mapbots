#!/usr/bin/env python3

import logging
import osmreader

# Setup logging
logger = logging.getLogger('mapbots')
logger.setLevel(logging.DEBUG)
long_format = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
short_format = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
ch = logging.StreamHandler() # Create console handler
ch.setLevel(logging.INFO)
ch.setFormatter(short_format)
fh = logging.FileHandler('mapbots.log') # create file handler
fh.setLevel(logging.DEBUG)
fh.setFormatter(long_format)
logger.addHandler(ch)
logger.addHandler(fh)

if __name__ == '__main__':
    logger.info('Starting mapbots...')
    osm = osmreader.xmlreader.XMLReader()
    osm.load("graphtest.osm")
