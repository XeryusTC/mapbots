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
        osm = osmreader.IncrementalReader(sys.argv[1])
    else:
        osm = osmreader.IncrementalReader("graphtest.osm")
    exporter = osmreader.MapImageExporter(osm.nodes, osm.ways, osm.min_latitude,
        osm.max_latitude, osm.min_longitude, osm.max_longitude)
    exporter.export()
    gr = osmreader.IncrementalGraph(osm.nodes, osm.ways)
    gr.make_graph()
    gr.graph_to_file()
