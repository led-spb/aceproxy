# -*- coding: utf-8 -
from aceproxy import Playlist, Channel
import logging

class StaticPlaylist(Playlist):
   def load(self):
       self.logger = logging.getLogger('static')

       self.clear()
       name = 'static_1'

       ch = Channel(
            id      = self.uuid( name.encode('utf-8')),
            name    = name, 
            #url     = 'a1d50b2c8a9d66645960020e48bc72e32d63dc8c',
            url     = '2d1e7ff19615e7e841389715ef11f18ed54e235a',
            tags    = ['static'],
            hd      = ' HD' in name,
            logo    = None
       )
       self.add(ch)
       self.logger.info('Loaded %d channels', len(self.items) )
       pass
