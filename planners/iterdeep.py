import logging
import time

logger = logging.getLogger(__name__)

from planners.common import filter_neighbours
from pygraph.classes.digraph import digraph

def iterative_deepening(graph, start_node, goal_node, max_depth=64, min_depth=1):
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
    for lim in range(min_depth, max_depth+1):
        start = time.perf_counter()
        path = _iterdeep_rec(graph, start_node, goal_node, lim)
        if path is not None:
            logger.info('Found a path by iterative deepening DFS in %f sec with length %d',
                        (time.perf_counter() - total_time), len(path))
            return path
        logger.info('Elapsed %f sec during iterative deepening DFS with limit %d',
                    (time.perf_counter() - start), lim)

def _iterdeep_rec(graph, current_node, goal_node, max_depth, path=[]):
    """The Depth First Search algorithm used in iterative deepening

    Decreases the branching factor by assuming that each section will
    get traversed from one end to the other. This is done by registring
    from which end current way was entered, only neighbours that connect
    at the opposite end are kept.

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
    # Base case 1, we have reached the maximum depth, return failure
    if len(path) >= max_depth:
        return None

    neighbours = graph.neighbors(current_node)
    # Filter all the nodes so we only expand nodes at the opposite the
    # end where we entered the section
    if len(path) > 0:
        neighbours = filter_neighbours(graph, path[-1], current_node, neighbours)

    # Base case 2, the goal node is in the list of neighbours, return
    # success + the found path
    if goal_node in neighbours:
        return path + [current_node, goal_node]

    # Recursive case, expand the neighbours
    for neighbour in neighbours:
        # Skip this neighbour if it is already in the path we traversed
        if neighbour in path:
            continue

        ret = _iterdeep_rec(graph, neighbour, goal_node, max_depth, path + [current_node])
        if ret is not None:
            return ret
