import logging
import os.path
import requests
import time
import sys

from libs import magioService

# config
logging.basicConfig(filename='log/errors.log', format='%(asctime)s %(message)s', level=logging.WARN)

# init MagioTV service
service = magioService.Magio(None, None, 2, 3)


# hours - n hours to sleep between every generating
def generate_epg_constantly(hours):
    while True:
        epg_file = os.path.dirname(os.path.abspath(__file__)) + "/data/epg.xml"
        service.generate(epg_file)
        print("Uploading to borec")
        r = requests.put('http://epg.borec.cz/datastorage.php', data=open(epg_file, 'rb'))
        if r.status_code == 200:
            print("Done!")
        else:
            logging.error('Uploading to borec.cz failed!')
        time.sleep(hours * 60 * 60)


def runner():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    runner()
    generate_epg_constantly(2)
