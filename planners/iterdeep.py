import logging
import time

logger = logging.getLogger(__name__)

from pygraph.classes.digraph import digraph

def iterative_deepening(graph, start_node, goal_node, max_depth=64, min_depth=8):
    """Find a route in a graph using iterative deepening.

    Uses a standard Depth First Search algorithm to find a path.
    Prevents getting stuck in loops by using the iterative deepening
    method. The DFS will only look for a path with a limited length. The
    limit will be increased if a path could not be found.

    Params:
    graph - The graph to do the search on
    start_node - The node that is the starting point of the route
    goal_node - The node that is the end point of the route
    max_depth - The maximum depth iterative deepening wil go to when
                trying to find a path
    min_depth - The first path length limit to use
    """
    logger = logging.getLogger('.'.join((__name__, 'iterative_deepening')))
    logger.info('Starting looking for a route from %s to %s using IDDFS (max depth: %d)',
                start_node, goal_node, max_depth)
    total_time = time.perf_counter()
    for lim in range(min_depth, max_depth):
        start = time.perf_counter()
        path = _iterdeep_rec(graph, start_node, goal_node, lim, 0)
        if path is not None:
            logger.info('Found a path by iterative deepening DFS in %f sec with length %d',
                        (time.perf_counter() - total_time), len(path))
            return path
        logger.info('Elapsed %f sec during iterative deepening DFS with limit %d',
                    (time.perf_counter() - start), lim)

def _iterdeep_rec(graph, current_node, goal_node, max_depth, depth, path=[]):
    """The Depth First Search algorithm used in iterative deepening

    Params:
    graph - The graph to do the search on
    current_node - The node where we are continuing the search from
    goal_node - The node we want to end up at
    max_depth - The maximum length of the path before returning failure
    depth - The current length of the path, when this gets larger than
            max_depth a failure will be returned
    path - The path that has been build from the start node up to but
           not including current_node
    """
    neighbours = graph.neighbors(current_node)
    # Base case 1, the goal node is in the list of neighbours, return
    # success + the found path
    if goal_node in neighbours:
        return path + [current_node, goal_node]
    # Base case 2, we have reached the maximum depth, return failure
    elif depth > max_depth:
        return None
    # Recursive case, look through all the neighbour nodes and try to
    # find a route continuing from them
    for neighbour in neighbours:
        # Skip this neighbour if it is already in the path we traversed
        if neighbour in path:
            continue
        # Recursive call, return its result if it is successful
        ret = _iterdeep_rec(graph, neighbour, goal_node, max_depth, depth+1, path + [current_node])
        if ret is not None:
            return ret
