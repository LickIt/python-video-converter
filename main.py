#!/usr/bin/env python
""" Main module of the converter.
    You can pass the configuration file as a command-line argument. """
import signal
import time
import errno
import sys
import threading
import os
import logging
from converter import Converter
from configuration import Configuration


class Main(object):
    """ The program's main execution class """

    def __init__(self, config_file):
        self.configuration = Configuration.read_from(config_file)
        logging.basicConfig(
            format="[%(levelname)s] %(asctime)s - %(message)s",
            level=logging.getLevelName(self.configuration.loglevel))
        logging.debug(self.configuration.__dict__)
        self._interrupt = threading.Event()
        self._converters = dict()
        self._converters_lock = threading.Lock()

    def sigterm_handler(self, signum, frame):
        """ handle system signals """
        logging.info("Shutting down")
        self._interrupt.set()

    def run(self):
        """ main loop """
        logging.info("Monitoring '%s'", self.configuration.input_directory)

        while not self._interrupt.isSet():
            try:
                # remove finished threads
                with self._converters_lock:
                    self._converters = {k: v for k, v in self._converters.items()
                                        if v.is_alive()}

                # convert new files
                files = self.get_monitored_files()
                with self._converters_lock:
                    for file in files:
                        if file in self._converters:
                            continue

                        self._converters[file] = Converter(
                            file, self.configuration, self._interrupt)
                        self._converters[file].start()

                # if interrupted between sleeps
                if not self._interrupt.isSet():
                    time.sleep(self.configuration.poll_frequency)
            except IOError as ex:
                if ex.errno != errno.EINTR:
                    raise

        logging.info("Waiting for threads to exit")
        for converter in self._converters.values():
            converter.join()

    def get_monitored_files(self):
        """ retrieve list of files in the monitored directory """
        input_directory = self.configuration.input_directory
        video_extensions = self.configuration.video_extensions
        return [os.path.join(input_directory, f) for f in os.listdir(input_directory)
                if os.path.splitext(f)[1][1:] in video_extensions]


configuration_file = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "configuration.ini")
if len(sys.argv) == 2:
    configuration_file = sys.argv[1]
main = Main(configuration_file)

# stop the program gracefully on interrupt and terminate
signal.signal(signal.SIGINT, main.sigterm_handler)
signal.signal(signal.SIGTERM, main.sigterm_handler)

main.run()
