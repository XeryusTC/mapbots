import geopy.distance
import logging
import pygraph.classes.exceptions as graphexc

from pygraph.classes.digraph import digraph
from pygraph.classes.exceptions import AdditionError

logger = logging.getLogger(__name__)

class DirectionalGraphBuilder:
    def __init__(self, nodes, ways):
        self.logger = logging.getLogger('.'.join((__name__, type(self).__name__)))
        self.nodes = nodes
        self.ways = ways
        self.graph = digraph()

    def build(self):
        """Builds the graph from the nodes and ways.

        Algorithm overview:
        - Loops over all the ways to determine whether they have any
          junctions with other ways (or themselves) in them. For each
          way section between two junction a node is added to the graph.
          This means that each way gets at least one section.
        - If a way consists of multiple sections then these sections
          get edges between them. If a way is one directional then edges
          are added in the direction that the nodes are defined in.
          Otherwise edges are added in both directions
        - Ways are then connected to each other. This is based on the
          start and end nodes of the sections that make up ways. Each
          section is checked which other sections it should connect to
          and these connections are made. It does check for one
          directional ways while doing this.
          Because every section is looped over bidirectional crossroads
          are handled correctly. Sections which can be travelled in both
          directions are thus bidirectional
        """
        # Split a way into its subsections between intersections
        self.logger.info("Splitting ways into sections that connect intersections")
        for way in self.ways:
            # The first node is also the first junction in a way
            last_junction = self.ways[way].nodes[0]

            # Check if this way consists of multiple sections
            for node in self.ways[way].nodes[1:]:
                if len(self.nodes[node].ways) > 1:
                    # A junction in the middle of the way has been found
                    self._build_section(way, last_junction, node)

                    # Move the last junction marker so the next section
                    # starts at the right place
                    last_junction = node
            else:
                # Handle ways that have a dead end
                if last_junction != self.ways[way].nodes[-1]:
                    self._build_section(way, last_junction, self.ways[way].nodes[-1])
                # The last element in a roundabout should be connected
                # to the first element
                try:
                    if self.ways[way].nodes[0] == self.ways[way].nodes[-1]:
                        first = ''.join([str(way), '_', '0'])
                        last = ''.join([str(way), '_', str(self.ways[way].sections-1)])
                        self.graph.add_edge((last, first))
                except KeyError:
                    pass # The way is not a roundabout
                except AdditionError:
                    logger.warning("Tried adding a roundabout connection between %s and %s while it already existed",
                                 first, last)

        # Connect ways to other ways
        self.logger.info("Connecting ways to other ways")
        for current_way in self.ways:
            for section in range(self.ways[current_way].sections):
                name = ''.join([str(current_way), '_', str(section)])
                # Only try to connect the start of a section to another
                # section if the current way is bidirectional
                if not self.ways[current_way].is_oneway():
                    section_start = self.graph.node_attributes(name)['start_node']
                    self._connect_sections(current_way, name, section_start)

                # Connect the end of the way to other ways
                section_end = self.graph.node_attributes(name)['end_node']
                # Loop over all the ways that the current section start
                # should be connected with
                self._connect_sections(current_way, name, section_end)
        self.logger.info("Finished building the graph")

    def _connect_sections(self, current_way, name, node):
        """Connects a section to all the sections that it is connected with.

        Connects a section to all the sections that are connected to one
        of its endpoints (node). It checks whether a way is oneway to
        make junctions oneway.

        Params:
        current_way - The ID of the way that is being connected
        name - The name of the section in which the endpoint lives
        node - The node ID of the endpoint
        """
        # Loop over all the ways that the current section should be
        # connected with for this endpoint
        for other_way in self.nodes[node].ways:
            # Skip connecting a section to other sections in this way
            # This has already been done when creating sections and has
            # side effects like self-referencing sections
            if current_way == other_way:
                continue
            for other_section in range(self.ways[other_way].sections):
                other_name = ''.join([str(other_way), '_', str(other_section)])
                other_attrs = self.graph.node_attributes(other_name)
                # We can always connect from the current way to the
                # start of another section
                if other_attrs['start_node'] == node:
                    try:
                        self.graph.add_edge((name, other_name))
                    except graphexc.AdditionError:
                        # Ignore adding the same edge twice
                        pass

                # Only connect to the end of another section if it is
                # bidirectional
                if not self.ways[other_way].is_oneway() and other_attrs['end_node'] == node:
                    try:
                        self.graph.add_edge((name, other_name))
                    except graphexc.AdditionError:
                        # Ignore adding the same edge twice
                        pass

    def _build_section(self, way, start_node, end_node):
        """Builds a section out a way and adds it to the graph.

        Given a way and two nodes in that way this function will
        construct a section and add it as a node to the graph. It will
        calculate the length and all the intermediary lat/lon
        coordinates in that section and store those in the graph too.

        Params:
        way - The way to build the section for
        start_node - The ID of the node the section should start at
        end_node - The ID of the node the section should end at
        """
        # Calculate the length of the section
        s = self.ways[way].nodes.index(start_node)
        # Make sure the end is always further in the sequence than the
        # start
        e = self.ways[way].nodes.index(end_node, s+1) + 1
        path = [ (self.nodes[n].lat, self.nodes[n].lon) for n in self.ways[way].nodes[s:e] ]
        length = calculate_distance(path)

        # Add the section to the graph as a node
        name = ''.join([str(way), '_', str(self.ways[way].sections)])
        attrs = {'start_node': start_node,
                 'end_node': end_node,
                 'tags': self.ways[way].tags,
                 'way': way,
                 'length': length,
                 'path': path}
        self.graph.add_node(name, attrs=attrs)

        # Create edges between sections if there are any
        if self.ways[way].sections > 0:
            previous_name = ''.join([str(way), '_', str(self.ways[way].sections-1)])
            self.graph.add_edge((previous_name, name))
            if not self.ways[way].is_oneway():
                self.graph.add_edge((name, previous_name))
        self.ways[way].sections += 1


def calculate_distance(points):
    """Calculates distance as the crow flies between a series of points.

    Takes a sequence of points and calculates the distance between each
    consecutive pair of points and returns the total distance. The
    distance is the distance over a surface of a sphere so the points
    are a (latitude, longitude) tuple. The distance is calculated using
    the Vincenty method.

    Params:
    points - A list of (lat, lon) tuples for which the distance needs to
             be calculated.
    """
    if len(points) < 2:
        raise ValueError("points must be a sequence with at least two components")

    total = 0.0
    last_point = points[0]
    for point in points[1:]:
        total += geopy.distance.distance(last_point, point).m
        last_point = point
    return total
