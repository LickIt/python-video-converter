#!/usr/bin/env python
""" Module for converting video files """
import threading
import logging
import os
import subprocess


class Converter(threading.Thread):
    """ Class for converting files """

    def __init__(self, file, configuration, interrupt):
        threading.Thread.__init__(self)
        self._file = file
        self._configuration = configuration
        self._interrupt = interrupt

    @staticmethod
    def ensure_directory(path):
        """ Ensure the path exists """
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def process_stderr(stream, interrupt):
        """ read process stderr in separate thread because it's blocking """
        for line in iter(stream.readline, b''):
            if interrupt.isSet():
                break
            logging.error(line.decode("UTF-8").rstrip(os.linesep))
        stream.close()

    def run(self):
        """ thread entry point """
        logging.info("Start converting '%s'", self._file)

        # construct output file path
        base_filename = os.path.splitext(os.path.basename(self._file))[0]
        output_filename = os.path.join(
            self._configuration.output_directory, base_filename + ".mp4")

        # create encoder process
        self.ensure_directory(output_filename)
        profile = self._configuration.profile_instance
        parameters = profile.parameters.replace("${input}", self._file)
        parameters = parameters.replace(
            "${escaped_input}",
            self._file.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'"))
        parameters = parameters.replace("${output}", output_filename)
        logging.debug(parameters)
        proc = subprocess.Popen(
            [profile.encoder] + parameters.split(), bufsize=1, stderr=subprocess.PIPE)

        # log stderr
        stderr_thread = threading.Thread(
            target=self.process_stderr, args=(proc.stderr, self._interrupt))
        stderr_thread.start()

        # wait for process exit
        while proc.poll() is None:
            if self._interrupt.isSet():
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

            self._interrupt.wait(timeout=10)

        # cleanup
        stderr_thread.join()
        if proc.returncode != 0:
            logging.error("Converting exited with code %d", proc.returncode)
            return

        if self._configuration.complete_action == "delete":
            os.remove(self._file)
        elif self._configuration.complete_action == "rename":
            os.rename(self._file, os.path.splitext(self._file) + ".done")

        logging.info("Done converting '%s'", self._file)
