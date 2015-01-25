import logging

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
