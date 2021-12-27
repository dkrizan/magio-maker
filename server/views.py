from django.http import HttpResponse, HttpRequest
import json
import logging

import os
from datetime import datetime
import pytz
from django.views.decorators.csrf import csrf_exempt
import requests

from libs import magioService
from libs.recorder import Recorder
from multiprocessing import Pool

logging.basicConfig(filename='log/errors.log', format='%(asctime)s %(message)s', level=logging.ERROR)

username = os.environ.get('USERNAME')
password = os.environ.get('PASSWORD')
if username is None or password is None:
    raise EnvironmentError('Environmental variables "USERNAME" or "PASSWORD" are missing')

service = magioService.Magio(os.environ.get('USERNAME'), os.environ.get('PASSWORD'), 2, 3)


def index(request):
    epg_file = os.path.join(os.path.curdir, 'data/epg.xml')
    if not os.path.exists(epg_file):
        return "No EPG file generated yet"
    time_float = os.path.getmtime(epg_file)
    date = datetime.fromtimestamp(time_float)
    local = date.astimezone(pytz.timezone('Europe/Prague'))
    return HttpResponse("Last updated: " + local.strftime('%d.%m.%Y %H:%M:%S'))


@csrf_exempt
def record(request: HttpRequest):
    channel = service.get_channel(int(request.POST.get('channel')))
    stream = service.get_stream(channel.id)
    recorder = Recorder(stream, float(request.POST.get('duration')))
    recorder.start(''.join(channel.name.split()).lower() + "-" + datetime.now().isoformat())
    return HttpResponse("Done")


def channels(request):
    data = service.get_channels()
    content = {c.id: c.name for (k, c) in data.items()}
    return HttpResponse(json.dumps(content))


def _run_generating_epg():
    epg_file = os.path.dirname(os.path.abspath(__file__)) + "/../data/epg.xml"
    service.generate(epg_file)
    print("Uploading to borec")
    r = requests.put('http://epg.borec.cz/datastorage.php', data=open(epg_file, 'rb'))
    if r.status_code == 200:
        print("Done!")
    else:
        logging.error('Uploading to borec.cz failed!')


# generate epg and upload to borec
def generate_epg(request):
    pool = Pool(processes=1)
    pool.apply_async(_run_generating_epg)
    return HttpResponse("Epg creating started !")

