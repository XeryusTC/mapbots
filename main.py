#!/usr/bin/env python3

import logging
import logging.handlers
import random
import sys

import osmreader
import planners

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
    osm.filter_unused_nodes(True)
    osm.find_bounds()
    graph_builder = osmreader.DirectionalGraphBuilder(osm.nodes, osm.ways)
    graph_builder.build()
    exp = osmreader.MapImageExporter(osm.nodes, osm.ways, osm.min_lat,
                                     osm.max_lat, osm.min_lon, osm.max_lon)
    exp.export()
    gexp = osmreader.GraphMapExporter(graph_builder.graph, osm.min_lat,
                                      osm.max_lat, osm.min_lon, osm.max_lon)
    gexp.export()

    # Plan path between random nodes
    nodes = graph_builder.graph.nodes()
    start = random.choice(nodes)
    end = random.choice(nodes)
    path = planners.Astar(graph_builder.graph, start, end)

    pexp = planners.GraphPathExporter(graph_builder.graph, path, osm.min_lat,
                                      osm.max_lat, osm.min_lon, osm.max_lon)
    pexp.export()
