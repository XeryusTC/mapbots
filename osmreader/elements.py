import array
import logging

logger = logging.getLogger('mapbots.osmreader.elements')

class Node:
    def __init__(self, id, latitude, longitude):
        self.id = int(id)
        self.lat = float(latitude)
        self.lon = float(longitude)
        self.tags = {}
        self.ways = []

    @property
    def ways(self):
        return self._ways

    @ways.setter
    def ways(self, data):
        self._ways = array.array('q', data)

    def __str__(self):
        return "{id} ({lat}, {lon})".format(id=self.id, lat=self.lat, lon=self.lon)

class Way:
    def __init__(self, id):
        self.id = int(id)
        self.tags = {}
        self.nodes = []
        self.sections = 0

    def is_oneway(self):
        """Returns whether a way is unidirectional"""
        # Check whether the oneway tag is explicitly set
        if 'oneway' in self.tags and self.tags['oneway'] == True:
            return True
        # Check if this is a roundabout, which are also one way by implication
        if 'junction' in self.tags and self.tags['junction'] == 'roundabout':
            return True
        return False
