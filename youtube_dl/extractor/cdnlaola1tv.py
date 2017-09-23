# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_urllib_parse_urlencode,
    compat_urlparse,
)
from ..utils import (
    ExtractorError,
    sanitized_Request,
    unified_strdate,
    urlencode_postdata,
    xpath_element,
    xpath_text,
)


class CDNLaola1TvIE(InfoExtractor):
    _VALID_URL = r'https?://cdn.laola1.tv/titanplayer.php\?videoid=(?P<videoid>[0-9]+)&type=.+&customer=(?P<customer>[0-9]+)'
    _TEST = {
        'url': 'http://cdn.laola1.tv/titanplayer.php?videoid=694096&type=S&customer=2302&v5ident=&jsdebug=false',
        'info_dict': {
            'id': '694096',
            'ext': 'flv',
            'title': 'Frankreich - Polen',
            'upload_date': '20161204',
            'uploader': u'EHF - Europ\xe4ischer Handball Verband',

            #'thumbnail': 're:^https?://.*\.jpg$',
            # TODO more properties, either as:
            # * A value
            # * MD5 checksum; start the string with md5:
            # * A regular expression; start the string with re:
            # * Any Python type (for example int or float)
        }
    }


    def _real_extract(self, url):
        mobj = re.match(self._VALID_URL, url)

        video_id = mobj.group('videoid');
        partner_id = mobj.group('customer');
        portal='de';
        lang='de';
        display_id="Video_"+video_id;
        kind="livestream";

        webpage = self._download_webpage(url, display_id)

        if 'Dieser Livestream ist bereits beendet.' in webpage:
            raise ExtractorError('This live stream has already finished.', expected=True)

        hd_doc = self._download_xml(
            'http://www.laola1.tv/server/hd_video.php?%s'
            % compat_urllib_parse_urlencode({
                'play': video_id,
                'partner': partner_id,
                'portal': portal,
                'lang': lang,
                'v5ident': '',
            }), display_id)

        _v = lambda x, **k: xpath_text(hd_doc, './/video/' + x, **k)
        title = _v('title', fatal=True)

        VS_TARGETS = {
            'video': '2',
            'livestream': '17',
        }

        #Streamaccess.. it's que url tag in the previous xml download
        req = sanitized_Request(_v('url', fatal=True));

        timestamp = self._search_regex(
            r'flashvars\.timestamp\ =\ \"([0-9]+)\"',
            webpage, 'timestamp')

        auth = self._search_regex(
            r'var\ auth\ =\ \"([0-9a-z]+)\"',
            webpage, 'auth')

        token_url = "%s&ident=%s&klub=0&unikey=0&timestamp=%s&auth=%s" % ( _v('url', fatal=True), "", timestamp, auth )
        token_doc = self._download_xml(token_url, display_id, 'Downloading token')

        token_attrib = xpath_element(token_doc, './/token').attrib
        token_auth = token_attrib['auth']

        if token_auth in ('blocked', 'restricted', 'error'):
            raise ExtractorError(
                'Token error: %s' % token_attrib['comment'], expected=True)

        formats = self._extract_f4m_formats(
            '%s?hdnea=%s&hdcore=3.6.0' % (token_attrib['url'], token_auth),
            video_id, f4m_id='hds')
        self._sort_formats(formats)

        categories_str = _v('meta_sports')
        categories = categories_str.split(',') if categories_str else []

        return {
            'id': video_id,
            'display_id': display_id,
            'title': title,
            'upload_date': unified_strdate(_v('time_date')),
            'uploader': _v('meta_organisation'),
            'categories': categories,
            'is_live': _v('islive') == 'true',
            'formats': formats,
        }
