#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#      Copyright (C) 2016 Yllar Pajus
#      http://pilves.eu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
import re
import os
import sys
import urllib2
import urlparse
from datetime import datetime
import time
import json

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

import buggalo


class PostimeesException(Exception):
    pass


class Postimees(object):

    def download_url(self, url):
        for retries in range(0, 5):
            try:
                r = urllib2.Request(url.encode('iso-8859-1', 'replace'))
                r.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1')
                http_handler = urllib2.HTTPHandler(debuglevel=0)  # http debug
                https_handler = urllib2.HTTPSHandler(debuglevel=0)  # https debug
                opener = urllib2.build_opener(http_handler, https_handler)

                urllib2.install_opener(opener)
                u = urllib2.urlopen(r)
                # u = urllib2.urlopen(r, timeout = 30)
                contents = u.read()
                u.close()
                return contents
            except Exception, ex:
                if retries > 5:
                    raise PostimeesException(ex)

    def list_channels(self):
        url = 'https://services.postimees.ee/rest/v1/sections/81/events'
        items = list()
        data = self.download_url(url)
        if not data:
            raise PostimeesException(ADDON.getLocalizedString(203).encode('utf-8'))
        data = json.loads(data)
        for node in data:
            if node.get('article'):
                if node['article']['isPremium'] is False and node['article']['meta']['videoCount'] == 1:
                    try:
                        start_time = datetime.strptime(node['startDate'][:-6], '%Y-%m-%dT%H:%M:%S').strftime(
                            "%d.%b %H:%M")
                    except TypeError:
                        start_time = datetime(
                            *(time.strptime(node['startDate'][:-6], '%Y-%m-%dT%H:%M:%S')[0:6])).strftime(
                            "%d.%b %H:%M")  # workaround for stupid bug
                    title = "%s - %s" % (start_time, node['headline'])
                    item = xbmcgui.ListItem(title, iconImage=FANART)
                    item.setProperty('IsPlayable', 'true')
                    item.setProperty('Fanart_Image', FANART)
                    items.append(
                        (PATH + '?url=http:%s&title=%s' % (node['link'], title), item, False))  # isFolder=False
        xbmcplugin.addDirectoryItems(HANDLE, items)
        xbmcplugin.endOfDirectory(HANDLE)

    def get_video_id(self, url):
        html = self.download_url(url)
        regex = 'video-sources="([^,]+)'
        for videoid in re.findall(regex, html):
            return videoid

    def play_stream(self, url, title):
        saade = self.get_video_id(url)
        buggalo.addExtraData('saade', saade)
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()

        item = xbmcgui.ListItem(title, iconImage=ICON, path=saade)
        playlist.add(saade, item)
        xbmcplugin.setResolvedUrl(HANDLE, True, item)

    def display_error(self, message='n/a'):
        heading = buggalo.getRandomHeading()
        line1 = ADDON.getLocalizedString(200).encode('utf-8')
        line2 = ADDON.getLocalizedString(201).encode('utf-8')
        xbmcgui.Dialog().ok(heading, line1, line2, message)


if __name__ == '__main__':
    ADDON = xbmcaddon.Addon()
    PATH = sys.argv[0]
    HANDLE = int(sys.argv[1])
    PARAMS = urlparse.parse_qs(sys.argv[2][1:])
    ICON = os.path.join(ADDON.getAddonInfo('path'), 'icon.png')
    FANART = os.path.join(ADDON.getAddonInfo('path'), 'fanart.png')

    buggalo.SUBMIT_URL = 'https://pilves.eu/exception/submit.php'
    PostimeesAddon = Postimees()
    try:
        if 'url' in PARAMS and 'title' in PARAMS:
            PostimeesAddon.play_stream(PARAMS['url'][0], PARAMS['title'][0])
        else:
            PostimeesAddon.list_channels()

    except PostimeesException, ex:
        PostimeesAddon.display_error(str(ex))
    except Exception:
        buggalo.onExceptionRaised()
