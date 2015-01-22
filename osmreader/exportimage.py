import logging
import math

from PIL import Image, ImageDraw
from pydotplus import graphviz
from pygraph.readwrite import dot as graphtodot
from random import randrange
from weakref import WeakValueDictionary

logger = logging.getLogger('mapbots.osmreader.exportimage')

class _ColorManager:
    def __init__(self):
        """Handles (random) colours for drawing images.

        Colours can be specified in several ways: a 3-tuple specifying a
        RGB value; the name of a colour as interpreted by PIL (no
        validity checking is done here); the value "random" which means
        that a random 3-tuple is picked once and that value is used;
        "allrandom" which returns a new colour 3-tuple every time the
        colour is requested, meaning that every time an element is drawn
        it is drawn with a (pseudo) unique colour.
        """
        self.__colors = {}

    def __getattr__(self, name):
        try:
            if self.__colors[name] == None:
                return(randrange(255), randrange(255), randrange(255))
            else:
                return self.__colors[name]
        except KeyError:
            raise AttributeError("'{0}' object has no attribute '{1}'".format(self.__name__, name))

    def __setattr__(self, name, value):
        if name.endswith('_color'):
            if isinstance(value, tuple) and len(value) == 3:
                self.__colors[name] = value
            elif isinstance(value, str):
                value = value.lower()
                if value == "random":
                    # Just pick a random color and use it forever
                    self.__colors[name] = (randrange(255), randrange(255), randrange(255))
                elif value == "allrandom":
                    # Use a random color every time (None has special meaning in __getattr__)
                    self.__colors[name] = None
                else:
                    # Asume the string is a valid color string
                    self.__colors[name] = value
            elif value == None:
                self.__colors[name] = None
            else:
                raise TypeError("Unexpected color type received: {}".format(type(value)))
        else:
            # Use default behaviour for non-colors
            self.__dict__[name] = value


class MapImageExporter(_ColorManager):
    def __init__(self, nodes, ways, min_lat, max_lat, min_lon, max_lon, *args,
                 node_color=(0, 0, 0), way_color="allrandom", bg_color="white",
                 enlargement=50000):
        """Export map data (nodes and ways) as a map like image.

        Params:
        nodes - The raw nodes as read by any OSM file reader
        ways - The raw ways as read by any OSM file reader
        min_lat - The southern border of the map
        max_lat - The northern border of the map
        min_lon - The western border of the map
        max_lon - The eastern border of the map
        node_color - The colour of the nodes in the image
        way_color - The colour of the ways in the image
        bg_color - The colour of the image background
        enlargement - Multiplication factor from map coordinate to pixel
                      coordinate. Determines image size.
        """
        super(MapImageExporter, self).__init__()
        self.logger = logging.getLogger('mapbots.osmreader.exportimage.MapImageExporter')

        self.nodes = WeakValueDictionary(nodes)
        self.ways = WeakValueDictionary(ways)

        self.enlargement = enlargement
        self.width = math.ceil((max_lon - min_lon) * self.enlargement)
        self.height = math.ceil((max_lat - min_lat) * self.enlargement)
        self.min_lon = min_lon
        self.min_lat = min_lat

        self.node_color = node_color
        self.way_color = way_color
        self.bg_color = bg_color

    def export(self, filename="export.png"):
        """Export the information to an image file

        Params:
        filename - The filename to export to, must have a valid image
                   extention. Default: export.png
        """
        self.logger.info('Exporting a map image to %s', filename)
        im = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(im)

        # Draw all ways
        self.logger.info('Drawing the ways')
        for id, way in self.ways.items():
            coords = [ ((self.nodes[node].lon - self.min_lon) * self.enlargement,
                    (self.nodes[node].lat - self.min_lat) * self.enlargement) for node in way.nodes]
            draw.line(coords, fill=self.way_color)

        # draw all nodes as points
        self.logger.info('Drawing the nodes')
        for id, node in self.nodes.items():
            draw.point( ((node.lon - self.min_lon) * self.enlargement,
                (node.lat - self.min_lat) * self.enlargement), fill=self.node_color)

        im.transpose(Image.FLIP_TOP_BOTTOM).save(filename)


class GraphMapExporter(_ColorManager):
    def __init__(self, graph, min_lat, max_lat, min_lon, max_lon, *args,
                 section_color="allrandom", bg_color="white",
                 enlargement=50000):
        """Export a (directional) graph as a map image

        Params:
        graph - The graph to export to a image
        min_lat - The southern border of the map
        max_lat - The northern border of the map
        min_lon - The western border of the map
        max_lon - The eastern border of the map
        section_color = The colour of the graph sections in the image
        bg_color - The colour of the image background
        enlargement - Multiplication factor from map coordinate to pixel
                      coordinate. Determines image size.
        """
        super(GraphMapExporter, self).__init__()
        self.logger = logging.getLogger('mapbots.osmreader.exportimage.GraphMapExporter')

        self.graph = graph

        self.enlargement = enlargement
        self.width = math.ceil((max_lon - min_lon) * self.enlargement)
        self.height = math.ceil((max_lat - min_lat) * self.enlargement)
        self.min_lon = min_lon
        self.min_lat = min_lat

        self.section_color = section_color
        self.bg_color = bg_color

    def export(self, filename="graph-export.png"):
        self.logger.info('Exporting a graph to map image %s', filename)
        im = Image.new('RGB', (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(im)

        # Draw sections
        for section in self.graph.nodes():
            attrs = self.graph.node_attributes(section)
            # Convert the path in the node to image coordinates
            path = [ ((path[1]-self.min_lon)*self.enlargement, (path[0]-self.min_lat)*self.enlargement) for path in attrs['path'] ]
            draw.line(path, fill=self.section_color)

        im.transpose(Image.FLIP_TOP_BOTTOM).save(filename)

def graph_to_file(graph, filename='graph.png', delete_single=False):
    """Exports a graph to a image file.

    Params:
    graph - The graph to export.
    filename - The destination of the output. The filename should
               include an extention, the format of the file will always
               be PNG no matter what the extention is.
    delete_single - If set to true then all nodes without any neighbours
                    will be deleted prior to exporting the graph.
    """
    logger = logging.getLogger('mapbots.osmreader.exportimage.graph_to_file')
    logger.info("Exporting a graph to %s", filename)

    # Delete nodes that don't have any neighbours
    if delete_single:
        del_nodes = [node for node in graph.nodes() if not graph.neighbors(node)]
        logger.info("Deleting %d nodes without neighbours", len(del_nodes))
        for node in del_nodes:
            graph.del_node(node)

    # Write the graph
    dot = graphtodot.write(graph)
    gvgraph = graphviz.graph_from_dot_data(dot)
    gvgraph.write(filename, format='png')
