#!/usr/bin/python
# -*- coding: utf-8 -
from tornado.ioloop import IOLoop, PeriodicCallback
import tornado.web
import re, hashlib, json
import logging, logging.config


class Channel:
   def __init__(self, id, name, content_id, hd=False, tags=[], logo=None):
       self.id   = id
       self.name = name
       self.content_id = content_id
       self.tags = tags
       self.hd   = hd
       self.logo = logo
       self.prio = 0

   def __str__(self):
       return json.dumps( self.__dict__, indent=2 )

class Playlist:
   def __init__(self, manager):
       self.manager = manager
       self.clear()

   def uuid(self, name):
       name = re.sub('\s+|\(.*?\)|\[.*?\]', '', name).lower()
       return hashlib.md5(name).hexdigest()

   def add(self, item):
       self.items.append(item)

   def clear(self):
       self.items=[]

   def load(self):
       pass


class PlaylistManager:
   def __init__(self, playlists, ioloop, update_time):
       self.playlists = [ x(self) for x in playlists ]
       self.update()
       self.period = PeriodicCallback( callback=self.update, callback_time=update_time, io_loop=ioloop )
       self.period.start()
       pass

   def update(self):
       for p in self.playlists:
           try:
             p.load()
           except Exception,e:
             logging.exception('Fail to load playlist %s', p.__class__.__name__ )

   def find_channel( self, string, strict=True ):
       result = []
       try:
         string = string.encode("latin1").decode("utf-8")
         string = unicode(string,'utf-8')
       except:
         pass

       lower_string = string.lower()
       for playlist in self.playlists:
           for item in playlist.items:
               if (strict and item.name.lower()==lower_string) or (not strict and lower_string in item.name.lower()) or item.id==string or item.content_id==string or lower_string in item.tags:
                  result.append(item)
       return sorted( result, key=lambda channel: channel.prio )


if __name__=="__main__":
   from config import Config
   from vlc import VlcClient
   from handlers import *
   import tornado.httpclient

   tornado.httpclient.AsyncHTTPClient.configure("tornado.simple_httpclient.SimpleAsyncHTTPClient")

   ioloop = IOLoop.instance()

   def log_request( handler ):
       bytes = -1 if not hasattr(handler,'size') else getattr(handler,'size')
       logger = handler.logger if hasattr(handler,"logger") else logging.getLogger("request")

       logger.info(
           "%d %s %d %.2fs", 
            handler.get_status(),  
            handler._request_summary().decode("utf-8"),
            bytes, 
            handler.request.request_time() 
       )
   logging.config.dictConfig( Config.logging )
   logging.info("Ace proxy started")

   manager = PlaylistManager( Config.playlists, ioloop, Config.timeouts['playlist']*1000 )

   vlc = VlcClient( ioloop = ioloop )
   vlc.connect()

   proxy = tornado.web.Application([
              (r'/(?:%s)?(?:channel|play|c)/(.*?/)?(.*)'  % Config.request_prefix,  ProxyRequestHandler,    { 'manager': manager, 'config': Config, 'vlc': vlc} ),
              (r'/(?:%s)?(?:record|rec)/(.*)/(.*)'        % Config.request_prefix,  RecordRequestHandler,   { 'manager': manager, 'config': Config, 'vlc': vlc} ),
              (r'/(?:%s)?(?:p|playlist|search)/(.*)'      % Config.request_prefix,  PlaylistRequestHandler, { 'manager': manager } ),
              (r'/(?:%s)?(.*)'                            % Config.request_prefix,  tornado.web.StaticFileHandler, {"path": "webapp", 'default_filename': 'index.html' } )
      ], log_function = log_request
   )
   proxy.listen( Config.listen )
   try:
      ioloop.start()
   except KeyboardInterrupt, e:
      ioloop.stop()
   finally:
      pass
   logging.info("Ace proxy stopped")
