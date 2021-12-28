import os
from typing import List, Dict

import requests
import time
import random
import json
from datetime import datetime, timedelta

from requests.adapters import HTTPAdapter, Retry

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:83.0) Gecko/20100101 Firefox/83.0'

html_escape_table = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
}


def html_escape(text):
    return "".join(html_escape_table.get(c, c) for c in text)


class SessionData:
    def __init__(self):
        self.access_token = ''
        self.refresh_token = ''
        self.expires_in = 0
        self.type = ''


class MagioGoDevice:
    def __init__(self):
        self.id = ''
        self.name = ''
        self.expiration_time = None
        self.is_this = False


class Base:
    def __repr__(self):
        return str(__dict__)


class MagioGoException(BaseException):
    def __init__(self, message, code):
        self.message = message
        self.code = code


class Channel(Base):
    def __init__(self):
        # channel Unique Id
        self.id = None  # type: int or None
        # channel name
        self.name = ''
        # channel icon absolute url
        self.logo = ''
        # marks channel as pin protected
        self.is_pin_protected = False
        # if not 0 channel supports archive/catchup/replay
        self.archive_days = 0
        # channel metadata
        self.metadata = {}


class Programme(Base):
    def __init__(self):
        self.id = None  # type: int or None
        # Programme Start Time in UTC
        self.start_time = None  # type: datetime or None
        # Programme End Time in UTC
        self.end_time = None  # type: datetime or None
        self.title = ''
        self.description = ''
        self.thumbnail = ''
        self.poster = ''
        self.duration = 0
        self.genres = []  # type: List[str]
        self.actors = []  # type: List[str]
        self.directors = []  # type: List[str]
        self.writers = []  # type: List[str]
        self.producers = []  # type: List[str]
        self.seasonNo = None
        self.episodeNo = None
        self.year = None  # type: int or None
        self.is_replyable = False
        # programme metadata
        self.metadata = {}  # type: Dict[str, int]


class Magio:
    def __init__(self, username, password, from_days=2, until_days=3):
        self._data = SessionData()
        self.user = username
        self.password = password
        self.from_days = from_days
        self.to_days = until_days
        self._channels = {}
        self.storage_file = os.path.join(os.path.curdir, 'store.json')

    def _store_session(self, data):
        with open(self.storage_file, 'w+') as f:
            json.dump(data.__dict__, f)

    def _load_session(self, data):
        if os.path.exists(self.storage_file):
            with open(self.storage_file, 'r') as f:
                data.__dict__ = json.load(f)

    def _load_channels(self) -> Dict:
        self._access()
        resp = self._get('https://skgo.magio.tv/v2/television/channels',
                         params={'list': 'LIVE', 'queryScope': 'LIVE'},
                         headers=self._auth_headers())
        ret = {}
        for i in resp['items']:
            i = i['channel']
            c = Channel()
            c.id = int(i['channelId'])
            c.name = i['name']
            c.logo = i['logoUrl']
            if i['hasArchive']:
                c.archive_days = 7
            ret[c.id] = c
        self._channels = ret
        return ret

    def get_stream(self, channel_id):
        self._login()
        resp = self._get('https://skgo.magio.tv/v2/television/stream-url',
                         params={'service': 'LIVE', 'name': 'TV', 'devtype': 'OTT_ANDROID',
                                 'id': channel_id, 'prof': 'p3', 'ecid': '', 'drm': 'verimatrix'},
                         headers=self._auth_headers())
        return resp['url']

    def get_channels(self):
        if not self._channels:
            self._load_channels()
        return self._channels

    def get_channel(self, channel_id) -> Channel:
        return self.get_channels()[channel_id]

    def _epg(self, channels, from_date, to_date):
        self._login()
        ret = {}

        from_date = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
        to_date = to_date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        now = datetime.utcnow()

        days = int((to_date - from_date).days)

        for n in range(days):
            current_day = from_date + timedelta(n)
            time_filter = 'startTime=ge=%sT00:00:00.000Z;startTime=le=%sT00:59:59.999Z' % (
                current_day.strftime("%Y-%m-%d"), (current_day + timedelta(days=1)).strftime("%Y-%m-%d"))

            fetch_more = True
            offset = 0
            while fetch_more:
                resp = self._get('https://skgo.magio.tv/v2/television/epg',
                                 params={'filter': time_filter, 'limit': '100', 'offset': offset * 20, 'list': 'LIVE'},
                                 headers=self._auth_headers())

                fetch_more = len(resp['items']) == 100
                offset = offset + 1

                for i in resp['items']:
                    for p in i['programs']:
                        channel = str(p['channel']['id'])

                        if channel not in channels:
                            continue

                        if channel not in ret:
                            ret[channel] = []

                        programme = self._programme_data(p['program'])
                        programme.start_time = datetime.utcfromtimestamp(p['startTimeUTC'] / 1000)
                        programme.end_time = datetime.utcfromtimestamp(p['endTimeUTC'] / 1000)
                        programme.duration = p['duration']
                        programme.is_replyable = (programme.start_time > (now - timedelta(days=7))) and (
                                programme.end_time < now)

                        ret[channel].append(programme)

        return ret

    def _access(self):
        self._post('https://skgo.magio.tv/v2/auth/init',
                   params={'dsid': 'Netscape.' + str(int(time.time())) + '.' + str(random.random()),
                           'deviceName': 'TV',
                           'deviceType': 'OTT_ANDROID',
                           'osVersion': '0.0.0',
                           'appVersion': '0.0.0',
                           'language': 'SK'},
                   headers={'Origin': 'https://www.magiogo.sk', 'Pragma': 'no-cache',
                            'Referer': 'https://www.magiogo.sk/', 'User-Agent': UA,
                            'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'cross-site'})

    def devices(self):
        # type: () -> List[MagioGoDevice]
        def make_device(i, is_this):
            device = MagioGoDevice()
            device.id = str(i['id'])
            device.name = i['name']
            device.expiration_time = self._strptime(i['verimatrixExpirationTime'], "%Y-%m-%dT%H:%M:%S.%fZ")
            device.is_this = is_this
            return device

        self._login()
        resp = self._get('https://skgo.magio.tv/home/listDevices', headers=self._auth_headers())

        devices = [make_device(i, False) for i in resp['items']]

        if resp['thisDevice']:
            devices.append(make_device(resp['thisDevice'], True))
        return devices

    def _login(self):
        self._load_session(self._data)

        if not self._data.access_token:
            self._access()
            self._post('https://skgo.magio.tv/v2/auth/login',
                       jsonData={'loginOrNickname': self.user, 'password': self.password},
                       headers=self._auth_headers())

        if self._data.refresh_token and self._data.expires_in < int(time.time() * 1000):
            self._post('https://skgo.magio.tv/v2/auth/tokens',
                       jsonData={'refreshToken': self._data.refresh_token},
                       headers=self._auth_headers())

    def _post(self, url, data=None, jsonData=None, **kwargs):
        try:
            resp = self._request().post(url, data=data, json=jsonData, **kwargs).json()
            self._check_response(resp)
            return resp
        except requests.exceptions.ConnectionError as err:
            raise ConnectionError(str(err))
        except MagioGoException as e:
            if self._is_max_device_limit(e):
                resp = self._request().post(url, data=data, json=jsonData, **kwargs).json()
                self._check_response(resp)
                return resp

    def disconnect_device(self, device_id):
        # type: (str) -> None
        self._login()
        self._get('https://skgo.magio.tv/home/deleteDevice', params={'id': device_id}, headers=self._auth_headers())


    def _auth_headers(self):
        return {'Authorization': self._data.type + ' ' + self._data.access_token,
                'Origin': 'https://www.magiogo.sk', 'Pragma': 'no-cache', 'Referer': 'https://www.magiogo.sk/',
                'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Site': 'cross-site', 'User-Agent': UA}

    def _check_response(self, resp):
        if resp['success']:
            if 'token' in resp:
                self._data.access_token = resp['token']['accessToken']
                self._data.refresh_token = resp['token']['refreshToken']
                self._data.expires_in = resp['token']['expiresIn']
                self._data.type = resp['token']['type']
                self._store_session(self._data)
        else:
            self._store_session(SessionData())
            raise MagioGoException(str(resp['errorMessage']), resp['errorCode'])

    def _is_max_device_limit(self, e):
        if e.code == 'DEVICE_MAX_LIMIT':
            device = min([d for d in self.devices() if not d.is_this])
            self.disconnect_device(device.id)
            return True
        return False

    def _get(self, url, params=None, **kwargs):
        try:
            resp = self._request().get(url, params=params, **kwargs).json()
            self._check_response(resp)
            return resp
        except requests.exceptions.ConnectionError as err:
            raise ConnectionError(str(err))
        except MagioGoException as e:
            if self._is_max_device_limit(e):
                resp = self._request().get(url, params=params, **kwargs).json()
                self._check_response(resp)
                return resp

    def _programme_data(self, pi):
        def safe_int(value, default=None):
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        programme = Programme()
        programme.id = pi['programId']
        programme.title = pi['title']
        programme.description = pi['description']

        pv = pi['programValue']
        if pv['episodeId'] is not None:
            programme.episodeNo = safe_int(pv['episodeId'])
        if pv['seasonNumber'] is not None:
            programme.seasonNo = safe_int(pv['seasonNumber'])
        if pv['creationYear'] is not None:
            programme.year = safe_int(pv['creationYear'])
        for i in pi['images']:
            programme.thumbnail = i
            break
        for i in pi['images']:
            if "_VERT" in i:
                programme.poster = i
                break
        for d in pi['programRole']['directors']:
            programme.directors.append(d['fullName'])
        for a in pi['programRole']['actors']:
            programme.actors.append(a['fullName'])
        if pi['programCategory'] is not None:
            for c in pi['programCategory']['subCategories']:
                programme.genres.append(c['desc'])

        return programme

    def create_epg(self, file_name, epg):
        with open(file_name, 'w', encoding='utf8') as file:
            file.write('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
            file.write('<tv>\n')

            for channel_id in epg:
                file.write('<channel id="%s">\n' % channel_id)
                file.write('</channel>\n')

            for channel_id in epg:
                for p in epg[channel_id]:
                    file.write('<programme channel="%s" start="%s" stop="%s">\n' % (
                        channel_id, p.start_time.strftime('%Y%m%d%H%M%S'), p.end_time.strftime('%Y%m%d%H%M%S')))
                    if p.title:
                        file.write('<title>%s</title>\n' % html_escape(p.title))
                    if p.description:
                        file.write('<desc>%s</desc>\n' % html_escape(p.description))
                    if p.thumbnail:
                        file.write('<icon src="%s"/>\n' % html_escape(p.thumbnail))
                    if p.genres:
                        file.write('<category>%s</category>\n' % html_escape(', '.join(p.genres)))
                    if p.actors or p.directors or p.writers or p.producers:
                        file.write('<credits>\n')
                        for actor in p.actors:
                            file.write('<actor>%s</actor>\n' % html_escape(actor))
                        for director in p.directors:
                            file.write('<director>%s</director>\n' % html_escape(director))
                        for writer in p.writers:
                            file.write('<writer>%s</writer>\n' % html_escape(writer))
                        for producer in p.producers:
                            file.write('<producer>%s</producer>\n' % html_escape(producer))
                        file.write('</credits>\n')
                    if p.seasonNo and p.episodeNo:
                        file.write(
                            '<episode-num system="xmltv_ns">%d.%d.</episode-num>\n' % (p.seasonNo - 1, p.episodeNo - 1))
                    file.write('</programme>\n')
            file.write('</tv>\n')

    def _request(self):
        session = requests.Session()
        session.mount('https://',
                      HTTPAdapter(
                          max_retries=Retry(total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])))
        return session

    @staticmethod
    def _strptime(date_string, format):
        # https://forum.kodi.tv/showthread.php?tid=112916 it's insane !!!
        try:
            return datetime.strptime(date_string, format)
        except TypeError:
            import time as ptime
            return datetime(*(ptime.strptime(date_string, format)[0:6]))

    def generate(self, output):
        print("Fetching channels")
        channels = self._load_channels()
        print("Found " + str(len(channels)) + " channels")

        print("Fetching EPG")
        now = datetime.now()
        data = self._epg(channels.keys(), now - timedelta(days=self.from_days),
                         now + timedelta(days=self.to_days))

        print("Building XMLTV file")
        self.create_epg(output, data)

        return True
