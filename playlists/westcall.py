# -*- coding: utf-8 -
from aceproxy import Playlist, Channel
import requests, re
import logging

replacements = [ (u'^Матч$',u'Матч ТВ') ]

class WestcallPlaylist(Playlist):
   def load(self):
       self.logger = logging.getLogger('westcall')
       headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1' }
       req = requests.get( 'https://westcall.spb.ru/homes/files/westcall_tv.m3u', headers=headers, stream=True )
       ch = None
       self.clear()

       for line in req.iter_lines():
           if line.startswith('#EXTINF:'):
              name = line.split(",",2)[1]
              name = name.decode("utf-8")
              for rep in replacements:
                  name = re.sub( rep[0], rep[1], name, re.U+re.I )

              ch = Channel(
                 id      = self.uuid( name.encode('utf-8')  ),
                 name    = name, 
                 url     = None,
                 tags    = ['westcall'],
                 hd      = ' HD' in name,
                 logo    = None
              )
           elif ch !=None:
              url = line.strip()
              #self.logger.debug( "%s: %s", ch.name, url )
              #ch.content_id = url.replace('udp://@','http://127.0.0.1:4022/udp/')
              ch.url = url
              self.add(ch)
              ch = None

       self.logger.info('Loaded %d channels', len(self.items) )
       pass
