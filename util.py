import logging
import math

from PIL import Image, ImageDraw
from random import randrange

logger = logging.getLogger(__name__)

class ColorManager:
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

class MapExporter(ColorManager):
    def __init__(self, min_lat, max_lat, min_lon, max_lon, bg_color="white", enlargement=50000):
        """Abstract class to extend to export data as a map

        Params:
        min_lat - The southern border of the map
        max_lat - The northern border of the map
        min_lon - The western border of the map
        max_lon - The eastern border of the map
        bg_color - The colour of the image background
        """
        super(MapExporter, self).__init__()
        # Calculate the image size based on the lat/lon information
        self.enlargement = enlargement
        self.width = math.ceil((max_lon - min_lon) * self.enlargement)
        self.height = math.ceil((max_lat - min_lat) * self.enlargement)
        self.min_lon = min_lon
        self.min_lat = min_lat

        self.bg_color = bg_color

        # Create a surface to draw on
        self.image = Image.new('RGB', (self.width, self.height), self.bg_color)
        self.draw = ImageDraw.Draw(self.image)

    def export(self, filename="export.png"):
        raise NotImplementedError("An exporter should implement the export function")

    def _save_image(self, filename, flip=True):
        """Save an image to an image file

        Params:
        filename - The filename to save to, should include a valid
                   extention so PIL can autodetect the right format
        image - The PIL image data to save
        flip - When true the image will be horizontally flipped. Usually
               an image is created upside down so this will turn it
               right side up when exporting. True by default.
        """
        if flip:
            self.image.transpose(Image.FLIP_TOP_BOTTOM).save(filename)
        else:
            self.image.save(filename)
