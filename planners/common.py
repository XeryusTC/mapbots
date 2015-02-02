import logging

logger = logging.getLogger(__name__)

ENTERED_START = 0
ENTERED_END = 1

def find_side_entered(graph, previous, current):
    """Find out from which side a section was entered

    Params:
    graph - The graph that gets searched
    previous - The section that occurs in the path before the current
               section
    current - The section of which we are trying to detect from which
              side it was entered

    Returns: ENTERED_START if the current section was entered at the
    start node. ENTERED_END otherwise
    """
    node_info = graph.node_attributes(current)
    prev_node = graph.node_attributes(previous)
    return ENTERED_START if node_info['start_node'] in (prev_node['start_node'], prev_node['end_node']) else ENTERED_END

def filter_neighbours(graph, entered_side, parent, neighbours):
    """Filters the neighbours based on which side a node was entered on

    The pathfinding algorithms should assume that a section gets
    travelled when it occurs in the path. By default this is not the
    case as the graph returns all the neighbours. This function can be
    used to filter the neighbours so that only the neighbours are kept
    that are on the opposite end of where the section got entered.

    Params:
    graph - The graph that gets searched
    entered_side - The side from which the parent was entered. Should be
                   ENTERED_START or ENTERED_END
    parent - The current node that is being expanded
    neighbours - The list of neighbours to filter
    """
    node_info = graph.node_attributes(parent)
    new_neighbours = []
    for neighbour in neighbours:
        neighbour_info = graph.node_attributes(neighbour)
        if entered_side == ENTERED_START and node_info['end_node'] in (neighbour_info['start_node'], neighbour_info['end_node']):
            new_neighbours.append(neighbour)
        elif entered_side == ENTERED_END and node_info['start_node'] in (neighbour_info['start_node'], neighbour_info['end_node']):
            new_neighbours.append(neighbour)
    return new_neighbours
