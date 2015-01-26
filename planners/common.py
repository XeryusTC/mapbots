import logging

logger = logging.getLogger(__name__)

def filter_neighbours(graph, previous, parent, neighbours):
    """Filters the neighbours based on which side a node was entered on

    The pathfinding algorithms should assume that a section gets
    travelled when it occurs in the path. By default this is not the
    case as the graph returns all the neighbours. This function can be
    used to filter the neighbours so that only the neighbours are kept
    that are on the opposite end of where the section got entered.

    Params:
    graph - The graph that gets searched
    previous - The node that occurs in the path before the node that we
               retrieved the neighbours on
    parent - The current node that is being expanded
    neighbours - The list of neighbours to filter
    """
    node_info = graph.node_attributes(parent)
    prev_node = graph.node_attributes(previous)
    entered_start = node_info['start_node'] in (prev_node['start_node'], prev_node['end_node'])

    new_neighbours = []
    for neighbour in neighbours:
        neighbour_info = graph.node_attributes(neighbour)
        if entered_start and node_info['end_node'] in (neighbour_info['start_node'], neighbour_info['end_node']):
            new_neighbours.append(neighbour)
        elif not entered_start and node_info['start_node'] in (neighbour_info['start_node'], neighbour_info['end_node']):
            new_neighbours.append(neighbour)
    return new_neighbours
