#!/usr/bin/env python
import threading
import time
import logging


class Converter(threading.Thread):

    def __init__(self, file, configuration, interrupt):
        threading.Thread.__init__(self)
        self._file = file
        self._configuration = configuration
        self._interrupt = interrupt

    def run(self):
        logging.info("Star converting '%s'", self._file)
        time.sleep(15)
        logging.info("Done converting '%s'", self._file)
