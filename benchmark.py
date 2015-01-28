#!/usr/bin/env python3

import itertools
import logging
import logging.handlers
import multiprocessing as mp
import queue
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

def Astar_worker(graph, taskqueue, resultqueue, logqueue):
    # Set up logging to use the queue
    h = logging.handlers.QueueHandler(logqueue)
    root = logging.getLogger()
    root.handlers = []
    root.addHandler(h)

    logger = logging.getLogger('A*_worker')
    logger.info("Starting A* benchmark subprocess")

    for id, start, end in iter(taskqueue.get, None):
        # Run A* and record its runtime
        start_time = time.perf_counter()
        path, open_set, closed_set = planners.Astar(graph, start, end, True)
        time_taken = time.perf_counter() - start_time
        # Create the statistics and report them to the main process
        length = sum([ graph.node_attributes(section)['length'] for section in path ])
        data = (id, start, end, 0, len(path), length, len(open_set), len(closed_set), time_taken)
        resultqueue.put(data)
        # Report that we have finished the benchmark
        taskqueue.task_done()
    # Notify that we processed the stop signal
    taskqueue.task_done()
    logger.info("Exiting A* benchmark subprocess")

def process_subprocess_logs(logqueue):
    try:
        while True:
            record = logqueue.get_nowait()
            logger = logging.getLogger(record.name)
            logger.handle(record)
    except queue.Empty:
        pass

def process_result_queue(resultqueue, logs):
    try:
        while True:
            record = resultqueue.get_nowait()
            logs.append(record)
    except queue.Empty:
        pass

def Astar_benchmark(runs=20):
    logger = logging.getLogger('A*_benchmark')

    logger.info("Setting up A* benchmark")
    osm = osmreader.MultiReader("benchmark.osm")
    osm.filter_unused_nodes(True)
    osm.find_bounds()
    graph = osmreader.DirectionalGraphBuilder(osm.nodes, osm.ways)
    graph.build()

    # Generate paths starts
    sections = ['6398654_5', '6455545_1', '6394116_3', '6398167_0', '6394550_1',
                '6454161_1', '6389831_0']
    paths = list(itertools.permutations(sections, 2))
    logs = []

    # Set up for the subprocesses
    taskqueue = mp.JoinableQueue()
    resultqueue = mp.Queue()
    logqueue = mp.Queue()
    # Use all cores but leave one for the main process
    process_count = max(2, mp.cpu_count() - 2)

    # Start the subprocesses before adding the tasks so they can get
    # started right away before we added several thousand (or more)
    # items to the task queue
    processes = [mp.Process(target=Astar_worker, args=(graph.graph, taskqueue, resultqueue, logqueue)) for i in range(process_count)]
    for p in processes:
        p.start()

    # Add the tasks and process logs and results until we are done
    logger.info("Creating benchmarks to run")
    total_time = time.perf_counter()
    j = 0 # benchmark number counter
    for start, end in paths:
        process_subprocess_logs(logqueue)
        for i in range(runs):
            taskqueue.put((j, start, end))
            j += 1
    for i in range(process_count):
        taskqueue.put(None)

    while taskqueue.qsize() > process_count * 2:
        process_subprocess_logs(logqueue)
        process_result_queue(resultqueue, logs)
        time.sleep(1) # Allow the CPU some rest

    # Wait for all processes to finish and process results one final time
    taskqueue.join()
    process_subprocess_logs(logqueue)
    for p in processes:
        p.join()
    process_result_queue(resultqueue, logs)
    process_subprocess_logs(logqueue)
    logger.info("Finished running benchmarks, total time spend: %f sec", time.perf_counter() - total_time)

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
