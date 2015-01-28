#!/usr/bin/env python3

import itertools
import logging
import statistics as stat
import time

import osmreader
import planners

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    long_format = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    short_format = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
    # Create console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(short_format)
    # Create file handler that keeps 5 files of max 1MB
    fh = logging.handlers.RotatingFileHandler('benchmark.log', maxBytes=1024*1024*5, backupCount=5)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(long_format)
    # Add handlers to root element
    logger.addHandler(ch)
    logger.addHandler(fh)

def Astar_benchmark(runs=100):
    logger = logging.getLogger('A*_benchmark')

    logger.info("Setting up A* benchmark")
    osm = osmreader.MultiReader("benchmark.osm")
    osm.filter_unused_nodes(True)
    osm.find_bounds()
    graph = osmreader.DirectionalGraphBuilder(osm.nodes, osm.ways)
    graph.build()

    # Generate paths starts
    sections = ['6398654_5', '6455545_1', '6394116_3', '6398167_0', '6394550_1',
                '6454161_1', '6389831_0','29090917_0', '6456937_2', '6398969_0']
    paths = list(itertools.permutations(sections, 2))
    logs = []

    logger.info("Starting A* benchmark, running %d benchmarks %d times", len(paths), runs)
    total_time = time.perf_counter()
    j = 0 # benchmark number counter
    for start, end in paths:
        start_time = time.perf_counter()
        times = []
        for i in range(runs):
            single_time = time.perf_counter()
            path, open_set, closed_set = planners.Astar(graph.graph, start, end, True)

            # Add to statistics list
            time_taken = time.perf_counter() - single_time
            times.append(time_taken)
            # Calculate path length
            length = sum([ graph.graph.node_attributes(section)['length'] for section in path])
            logs.append((j, start, end, i, len(path), length, len(open_set), len(closed_set), time_taken))
        # Log statistics
        logger.info("Ran %d benchmarks from %s to %s for %f sec", runs, start, end, time.perf_counter() - start_time)
        logger.info("Lengths: path %d, open set %d, closed set %d",
                     len(path), len(open_set), len(closed_set))
        j += 1
    logger.info("Took %f sec to run benchmark and generate statistics", time.perf_counter() - total_time)

    logger.info("Generating A* sum statistics")
    logsT = list(zip(*logs)) # Transpose logs
    logger.info("                 |     Mean    |    Median   |   St. Dev.")
    logger.info("Path length      | {:11.4f} | {:11.4f} | {:11.4f}".format(stat.mean(logsT[4]), stat.median(logsT[4]), stat.stdev(logsT[4])))
    logger.info("Route length (m) | {:11.4f} | {:11.4f} | {:11.4f}".format(stat.mean(logsT[5]), stat.median(logsT[5]), stat.stdev(logsT[5])))
    logger.info("Open set         | {:11.4f} | {:11.4f} | {:11.4f}".format(stat.mean(logsT[6]), stat.median(logsT[6]), stat.stdev(logsT[6])))
    logger.info("Closed set       | {:11.4f} | {:11.4f} | {:11.4f}".format(stat.mean(logsT[7]), stat.median(logsT[7]), stat.stdev(logsT[7])))
    logger.info("Run time (s)     | {:11.4f} | {:11.4f} | {:11.4f}".format(stat.mean(logsT[8]), stat.median(logsT[8]), stat.stdev(logsT[8])))
    logger.info("Total time spend in A*: %f sec", sum(logsT[8]))

if __name__ == '__main__':
    setup_logging()
    Astar_benchmark()
