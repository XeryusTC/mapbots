import logging
import math

from PIL import Image, ImageDraw
from random import randrange

logger = logging.getLogger('mapbots.osmreader.exportimage')

class MapImageExporter:
    def __init__(self, nodes, ways, min_latitude, max_latitude, min_longitude,
            max_longitude, *args, node_color=(0, 0, 0), way_color="allrandom",
            bg_color="white", enlargement=50000):
        self.logger = logging.getLogger('mapbots.osmreader.exportimage.MapImageExporter')
        self.nodes = nodes
        self.ways = ways
        self.node_color = node_color
        self.way_color = way_color
        self.enlargement = enlargement
        self.width = math.ceil((max_longitude - min_longitude) * self.enlargement)
        self.height = math.ceil((max_latitude - min_latitude) * self.enlargement)
        self.min_longitude = min_longitude
        self.min_latitude = min_latitude

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

    @property
    def node_color(self):
        return self.__get_color(self._node_color)

    @node_color.setter
    def node_color(self, new):
        self._node_color = self.__set_color(new)

    @property
    def way_color(self):
        return self.__get_color(self._way_color)

    @way_color.setter
    def way_color(self, new):
        self._way_color = self.__set_color(new)

    @property
    def bg_color(self):
        return self.__get_color(self._bg_color)

    @bg_color.setter
    def bg_color(self, new):
        self._way_color = self.__set_color(new)

    def __get_color(self, color):
        if color == None:
            return(randrange(255), randrange(255), randrange(255))
        else:
            return color

    def __set_color(self, new):
        if isinstance(new, tuple) and len(new) == 3:
            return new
        elif isinstance(new, str):
            new = new.lower()
            if new == "random":
                # Just pick a random color to use forever
                return (randrange(255), randrange(255), randrange(255))
            elif new == "allrandom":
                # Use a random color every time
                return None
            else:
                # Asume a valid color string
                return new
        elif new == None:
            return None

        raise TypeError("Unexpected type received: {}".format(type(new)))
