import os
from datetime import datetime

import ffmpeg
import logging

cmd = os.environ.get('FFMPEG_PATH')


class Recorder:
    def __init__(self, url: str, duration: float):
        self.stream = url
        self.duration = duration

    def start(self, output: str):
        try:
            output = 'data/' + output + datetime.strftime(datetime.now(), '%s') + '.ts'
            (
                ffmpeg.input(self.stream)
                .output(output, **{'t': self.duration * 60})
                .run(capture_stdout=True, capture_stderr=True, **(dict(cmd=cmd) if cmd is not None else dict()))
            )
        except ffmpeg.Error as e:
            print('stdout:', e.stdout.decode('utf8'))
            print('stderr:', e.stderr.decode('utf8'))
            logging.error(e.stderr.decode('utf8'))
            raise e
