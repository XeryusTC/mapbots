#!/usr/bin/env python3

import logging
import sys

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
    if len(sys.argv) > 1:
        osm = osmreader.XMLReader(sys.argv[1])
    else:
        osm = osmreader.XMLReader("graphtest.osm")
    osm.filter_ways()
    osm.filter_nodes()
    osm.export_simple_image()
