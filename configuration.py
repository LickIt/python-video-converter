#!/usr/bin/env python
import os.path
import configparser


class Configuration(object):

    def __init__(self, profile, input_directory, output_directory, video_extensions, poll_frequency, loglevel):
        self.profile = profile
        self.input_directory = os.path.realpath(input_directory)
        self.video_extensions = video_extensions.split(",")
        self.output_directory = os.path.realpath(output_directory)
        self.poll_frequency = int(poll_frequency)
        self.loglevel = loglevel.upper()
        self.profile_instance = None

    @staticmethod
    def read_from(file):
        config = configparser.ConfigParser()
        config.read(file)

        instance = Configuration(**dict(config.items("main")))
        instance.profile_instance = Configuration.Profile(
            **dict(config.items("profile|" + instance.profile)))
        return instance

    class Profile(object):

        def __init__(self, encoder, parameters):
            self.encoder = encoder
            self.parameters = parameters
