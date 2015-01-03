import logging
import math

from PIL import Image, ImageDraw
from pydotplus import graphviz
from pygraph.readwrite import dot as graphtodot
from random import randrange
from weakref import WeakValueDictionary

logger = logging.getLogger('mapbots.osmreader.exportimage')

class MapImageExporter:
    def __init__(self, nodes, ways, min_latitude, max_latitude, min_longitude,
            max_longitude, *args, node_color=(0, 0, 0), way_color="allrandom",
            bg_color="white", enlargement=50000):
        self.logger = logging.getLogger('mapbots.osmreader.exportimage.MapImageExporter')

        self.nodes = WeakValueDictionary(nodes)
        self.ways = WeakValueDictionary(ways)

        self.enlargement = enlargement
        self.width = math.ceil((max_longitude - min_longitude) * self.enlargement)
        self.height = math.ceil((max_latitude - min_latitude) * self.enlargement)
        self.min_longitude = min_longitude
        self.min_latitude = min_latitude

        self.__colors = {}
        self.node_color = node_color
        self.way_color = way_color
        self.bg_color = bg_color

    def export(self, filename="export.png"):
        self.logger.info('Exporting a map image to %s', filename)
        im = Image.new('RGB', (self.width, self.height), 'white')
        draw = ImageDraw.Draw(im)

        # Draw all ways
        self.logger.info('Drawing the ways')
        for id, way in self.ways.items():
            coords = [ ((self.nodes[node].longitude - self.min_longitude) * self.enlargement,
                    (self.nodes[node].latitude - self.min_latitude) * self.enlargement) for node in way.nodes]
            draw.line(coords, fill=self.way_color)

        # draw all nodes as points
        self.logger.info('Drawing the nodes')
        for id, node in self.nodes.items():
            draw.point( ((node.longitude - self.min_longitude) * self.enlargement,
                (node.latitude - self.min_latitude) * self.enlargement), fill=self.node_color)

        im.transpose(Image.FLIP_TOP_BOTTOM).save(filename)

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
