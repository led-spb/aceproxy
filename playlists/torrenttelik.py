# -*- coding: utf-8 -
from aceproxy import Playlist, Channel
import requests, json
import logging, re

replacements = [ (u'\s+Резерв\s+\d+',u'') ]

class TorrentTelikPlaylist(Playlist):
   def load(self):
       self.logger = logging.getLogger('torrent-telik')
       headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1' }
       data = requests.get( 'http://torrent-telik.com/channels/torrent-tv.json', headers=headers ).json()
       self.clear()
       for ch in data['channels']:
           for rep in replacements:
               ch['name'] = re.sub( rep[0], rep[1], ch['name'], re.U+re.I )

           channel = Channel( 
               id       = self.uuid( ch['name'].encode('utf-8') ),
               name     = ch['name'], 
               url      = ch['url'].replace("acestream://",""),
               tags     = [ch['cat'].lower()],
               hd       = ' HD' in ch['name'],
               logo     = None
           )
           self.add(channel)
       self.logger.info('Loaded %d channels', len(self.items) )
       pass
