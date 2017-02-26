""" Module for encoding video files """
import threading
import logging
import os
from configuration import EncodingCompleteAction


class Encoder(threading.Thread):
    """ Abstract base class for encoding """

    def __init__(self, input_file, configuration, interrupt):
        super().__init__()

        input_file = os.path.realpath(input_file)
        base_filename = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(
            configuration.output_directory, base_filename + ".mp4")

        self.input_file = input_file
        self.output_file = output_file
        self.interrupt = interrupt
        self.complete_action = configuration.complete_action

    @staticmethod
    def ensure_directory(path):
        """ Ensure the path exists """
        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def run(self):
        """ Thread entry point """
        logging.info("Start converting '%s'", self.input_file)

        self.output_file += ".tmp"
        self.ensure_directory(self.output_file)

        try:
            if not self.encode():
                raise RuntimeError(
                    "Failed to encode file '{0}'".format(self.input_file))
            os.rename(self.output_file, self.output_file[:-4])

            if self.complete_action == EncodingCompleteAction.DELETE:
                os.remove(self.input_file)
            elif self.complete_action == EncodingCompleteAction.RENAME:
                os.rename(self.input_file, self.input_file + ".done")

        except (RuntimeError, OSError) as ex:
            # we can probably recover from these exceptions
            logging.exception(ex)
        finally:
            # remove temp file if present
            if os.path.exists(self.output_file):
                os.remove(self.output_file)

        logging.info("Done converting '%s'", self.input_file)

    def encode(self):
        """ Encoding method. Must be implemented in subclasses """

        raise NotImplementedError()
