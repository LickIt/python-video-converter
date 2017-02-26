""" Module for configuration classes """
import os.path
from enum import Enum
import configparser


class Configuration(object):
    """ The program configuration representation """

    def __init__(self, profile, input_directory, output_directory,
                 video_extensions, complete_action, poll_frequency="60", loglevel="info"):
        self.profile = profile
        self.input_directory = os.path.abspath(input_directory)
        self.video_extensions = video_extensions.split(",")
        self.output_directory = os.path.abspath(output_directory)
        self.poll_frequency = int(poll_frequency)
        self.loglevel = loglevel.upper()
        self.complete_action = EncodingCompleteAction[complete_action.upper()]
        self.profile_instance = None

    def __repr__(self):
        return repr(self.__dict__)

    @staticmethod
    def read_from(file, create_profile):
        """ Read configuration from file """

        config = configparser.ConfigParser()
        config.read(file)

        instance = Configuration(**dict(config.items("default")))
        instance.profile_instance = create_profile(
            dict(config.items("profile|" + instance.profile)))
        return instance


class EncodingCompleteAction(Enum):
    """ Action to invoke on the input file after encoding """

    DELETE = 1
    RENAME = 2
