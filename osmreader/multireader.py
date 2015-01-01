import logging
import logging.handlers
import multiprocessing as mp
import queue
import xml.etree.ElementTree as ET
import time

from osmreader.elements import Node, Way

logger = logging.getLogger('mapbots.osmreader.multireader')

def _xml_parser(logqueue, elemqueue, filename):
    """Parses XML and puts it in a queue, ran as a subprocess

    Parses the OSM XML and puts the elements in a queue where they can
    be processed by other parts of the program.

    Params:
    logqueue - The queue where log records have to end up in
    elemqueue - Queue where parsed elements end up in so they can be
                handled by the rest of the programs
    filename - The filename of the XML file to parse"""
    # Use only a QueueHandler for the process that runs this code
    # This prevents the process to writing to the log file while the
    # main process also writes to the log file
    h = logging.handlers.QueueHandler(logqueue)
    root = logging.getLogger('mapbots')
    root.handlers = []
    root.addHandler(h)

    # The logger to use for this process
    logger = logging.getLogger('mapbots.osmreader.multireader._xml_parser')
    logger.info("Starting multiprocess XML parser")

    logger.info("Finished parsing XML, exiting parser subprocess")
    elemqueue.put_nowait(None)

class MultiReader:
    """Uses multiprocessing to split XML parsing and parsing nodes."""
    def __init__(self, filename=None):
        self.logger = logging.getLogger('mapbots.osmreader.multireader.MultiReader')
        self.nodes = {}
        self.ways = {}
        if filename is not None:
            self.load(filename)

    def load(self, filename):
        if not isinstance(filename, str):
            raise TypeError("Filename must be the name of a file on an absolute or relative path")
        elif len(filename) == 0:
            raise ValueError("Filename must not be empty")

        logqueue = mp.Queue()
        elemqueue = mp.Queue()

        # Create and start XML parser subprocess
        parser = mp.Process(target=_xml_parser, args=(logqueue, elemqueue, filename))
        parser.start()

        # Main loop
        self.logger.info("Starting multiprocess main loop")
        running = True
        while running:
            # Handle XML elements
            try:
                # Get the next element in the XML file
                elem = elemqueue.get(False)
            except queue.Empty:
                pass
            else:
                # Finish if there are no more elements to parse
                if elem is None:
                    running = False
                # Handle elements

            # Handle queued log messages
            try:
                while True:
                    record = logqueue.get(False)
                    logger = logging.getLogger(record.name)
                    logger.handle(record)
            except queue.Empty:
                # There are no more log messages to handle, move back
                # to handling XML elements
                pass
        parser.join()
        self.logger.info("Finished multiprocess main loop")
