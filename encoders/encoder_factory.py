""" Factory module for encoders """
from .ffmpeg import FFMpegEncoder
from .ffmpeg import FFMpegConfiguration


class EncoderFactory(object):
    """ Factory class for creating encoders and encoding profiles """

    ENCODERS = {"ffmpeg": (FFMpegEncoder, FFMpegConfiguration)}

    @staticmethod
    def get_encoder_definition(encoder_name):
        """ Get encoder definition in the form (EncoderClass, EncoderConfigurationClass) """

        if encoder_name not in EncoderFactory.ENCODERS:
            raise RuntimeError("Unsupported encoder '{}'".format(encoder_name))

        return EncoderFactory.ENCODERS[encoder_name]

    @staticmethod
    def create_encoding_profile(profile_parameters):
        """ Create encoder profile instance based on cofiguration """

        encoder_name = profile_parameters["encoder"]
        config_class = EncoderFactory.get_encoder_definition(encoder_name)[1]
        return config_class(**profile_parameters)

    @staticmethod
    def create_encoder(input_file, configuration, interrupt):
        """ Create encoder instance for the specified file based on the configuration """

        encoder_name = configuration.profile_instance.encoder
        encoder_class = EncoderFactory.get_encoder_definition(encoder_name)[0]
        return encoder_class(input_file, configuration, interrupt, configuration.profile_instance)
