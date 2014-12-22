import logging

logger = logging.getLogger('mapbots.osmreader.elements')

class Node:
    def __init__(self, id, latitude, longitude):
        self.logger = logging.getLogger('mapbots.osmreader.elements.Node')
        self.id = int(id)
        self.latitude = float(latitude)
        self.longitude = float(longitude)
        self.tags = {}

    def __str__(self):
        return "{id} ({lat}, {lon})".format(id=self.id, lat=self.latitude, lon=self.longitude)

class Way:
    def __init__(self, id):
        self.logger = logging.getLogger('mapbots.osmreader.elements.Way')
        self.id = int(id)
        self.tags = {}
        self.nodes = []
