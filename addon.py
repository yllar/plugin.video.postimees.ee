#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#      2017 Yllar Pajus
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
import urllib
import urlparse
import json
from bs4 import BeautifulSoup

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

import buggalo

UA = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'


class PostimeesException(Exception):
    pass


class Postimees(object):
    def download_url(self, url, header=None):
        for retries in range(0, 5):
            try:
                r = urllib2.Request(url.encode('iso-8859-1', 'replace'))
                r.add_header('User-Agent', UA)
                if header:
                    for h_key, h_value in header.items():
                        r.add_header(h_key, h_value)
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

    def get_session(self, origin):
        url = 'https://sts.postimees.ee/session/register/'
        extra_header = {'Accept': 'application/json, text/plain, */*', 'X-Original-URI': origin}
        data = json.loads(self.download_url(url, extra_header))
        # xbmc.log('Session data: %s' % data, xbmc.LOGNOTICE)
        return data['session']

    def list_sections(self):
        url = 'https://pleier.postimees.ee'
        items = list()
        data = BeautifulSoup(self.download_url(url), 'html.parser')
        if not data:
            raise PostimeesException(ADDON.getLocalizedString(203).encode('utf-8'))
        urlid = data.find(class_="main-links")
        menu = urlid.find_all('a')
        for sections in menu:
            if 'class' in sections.attrs:
                title = sections.text
            else:
                title = '[COLOR blue] %s[/COLOR]' % sections.text
            item = xbmcgui.ListItem(title, iconImage=FANART)
            item.setProperty('IsPlayable', 'true')
            item.setProperty('Fanart_Image', FANART)
            items.append((PATH + "?section=%s&title=%s&start=0&limit=10" % (
                sections.get('href').replace('https://pleier.postimees.ee/section/', ''), title), item, True))
        xbmcplugin.addDirectoryItems(HANDLE, items)
        xbmcplugin.endOfDirectory(HANDLE)

    def get_section(self, section, title, start=0, limit=10):
        url = 'https://services.postimees.ee/rest/v1/sections/%s/articles?offset=%s&limit=%s' % \
              (section, start, limit)
        items = list()
        encrypted = False
        data = json.loads(self.download_url(url))
        for show in data:
            try:
                try:
                    encrypted = show['media'][0]['meta']['encrypted']
                except:
                    encrypted = False
                if encrypted:
                    video = "%s&s=%s|User-Agent=%s" % (
                        show['media'][0]['sources']['hls'], self.get_session(show['media'][0]['sources']['hls']),
                        urllib.quote_plus(UA))
                else:
                    video = show['media'][0]['sources']['hls']
                # xbmc.log('Video url: %s' % video, xbmc.LOGNOTICE)

                fanart = self.download_and_cache_fanart(show['thumbnail']['sources']['landscape']['small'],
                                                        show['headline'], True)
                try:
                    plot = re.sub('<[^<]+?>', '', show['articleLead'][0]['html'])
                except:
                    plot = show['headline']
                infoLabels = {'title': show['headline'],
                              'plot': plot
                              }
                item = xbmcgui.ListItem(show['headline'], iconImage=fanart)
                item.setProperty('Fanart_Image', fanart)
                item.setInfo('video', infoLabels)
                item.setProperty('IsPlayable', 'True')
                items.append((video, item))
            except:
                pass
        item = xbmcgui.ListItem('[COLOR yellow]%s[/COLOR]' % ADDON.getLocalizedString(204).encode('utf-8'),
                                iconImage=FANART)
        item.setProperty('Fanart_Image', FANART)
        items.append((PATH + '?section=%s&title=%s&start=%s&limit=%s' % (
            section, title, int(start) + int(limit) + 1, limit), item, True))
        xbmcplugin.addDirectoryItems(HANDLE, items)
        xbmcplugin.endOfDirectory(HANDLE)

    def download_and_cache_fanart(self, url, title, fetch=False):
        fanart_path = os.path.join(CACHE_PATH, '%s.jpg' % title.encode('utf-8'))
        fanart_url = url

        if not os.path.exists(fanart_path) and fetch:
            image_data = self.download_url(fanart_url.replace(' ', '%20').replace('\/', ''))
            if image_data:
                try:
                    f = open(fanart_path, 'wb')
                    f.write(image_data)
                    f.close()
                    return fanart_path
                except IOError:
                    pass
        elif os.path.exists(fanart_path):
            return fanart_path
        return FANART

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
    CACHE_PATH = xbmc.translatePath(ADDON.getAddonInfo("Profile"))
    if not os.path.exists(CACHE_PATH):
        os.makedirs(CACHE_PATH)

    buggalo.SUBMIT_URL = 'https://pilves.eu/exception/submit.php'
    PostimeesAddon = Postimees()
    try:
        if 'section' in PARAMS and 'title' in PARAMS:
            PostimeesAddon.get_section(PARAMS['section'][0], PARAMS['title'][0], PARAMS['start'][0], PARAMS['limit'][0])
        else:
            PostimeesAddon.list_sections()

    except PostimeesException, ex:
        PostimeesAddon.display_error(str(ex))
    except Exception:
        buggalo.onExceptionRaised()
