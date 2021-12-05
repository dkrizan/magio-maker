import logging
import os.path
import requests
import time
import argparse

from libs import magioService
from server import start_flask_thread

# config
logging.basicConfig(filename='log/errors.log', format='%(asctime)s %(message)s', level=logging.WARN)

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('--username', type=str, help="Username/login")
parser.add_argument('--password', type=str, help="User password")
parser.add_argument('--back', type=int, default=2, help="Set number of days back to generate EPG (default: 2)")
parser.add_argument('--until', type=int, default=3, help="Set number of days until to generate EPG (default: 3)")
args = parser.parse_args()

# init MagioTV service
service = magioService.Magio(None, None, args.back, args.until)


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


if __name__ == '__main__':
    start_flask_thread()
    generate_epg_constantly(2)
