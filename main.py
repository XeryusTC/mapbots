#!/usr/bin/env python3

import logging
import logging.handlers
import sys

import osmreader

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
long_format = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
short_format = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
 # Create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(short_format)
# Create file handler that keeps 5 files of max 1MB
fh = logging.handlers.RotatingFileHandler('mapbots.log', maxBytes=1024*1024, backupCount=5)
fh.setLevel(logging.DEBUG)
fh.setFormatter(long_format)
# Add handlers to root element
logger.addHandler(ch)
logger.addHandler(fh)

if __name__ == '__main__':
    logger.info('Starting mapbots...')
    if len(sys.argv) > 1:
        osm = osmreader.MultiReader(sys.argv[1])
    else:
        osm = osmreader.MultiReader("graphtest.osm")
    osm.filter_unused_nodes()
    graph_builder = osmreader.DirectionalGraphBuilder(osm.nodes, osm.ways)
    graph_builder.build()
    osmreader.graph_to_file(graph_builder.graph)
