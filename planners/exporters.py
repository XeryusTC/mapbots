import logging

from util import MapExporter

logger = logging.getLogger(__name__)

class GraphPathExporter(MapExporter):
    def __init__(self, graph, path, min_lat, max_lat, min_lon, max_lon, *args,
                 bg_color="white", path_color="red", non_path_color="black"):
        """Export a graph as a map image with a path highlighted

        Params:
        graph - The graph to export to a image
        min_lat - The southern border of the map
        max_lat - The northern border of the map
        min_lon - The western border of the map
        max_lon - The eastern border of the map
        non_path_color - The colour of the graph sections in the image
        path_color - The colour of the graph sections that are part of
                     the path
        bg_color - The colour of the image background
        enlargement - Multiplication factor from map coordinate to pixel
                      coordinate. Determines image size.
        """
        super(GraphPathExporter, self).__init__(min_lat, max_lat, min_lon, max_lon, bg_color)
        self.logger = logging.getLogger('.'.join((__name__, type(self).__name__)))

        self.graph = graph
        self.path = path

        self.path_color = path_color
        self.non_path_color = non_path_color

    def export(self, filename="path.png"):
        for section in self.graph.nodes():
            attrs = self.graph.node_attributes(section)
            path = [ ((path[1]-self.min_lon)*self.enlargement, (path[0]-self.min_lat)*self.enlargement) for path in attrs['path'] ]
            if section in self.path:
                self.draw.line(path, fill=self.path_color)
            else:
                self.draw.line(path, fill=self.non_path_color)

        self._save_image(filename)
