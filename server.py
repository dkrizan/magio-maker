import json
import logging

from flask import Flask, request
from threading import Thread
import os
from datetime import datetime
import pytz

from libs import magioService
from libs.recorder import Recorder

logging.basicConfig(filename='log/errors.log', format='%(asctime)s %(message)s', level=logging.ERROR)

app = Flask('')

service = magioService.Magio(os.environ.get('USERNAME'), os.environ.get('PASSWORD'))


@app.route('/')
def home():
    epg_file = os.path.join(os.path.curdir, 'data/epg.xml')
    if not os.path.exists(epg_file):
        return "No EPG file generated yet"
    time_float = os.path.getmtime(epg_file)
    date = datetime.fromtimestamp(time_float)
    local = date.astimezone(pytz.timezone('Europe/Prague'))
    return "Last updated: " + local.strftime('%d.%m.%Y %H:%M:%S')


@app.route('/record', methods=['POST'])
def record():
    channel = service.get_channel(int(request.form['channel']))
    stream = service.get_stream(channel.id)
    recorder = Recorder(stream, float(request.form['duration']))
    recorder.start(''.join(channel.name.split()).lower() + "-" + datetime.now().isoformat())
    return "Done"


@app.route('/channels')
def channels():
    data = service.get_channels()
    content = {c.id: c.name for (k, c) in data.items()}
    return json.dumps(content)


def run():
    app.run(host='0.0.0.0', port=8080)


def start_flask_thread():
    t = Thread(target=run)
    t.start()
