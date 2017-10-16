from aceproxy import Playlist, Channel
import urllib2, json
import logging


class TorrentStreamPlaylist(Playlist):
   def load(self):
       self.logger = logging.getLogger('torstream')
       data = json.load( urllib2.urlopen('https://acestreamcontroller2.appspot.com/secured/content/get-playlist?providerCode=0&version=3') )
       self.clear()

       for ch in data['playlist']:
           channel = Channel( 
               id         = ch['uuid'],
               name       = ch['name'], 
               url        = ch['uri'].replace("acestream://","").replace("uuid://",""),
               tags       = [x.lower() for x in ch['categories']],
               hd         = ch['hd'],
               logo       = ch['logo']['uri'] if 'logo' in ch and 'uri' in ch['logo'] else None
           )
           self.add(channel)
       self.logger.info('Loaded %d channels', len(self.items) )
       pass