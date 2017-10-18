#!/usr/bin/python
# -*- coding: utf-8 -
from tornado.ioloop import IOLoop, PeriodicCallback
import tornado.web
import re, hashlib, json
import logging, logging.config


class Channel:
   def __init__(self, id, name, url, hd=False, tags=[], logo=None, prio=0):
       self.id   = id
       self.name = name
       self.url  = url
       self.tags = tags
       self.hd   = hd
       self.logo = logo
       self.prio = prio

   def __str__(self):
       return json.dumps( {'id': self.id, 'name': self.name, 'url': self.url, 'tags': self.tags, 'hd': self.hd, 'prio': self.prio, 'logo': self.logo}, indent=2 )


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
       self.logger = logging.getLogger('playlistmanager')
       self.playlists = [ x(self) for x in playlists ]
       self.channels = []
       self.load_cache()

       #self.update()
       if update_time>0:
          self.period = PeriodicCallback( callback=self.update, callback_time=update_time, io_loop=ioloop )
          self.period.start()
       pass

   def load_cache(self):
       try:
          f = open("playlist.json","rt")
          data = json.load(f)
          self.channels = [Channel(**item) for item in data]
          f.close()

          self.logger.info("Loaded %d channels from cache" % len(self.channels) )
       except:
          self.logger.exception("Error while loading playlist cache")
       pass

   def store_cache(self):
       try:
          f = open("playlist.json","wt")
          json.dump( self.channels, f, default=lambda x: x.__dict__, indent=2 )
          f.close()
          self.logger.info("Stored %d channels to cache" % len(self.channels) )
       except:
          self.logger.exception("Error while storing playlist cache")
       pass
                     
   def update(self):
       new_channels=[]
       for p in self.playlists:
           try:
             p.load()
           except Exception,e:
             logging.exception('Fail to load playlist %s', p.__class__.__name__ )
           new_channels += p.items
       self.channels = new_channels
       self.store_cache()

   def find_channel( self, string, strict=True ):
       result = []
       try:
         string = string.encode("latin1").decode("utf-8")
         string = unicode(string,'utf-8')
       except:
         pass

       lower_string = string.lower()
       #for playlist in self.playlists:
       if True:
           for item in self.channels:#playlist.items:
               if (strict and item.name.lower()==lower_string) or (not strict and lower_string in item.name.lower()) or item.id==string or item.url==string or lower_string in item.tags:
                  result.append(item)
       return sorted( result, key=lambda channel: channel.prio )


if __name__=="__main__":
   from config import Config
   import argparse
   from vlc import VlcClient
   from handlers import *
   import tornado.httpclient
   from concurrent.futures import ThreadPoolExecutor

   parser = argparse.ArgumentParser()
   parser.add_argument('action', default='serve', choices=['serve','refresh'] )
   parser.add_argument('-v',     dest='debug',  default=False, type=bool )

   args = parser.parse_args()
   if args.debug:
      config.loglevel='DEBUG'

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
   if args.action=='refresh':
      manager.update()
      exit()

   vlc = VlcClient( ioloop = ioloop )
   vlc.connect()

   proxy = tornado.web.Application([
              (r'/(?:%s)?(?:channel|play|c)/(.*?/)?(.*)'  % Config.request_prefix,  ProxyRequestHandler,    { 'manager': manager, 'ioloop': ioloop, 'config': Config, 'vlc': vlc} ),
              (r'/(?:%s)?(?:record|rec)/(.*?)(/.*?)?'     % Config.request_prefix,  RecordRequestHandler,   { 'manager': manager, 'ioloop': ioloop, 'config': Config, 'vlc': vlc} ),
              (r'/(?:%s)?(?:p|playlist|search)/(.*)'      % Config.request_prefix,  PlaylistRequestHandler, { 'manager': manager, 'ioloop': ioloop, 'config': Config } ),
              (r'/(?:%s)?(?:manage)/(.*)'                 % Config.request_prefix,  ManageRequestHandler,   { 'manager': manager, 'ioloop': ioloop, 'config': Config, 'executor': ThreadPoolExecutor(max_workers=4) } ),
              (r'/(?:%s)?(.*)'                            % Config.request_prefix,  tornado.web.StaticFileHandler, {"path": "webapp", 'default_filename': 'index.html' } )
      ], log_function = log_request)
   proxy.listen( Config.listen )
   try:
      ioloop.start()
   except KeyboardInterrupt, e:
      ioloop.stop()
   finally:
      pass
   logging.info("Ace proxy stopped")
