""" Module for encoding files with ffmpeg """
import os
import json
import logging
import subprocess
import threading
from enum import Enum
from .encoder import Encoder


class FFMpegEncoder(Encoder):
    """ FFMpeg encoder class """

    def __init__(self, input_file, configuration, interrupt, profile_instance):
        super().__init__(input_file, configuration, interrupt)
        self.configuration = profile_instance
        self.executable = os.path.join(self.configuration.executable_directory, "ffmpeg") \
            if self.configuration.executable_directory else "ffmpeg"

    @staticmethod
    def process_stderr(stream, interrupt):
        """ Read process stderr in separate thread because it's blocking """

        for line in iter(stream.readline, b''):
            if interrupt.isSet():
                break
            logging.error(line.decode("UTF-8").rstrip(os.linesep))
        stream.close()

    @staticmethod
    def escape_filter_value(value):
        """ Escape all special characters in filter values """

        return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

    def encode(self):
        """ Encoding method from super class contract """

        # get streams info with FFProbe
        ffprobe = FFProbe(
            self.input_file, self.configuration.executable_directory)
        if not ffprobe.run():
            return False

        args = self.construct_args(ffprobe)
        logging.debug("Executing ffmpeg with parameters: %s", " ".join(args))
        proc = subprocess.Popen(args, bufsize=1, stderr=subprocess.PIPE)

        # log stderr
        stderr_thread = threading.Thread(
            target=self.process_stderr, args=(proc.stderr, self.interrupt))
        stderr_thread.start()

        # wait for process exit
        while proc.poll() is None:
            if self.interrupt.isSet():
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()

            self.interrupt.wait(timeout=10)

        # cleanup
        stderr_thread.join()
        if proc.returncode != 0:
            logging.error("ffmpeg exited with code %d", proc.returncode)
            return False

        return True

    def construct_args(self, ffprobe):
        """ Construct the process start arguments """

        video_stream = ffprobe.get_video_stream()
        audio_stream = ffprobe.get_audio_stream(
            self.configuration.audio_language)
        subtitle_stream = ffprobe.get_subtitle_stream(
            self.configuration.subtitle_language)

        args = [self.executable, "-i", self.input_file]

        # mappings and disposition
        args += ["-map", "0:" + str(video_stream["index"])]
        args += ["-map", "0:" + str(audio_stream["index"])]
        args += ["-disposition:1", "default"]
        if self.configuration.subtitles_action == FFMpegSubtitleAction.EMBED:
            args += ["-map", "0:" + str(subtitle_stream["index"])]
            args += ["-disposition:2", "default"]

        # codecs
        args += self.configuration.video_parameters.split()
        args += self.configuration.audio_parameters.split()
        if subtitle_stream and self.configuration.subtitles_action == FFMpegSubtitleAction.BURNIN:
            args += ["-vf",
                     "subtitles='{}'".format(self.escape_filter_value(self.input_file))]

        # misc arguments
        if self.configuration.executable_parameters:
            args += self.configuration.executable_parameters.split()
        args += ["-f", "mp4", self.output_file]
        return args


class FFMpegConfiguration(object):
    """ Configuration class for storing ffmpeg encoder parameters """

    def __init__(self, encoder, video_parameters, audio_parameters, subtitles="embed",
                 audio_language=None, subtitle_language=None,
                 executable_directory=None, executable_parameters=None):
        self.encoder = encoder
        self.video_parameters = video_parameters
        self.audio_parameters = audio_parameters
        self.subtitles_action = FFMpegSubtitleAction[subtitles.upper()]
        self.audio_language = [x.strip() for x in audio_language.split(",")] \
            if audio_language else None
        self.subtitle_language = [x.strip() for x in subtitle_language.split(",")] \
            if subtitle_language else None
        self.executable_directory = os.path.abspath(executable_directory) \
            if executable_directory else None
        self.executable_parameters = executable_parameters

    def __repr__(self):
        return repr(self.__dict__)


class FFMpegSubtitleAction(Enum):
    """ Subtitle action constants """

    BURNIN = 1
    EMBED = 2
    NONE = 3
    # EXTRACT = 4


class FFProbe(object):
    """ FFProbe helper class to get stream information """

    def __init__(self, input_file, executable_directory):
        self.input_file = input_file
        self.executable = os.path.join(
            executable_directory, "ffprobe") if executable_directory else "ffprobe"
        self.json = None

    def run(self):
        """ Run ffprobe for the input file to get information about the streams """

        parameters = [self.executable,
                      "-i", self.input_file,
                      "-show_streams",
                      "-loglevel", "quiet",
                      "-print_format", "json"]

        logging.debug("Executing ffprobe with parameters: %s", parameters)
        proc = subprocess.Popen(parameters, bufsize=1,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # timeout after 60 seconds
        (stdout, stderr) = proc.communicate(timeout=60)

        if proc.returncode != 0:
            if len(stderr) > 0:
                logging.error(stderr.decode("UTF-8"))
            logging.error("ffprobe exited with code %d", proc.returncode)
            return False

        self.json = json.loads(stdout.decode("UTF-8"))
        return True

    @staticmethod
    def get_default_stream(streams):
        """ Get the default stream in a list of streams if there is one.
            Otherwise return the first stream. """

        if len(streams) == 0:
            return None

        default = [s for s in streams if "disposition" in s
                   and "default" in s["disposition"]
                   and s["disposition"]["default"] == 1]

        if len(default) > 0:
            return default[0]

        return streams[0]

    @staticmethod
    def get_stream_language(stream):
        """ Get the stream language if it is specified """

        if "tags" in stream and "language" in stream["tags"]:
            return stream["tags"]["language"]

        return None

    def get_streams_by_type(self, _type):
        """ Get all streams by stream type """

        return [s for s in self.json["streams"]
                if s["codec_type"] == _type]

    def get_video_stream(self):
        """ Get the video stream index """

        streams = self.get_streams_by_type("video")
        return self.get_default_stream(streams)

    def get_audio_stream(self, audio_language):
        """ Get the audio stream index """

        streams = self.get_streams_by_type("audio")
        if audio_language:
            for lang in audio_language:
                filtered = [s for s in streams if
                            self.get_stream_language(s) == lang]
                if len(filtered) > 0:
                    return self.get_default_stream(filtered)

        return self.get_default_stream(streams)

    def get_subtitle_stream(self, subtitle_language):
        """ Get the audio stream index """

        streams = self.get_streams_by_type("subtitle")
        if subtitle_language:
            for lang in subtitle_language:
                filtered = [s for s in streams if
                            self.get_stream_language(s) == lang]
                if len(filtered) > 0:
                    return self.get_default_stream(filtered)

        return self.get_default_stream(streams)
