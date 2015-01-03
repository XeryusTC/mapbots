import array
import logging

logger = logging.getLogger('mapbots.osmreader.elements')

class Node:
    def __init__(self, id, latitude, longitude):
        self.id = int(id)
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.tags = {}
        self.ways = []

    @property
    def ways(self):
        return self._ways

    @ways.setter
    def ways(self, data):
        self._ways = array.array('q', data)

    def __str__(self):
        return "{id} ({lat}, {lon})".format(id=self.id, lat=self.latitude, lon=self.longitude)

class Way:
    def __init__(self, id):
        self.id = int(id)
        self.tags = {}
        self.nodes = []
        self.sections = 0

