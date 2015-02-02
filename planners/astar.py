import geopy.distance as gdistance
import heapq
import logging
import time

from planners.common import filter_neighbours, find_side_entered
from planners.exporters import GraphAstarExporter

logger = logging.getLogger(__name__)

def Astar(graph, start, goal, with_data=False):
    """Finds a path in a graph using the A* algorithm

    Params:
    graph - The graph to do the search in
    start - The start node
    goal - The goal node of the search
    with_data - When False will only return the path that has been
                found. When True will return a tuple of the path, the
                open set and the closed set.
    """
    logger = logging.getLogger('.'.join((__name__, 'A*')))
    logger.info('Using A* to plan a route from %s to %s', start, goal)

    fringe = []
    closed = set()
    ancestors = {}
    g = {}
    g[start] = 0

    heapq.heappush(fringe, (predicted_cost(graph, start, goal), start))

    start_time = time.perf_counter()
    while fringe:
        cur_cost, current = heapq.heappop(fringe)
        if current == goal:
            path = construct_path(ancestors, current)
            logger.info('Found a path with length %d using A* in %f sec. Sections searched: %d, sections to search: %d',
                        len(path), time.perf_counter() - start_time, len(closed), len(fringe))
            if with_data:
                open_set = [ item[1] for item in fringe ]
                return (path, open_set, closed)
            return path

        closed.add(current)
        neighbours = graph.neighbors(current)
        # TODO: filter neighbours
        if current != start:
            entered_side = find_side_entered(graph, ancestors[current], current)
            neighbours = filter_neighbours(graph, entered_side, current, neighbours)

        for neighbour in neighbours:
            # Skip a neighbour if we have already expanded it
            if neighbour in closed:
                continue

            new_g = g[current] + graph.node_attributes(current)['length']

            for cost, section in fringe:
                if section == neighbour and new_g < cost:
                    # Update neighbour in the fringe
                    ancestors[neighbour] = current
                    g[neighbour] = new_g
                    f = new_g + predicted_cost(graph, neighbour, goal)
                    # Replace the element in the fringe
                    fringe.remove( (cost, section) )
                    heapq.heapify(fringe)
                    heapq.heappush(fringe, (f, neighbour))
                    break
            else:
                # Neighbour is not in the fringe yet
                ancestors[neighbour] = current
                g[neighbour] = new_g
                f = new_g + predicted_cost(graph, neighbour, goal)
                heapq.heappush(fringe, (f, neighbour))
    print("fell through")

def cost(graph, path):
    """Calculates g(n) based on the length of a path

    Params:
    graph - The graph that the path goes through
    path - The path that is planned through the graph
    """
    return sum([graph.node_attributes(section)['length'] for section in path])

def predicted_cost(graph, current, goal):
    """Calculates h(n) based on shortest as-the-crow-flies path

    Params:
    graph - The graph containing where a path is being planned through
    current - The node the heuristic is calculated for
    goal - The goal of the search
    """
    cattrs = graph.node_attributes(current)
    gattrs = graph.node_attributes(goal)
    return min(gdistance.distance(cattrs['start_point'], gattrs['start_point']).m,
               gdistance.distance(cattrs['start_point'], gattrs['end_point']).m,
               gdistance.distance(cattrs['end_point'], gattrs['start_point']).m,
               gdistance.distance(cattrs['end_point'], gattrs['end_point']).m)

def construct_path(ancestors, end):
    """Constructs the path based on ancestor information

    Params:
    ancestors - Information about which section (value) was visited
                before another section (key)
    end - The last section in the path
    """
    path = [end]
    last = end
    while True:
        try:
            path.append(ancestors[last])
            last = ancestors[last]
        except KeyError:
            path.reverse()
            return path
