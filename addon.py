# -*- coding: utf-8 -*-

import re
import os
import sys

try:
    from urllib.parse import parse_qs, quote_plus
    from urllib.request import Request as urllib_Request
    from urllib.request import HTTPHandler, HTTPSHandler, urlopen, install_opener, build_opener
except ImportError:
    from urllib2 import Request as urllib_Request
    from urllib2 import urlopen, install_opener, build_opener, HTTPError, HTTPSHandler, HTTPHandler
    from urlparse import parse_qs
    from urllib import quote_plus

import json

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

UA = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'


class PostimeesException(Exception):
    pass


class Postimees(object):
    def download_url(self, url, header=None):
        for retries in range(0, 5):
            try:
                r = urllib_Request(url)
                r.add_header('User-Agent', UA)
                if header:
                    for h_key, h_value in header.items():
                        r.add_header(h_key, h_value)
                http_handler = HTTPHandler(debuglevel=0)
                https_handler = HTTPSHandler(debuglevel=0)
                opener = build_opener(http_handler, https_handler)
                install_opener(opener)
                u = urlopen(r)
                contents = u.read()
                u.close()
                return contents
            except:
                raise RuntimeError('Could not open URL: {}'.format(url))

    def get_session(self, origin):
        url = 'https://sts.postimees.ee/session/register/'
        extra_header = {'Accept': 'application/json, text/plain, */*', 'X-Original-URI': origin}
        try:
            data = json.loads(self.download_url(url, extra_header))
            return data['session']
        except:
            pass

    def get_origin(self, channel):
        return "https://kanal-live.babahhcdn.com/bb1039/smil:kanal%s.smil/playlist.m3u8?t=pmonline" % channel

    def get_live_items(self, channel):
        session = self.get_session(self.get_origin(channel))
        if session is not None:
            item = xbmcgui.ListItem('Kanal%s %s' % (channel, ADDON.getLocalizedString(32006)))
            item.setArt({'icon': self.get_icon(channel), 'fanart': FANART})
            item.setInfo('video', infoLabels={"Title": "Kanal%s %s" % (channel, ADDON.getLocalizedString(32006))})
            item.setProperty('IsPlayable', 'true')
            url = "%s&s=%s|User-Agent=%s" % (self.get_origin(channel), session, quote_plus(UA))
            return url, item

    def get_icon(self, channel):
        return os.path.join(ADDON.getAddonInfo('path'), 'resources/icons/kanal%s.png' % channel)

    def list_sections(self):
        url = 'https://tv.postimees.ee'
        items = list()
        # live
        channels = [2, 11, 12]
        for channel in channels:
            if self.get_live_items(channel) is not None:
                items.append(self.get_live_items(channel))

        data = self.download_url(url)

        if not data:
            raise PostimeesException(ADDON.getLocalizedString(32004))
        # replace bs4 with regex
        menu_regex = r'<a( class="child" | )href="%s/section/(\d+)" target="_self"(| class="menu-link")>(.*?)</a>' % url
        menu_items = re.findall(menu_regex, data)
        for menu_item in menu_items:
            if "menu-link" in menu_item[2]:
                title = '[COLOR blue] %s[/COLOR]' % menu_item[3]
            else:
                title = menu_item[3]
            item = xbmcgui.ListItem(title)
            item.setProperty('IsPlayable', 'true')
            item.setArt({'fanart': FANART, 'poster': FANART})
            items.append((PATH + "?section=%s&title=%s&start=0&limit=10" % (menu_item[1], title), item, True))
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
                except KeyError:
                    encrypted = False
                if encrypted:
                    video = "%s&s=%s|User-Agent=%s" % (
                        show['media'][0]['sources']['hls'], self.get_session(show['media'][0]['sources']['hls']),
                        quote_plus(UA))
                else:
                    video = show['media'][0]['sources']['hls']

                fanart = show['thumbnail']['sources']['landscape']['small']
                try:
                    plot = re.sub('<[^<]+?>', '', show['articleLead'][0]['html'])
                except IndexError:
                    plot = show['headline']
                infoLabels = {'title': show['headline'],
                              'plot': plot
                              }
                title = show['headline']
                if show['additionalHeadline']:
                    title = "%s %s" % (show['additionalHeadline'], title)
                item = xbmcgui.ListItem(title)
                item.setArt({'fanart': fanart, 'poster': fanart, 'icon': fanart})
                item.setInfo('video', infoLabels)
                item.setProperty('IsPlayable', 'True')
                items.append((video, item))
            except:
                pass
        item = xbmcgui.ListItem('[COLOR yellow]%s[/COLOR]' % ADDON.getLocalizedString(32005))
        item.setArt({'fanart': FANART, 'poster': FANART})
        items.append((PATH + '?section=%s&title=%s&start=%s&limit=%s' % (
            section, title, int(start) + int(limit) + 1, limit), item, True))
        xbmcplugin.addDirectoryItems(HANDLE, items)
        xbmcplugin.endOfDirectory(HANDLE)

    def display_error(self, message='n/a'):
        heading = 'error'
        line1 = ADDON.getLocalizedString(32001)
        line2 = ADDON.getLocalizedString(32002)
        xbmcgui.Dialog().ok(heading, line1, line2, message)


if __name__ == '__main__':
    ADDON = xbmcaddon.Addon()
    PATH = sys.argv[0]
    HANDLE = int(sys.argv[1])
    PARAMS = parse_qs(sys.argv[2][1:])
    FANART = os.path.join(ADDON.getAddonInfo('path'), 'resources/fanart.png')
    CACHE_PATH = xbmc.translatePath(ADDON.getAddonInfo("Profile"))
    if not os.path.exists(CACHE_PATH):
        os.makedirs(CACHE_PATH)

    PostimeesAddon = Postimees()
    try:
        if 'section' in PARAMS and 'title' in PARAMS:
            PostimeesAddon.get_section(PARAMS['section'][0], PARAMS['title'][0], PARAMS['start'][0], PARAMS['limit'][0])
        else:
            PostimeesAddon.list_sections()
    except PostimeesException as ex:
        PostimeesAddon.display_error(str(ex))
    except:
        pass
