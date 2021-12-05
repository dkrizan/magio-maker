from datetime import datetime

import ffmpeg


class Recorder:
    def __init__(self, url: str, duration: float):
        self.stream = url
        self.duration = duration

    def start(self, output: str):
        output = 'data/' + output + datetime.strftime(datetime.now(), '%s') + '.ts'
        (
            ffmpeg.input(self.stream)
            .output(output, **{'t': self.duration * 60})
            .run()
         )
