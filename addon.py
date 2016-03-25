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
import urllib
import urllib2
import urlparse
from BeautifulSoup import BeautifulSoup

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

import buggalo



class PostimeesException(Exception):
  pass

class Postimees(object):
  def downloadUrl(self,url):
    for retries in range(0, 5):
      try:
        r = urllib2.Request(url.encode('iso-8859-1', 'replace'))
        r.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1')
        httpHandler = urllib2.HTTPHandler(debuglevel=0) #debug
        httpsHandler = urllib2.HTTPSHandler(debuglevel=1)
        opener = urllib2.build_opener(httpHandler, httpsHandler)

        urllib2.install_opener(opener)
        u = urllib2.urlopen(r)
        #u = urllib2.urlopen(r, timeout = 30)
        contents = u.read()
        u.close()
        return contents
      except Exception, ex:
        if retries > 5:
          raise PostimeesException(ex)

  def listChannels(self):
    url = 'http://www.postimees.ee/'
    items = list()
    html = BeautifulSoup(self.downloadUrl(url))
    print url
    if not html:
      raise PostimeesException(ADDON.getLocalizedString(200).encode('utf-8'))
    kava = html.body.findAll('tbody')
    regex = 'window.location.href = \'([^\']+)\'.*eventDay">([^<]+)<.*eventDesc">([^<]+)<'
    for node in kava:
      for m in re.findall(regex,str(node)):
        if "lekan" in m[2] or "tse" in m[2]:
          title = "%s - %s" % (m[1],m[2])
          item = xbmcgui.ListItem(title, iconImage=FANART)
          item.setProperty('IsPlayable', 'true')
          item.setProperty('Fanart_Image', FANART)
          items.append((PATH + '?url=%s&title=%s' % (m[0],title), item, False)) #isFolder=False
    xbmcplugin.addDirectoryItems(HANDLE, items)
    xbmcplugin.endOfDirectory(HANDLE)

  def getVideoId(self,url):
    html = self.downloadUrl(url)
    regex = 'articleVideo([0-9^"]+)"'
    for videoid in re.findall(regex,html):
      return videoid

  def playStream(self,url,title):
    saade = "http://www.postimees.ee/video/hls/%s.m3u8" % self.getVideoId(url)
    buggalo.addExtraData('saade',saade)
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()

    item = xbmcgui.ListItem(title, iconImage = ICON, path = saade)
    playlist.add(saade,item)
    firstItem = item
    xbmcplugin.setResolvedUrl(HANDLE, True, item)

  def displayError(self, message = 'n/a'):
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
    if PARAMS.has_key('url') and PARAMS.has_key('title'):
      PostimeesAddon.playStream(PARAMS['url'][0],PARAMS['title'][0])
    else:
      PostimeesAddon.listChannels()

  except PostimeesException, ex:
    PostimeesAddon.displayError(str(ex))
  except Exception:
    buggalo.onExceptionRaised()
