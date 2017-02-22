#!/usr/bin/env python
import signal
import time
import errno
import sys
import configparser
import threading
import os


class Main(object):

    def __init__(self, configuration_file):
        config = configparser.ConfigParser()
        config.read(configuration_file)
        self.configuration = dict(config.items("main"))
        self.profile = dict(config.items(
            "profile|" + self.configuration["profile"]))
        self._interrupt = threading.Event()
        self._converters = dict()
        self._converters_lock = threading.Lock()

    def sigterm_handler(self, signum, frame):
        print("Shutting down...")
        self._interrupt.set()

    def run(self):
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
                            file, self.profile, self._interrupt)
                        self._converters[file].start()

                # if interrupted between sleeps
                if not self._interrupt.isSet():
                    time.sleep(3)
            except IOError as ex:
                if ex.errno != errno.EINTR:
                    raise

        print("Waiting for threads to exit...")
        for converter in self._converters.values():
            converter.join()

    def get_monitored_files(self):
        input_directory = self.configuration["input_directory"]
        video_extensions = self.configuration["video_extensions"].split(",")
        return [os.path.join(input_directory, f) for f in os.listdir(input_directory)
                if os.path.splitext(f)[1][1:] in video_extensions]


class Converter(threading.Thread):

    def __init__(self, file, profile, interrupt):
        threading.Thread.__init__(self)
        self._file = file
        self._profile = profile
        self._interrupt = interrupt

    def run(self):
        print("Converting " + self._file)
        time.sleep(15)
        print("Done")


configuration_file = "configuration.ini"
if len(sys.argv) == 2:
    configuration_file = sys.argv[1]
main = Main(configuration_file)

signal.signal(signal.SIGINT, main.sigterm_handler)
signal.signal(signal.SIGTERM, main.sigterm_handler)

main.run()
