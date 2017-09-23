# coding: utf-8
from __future__ import unicode_literals

import json
import re

from .common import InfoExtractor
from ..utils import (
    ExtractorError,
    unified_strdate,
    urlencode_postdata,
    xpath_element,
    xpath_text,
    update_url_query,
    js_to_json,
)

class EhfTvBaseIE(InfoExtractor):
    def _extract_token_url(self, stream_access_url, video_id, data):
        return self._download_json(
            stream_access_url, video_id, headers={
                'Content-Type': 'application/json',
            }, data=json.dumps(data).encode())['data']['stream-access'][0]

    def _extract_formats(self, token_url, video_id):
        token_doc = self._download_xml(
            token_url, video_id, 'Downloading token',
            headers=self.geo_verification_headers())

        token_attrib = xpath_element(token_doc, './/token').attrib

        if token_attrib['status'] != '0':
            raise ExtractorError(
                'Token error: %s' % token_attrib['comment'], expected=True)

        formats = self._extract_akamai_formats(
            '%s?hdnea=%s' % (token_attrib['url'], token_attrib['auth']),
            video_id)
        self._sort_formats(formats)
        return formats


class EhfTvIE(EhfTvBaseIE):
    IE_NAME = 'ehftv'
    _VALID_URL = r'https?://(?:www\.)?ehftv\.com/(?P<portal>[a-z]+)/(?P<kind>[^/]+)/(?P<slug>[^/?#&]+)'
    _TESTS = []

    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)
        display_id = mobj.group('slug')

        webpage = self._download_webpage(url, display_id)

        if 'Dieser Livestream ist bereits beendet.' in webpage:
            raise ExtractorError('This live stream has already finished.', expected=True)

        conf = self._parse_json(self._search_regex(
            r'(?s)conf\s*=\s*({.+?});', webpage, 'conf'),
            display_id, js_to_json)

        video_id = conf['videoid']

        config = self._download_json(conf['configUrl'], video_id, query={
            'videoid': video_id,
            'partnerid': conf['partnerid'],
            'language': conf.get('language', ''),
            'portal': conf.get('portalid', ''),
        })
        error = config.get('error')
        if error:
            raise ExtractorError('%s said: %s' % (self.IE_NAME, error), expected=True)

        video_data = config['video']
        title = video_data['title']
        is_live = video_data.get('isLivestream') and video_data.get('isLive')
        meta = video_data.get('metaInformation')
        sports = meta.get('sports')
        categories = sports.split(',') if sports else []

        token_url = self._extract_token_url(
            video_data['streamAccess'], video_id,
            video_data['abo']['required'])

        formats = self._extract_formats(token_url, video_id)

        return {
            'id': video_id,
            'display_id': display_id,
            'title': self._live_title(title) if is_live else title,
            'description': video_data.get('description'),
            'thumbnail': video_data.get('image'),
            'categories': categories,
            'formats': formats,
            'is_live': is_live,
        }

