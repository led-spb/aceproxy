#!/usr/bin/python
# -*- coding: utf-8 -
from tornado.ioloop import IOLoop, PeriodicCallback
import tornado.web
import tornado.iostream
import socket
import hashlib
import json, time
import logging, logging.config
import urlparse
import shlex, subprocess
from cStringIO import StringIO
import datetime
import os.path
from io import BytesIO
from cStringIO import StringIO
from collections import deque

class Channel:
   def __init__(self, id, name, content_id, hd=False, tags=[], logo=None):
       self.id = id
       self.name = name
       self.content_id = content_id
       self.tags = tags
       self.hd = hd
       self.logo = logo

class Playlist:
   def __init__(self, manager):
       self.manager = manager
       self.clear()

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
           p.load()

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
       return result


class VlcClient():
   def __init__(self, host='127.0.0.1', port=4212, password='admin', ioloop = IOLoop.instance(), on_close=None, on_connected=None):
       self.logger = logging.getLogger('vlc')
       self.host = host
       self.port = port
       self.ioloop = ioloop
       self.password = password
       self.on_close = on_close
       self.on_connected = on_connected
       self.requests = deque([])

   def connect(self):
       self.logger.debug('Connecting to VLC at %s:%d', self.host, self.port)

       self.sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM, 0)
       self.stream = tornado.iostream.IOStream(self.sock)
       self.stream.set_nodelay(1)
       self.stream.set_close_callback( self._closed )
       self.stream.connect( (self.host,self.port), self._start_auth )

   def _start_auth(self):
       self.logger.debug('Connection established')
       self.stream.read_until( "\x01", callback=self._send_auth )
       self._timeout = self.ioloop.add_timeout( self.ioloop.time()+3, self.close )
       pass

   def _closed(self):
       self.logger.debug('Connection closed')
       self.ioloop.remove_timeout( self._timeout )

       if self.on_close!=None:
          self.on_close()
       pass

   def close(self):
       self.stream.close()
       pass

   def _send_auth(self, data):
       self.logger.debug( unicode(data, 'utf-8', errors='ignore') )
       self.stream.write( self.password+"\r\n" )
       self.stream.read_until( "\r\n> ", callback=self._on_connected )

   def _on_connected(self, data):
       self.logger.debug( unicode(data, 'utf-8', errors='ignore').strip("> ").strip("\r\n") )
       self.logger.info('VLC ready')

       self.ioloop.remove_timeout( self._timeout )
       if self.on_connected!=None:
          self.on_connected(self)
       pass
       self.stream.read_until( "\r\n> ", callback=self._read_loop )

   def _read_loop(self, data):
       response = unicode(data, 'utf-8', errors='ignore').strip("> ").strip("\r\n")
       self.logger.debug( response )
       if len(self.requests)>0:
          callback = self.requests.popleft()
          parsed = self.parse_response(response)
          # self.logger.debug( repr(parsed) )
          if callback!=None:
             callback( parsed )
       self.stream.read_until( "\r\n> ", callback=self._read_loop )

   def send_command( self, command, callback=None ):
       self.logger.debug( command )
       self.requests.append( callback )
       self.stream.write( command.encode('utf-8')+"\r\n" )

   def parse_response(self, response):
       data = {}
       self._parse_response( data, 0, 0, [ x for x in response.split("\r\n") if x!='' ] )
       return data

   def _parse_response(self, obj, offset, p, lines):
       idx = p
       while idx<len(lines):
          line = lines[idx]
          pos = len(line)-len(line.lstrip())
          if pos<offset:
             return idx
          if pos>offset:
             new_obj = {}
             idx = self._parse_response( new_obj, pos, idx, lines )
             obj[curr_key] = new_obj

          if pos==offset:
             split = line.lstrip().split(" : ")
             curr_key = split[0]
             obj[curr_key] = split[1] if len(split)>1 else None
             idx = idx + 1
       return idx

class AsyncStreamHttp:
   def __init__( self, url, on_data=None, on_close=None, on_headers=None ):
       logging.info('Open HTTP connection to %s', url)
       self.url = url
       self.url_data = urlparse.urlparse(url)

       self.on_data    = on_data
       self.on_close   = on_close
       self.on_headers = on_headers
       self.headers  = []

       self.stream = tornado.iostream.IOStream( socket.socket( socket.AF_INET, socket.SOCK_STREAM, 0) )
       self.stream.set_close_callback( self._closed )
       self.stream.set_nodelay(1)
       self.stream.connect( (self.url_data.hostname, 80 if self.url_data.port is None else self.url_data.port), self._connected )

   def _connected(self):
       buffer = "%s %s HTTP/1.1\r\nHost: %s\r\n\r\n" % ( "GET", "/" if self.url_data.path==None else self.url_data.path , self.url_data.hostname )
       # write request and read response headers
       self.stream.read_until("\r\n\r\n", self._on_headers)
       self.stream.write( buffer )
                                     
   def _on_headers(self, data):
       data = data.split("\r\n")
       self.status  = data[0]
       self.headers = data[1:]

       if self.on_headers!=None:
          self.on_headers( self.status, self.headers )
       # start reading stream
       self._read_data()

   def _on_data(self,data):
       if self.on_data!=None:
          self.on_data(data)
       self._read_data()
       pass

   def _read_data(self):
       self.stream.read_until_close( streaming_callback=self.on_data )

   def _closed(self):
       if self.on_close!=None:
          self.on_close()
       pass

   def _dummy(self,data):
       pass

   def close(self):
       try:
          self.stream.close()
       except:
          pass
       pass


class AceClient:
   STATE_NOT_READY = 0
   STATE_IDLE = 1
   STATE_STARTING = 2
   STATE_RUNNING = 3

   product_key = 'GhX6cC5YbXMqPgC-s1pxmtvxcnnHuHkaXjklzMpAq-n8586VL6vfl-lrBoI'
   #product_key = 'n51LvQoTlJzNGaFxseRK-uvnvX-sD4Vm5Axwmc4UcoD-jruxmKsuJaH0eVgE'
   cache = {}

   def __init__(self, address, product_key = None, on_ready=None, on_close=None, cache_timeout=60, logger=None ):
       self._log = StringIO()
       if product_key!=None:
          self.product_key = product_key

       self.logger = logger if logger!=None else logging.getLogger('ace')
       self.logger.debug("Trying connect to ACE at %s", repr(address) )

       self.state = AceClient.STATE_NOT_READY
       self.livepos = {}
       self.sock   = socket.socket( socket.AF_INET, socket.SOCK_STREAM, 0)
       self.stream = tornado.iostream.IOStream(self.sock)
       self.stream.set_nodelay(1)
       self.stream.set_close_callback( self._closed )
       self.stream.connect( address, self._connected )
       self.video_url = None
       self.cache_timeout = cache_timeout
       self.cache_timeout_id = None

       self.on_ready = on_ready
       self.on_close = on_close
       self.on_video = None
       self.on_stop  = None
       pass

   def _dummy(self,data):
       pass

   def get_log(self):
       return self._log.getvalue()

   @classmethod
   def get_cached(cls, content_id):
       if not AceClient.cache.has_key(content_id):
          return None

       stored = AceClient.cache[content_id]
       del AceClient.cache[content_id]

       if stored!=None and stored.cache_timeout_id!=None:
          IOLoop.instance().remove_timeout( stored.cache_timeout_id )
       return stored

   def store_cache(self, retain=False):
       if retain:
         self.logger.info("Store %s ace client to cache", self.content_id )
       else:
         self.logger.info("Store %s ace client to cache for %d seconds", self.content_id, self.cache_timeout)

       AceClient.cache[self.content_id] = self
       # remove and stop ace after timeout
       if not retain:
          self.cache_timeout_id = IOLoop.instance().add_timeout( IOLoop.instance().time()+self.cache_timeout, self._on_cache_timeout )
       pass

   def _on_cache_timeout(self):
       ace = self.get_cached(self.content_id)
       if ace==None:
          return
       self.logger.info("Remove %s ace client from cache", self.content_id)
       self.close()
       pass

   def write(self, command):
       self._log.write(command)
       self._log.write("\r\n")

       self.logger.debug( ">>%s", command)
       self.stream.write( command ) 
       self.stream.write( "\r\n" )

   def _connected(self):
       # start reading
       self.stream.read_until( "\r\n", callback=self._on_read )
       self.logger.info("ACE connected")
       self.write("HELLOBG version=%d" % 3)

   def _closed(self):
       self.logger.info("Connection to ACE closed")
       if self.on_close!=None:
          self.on_close()

   def _on_read(self, data):
       self._log.write(data)

       data = data.strip()
       x = data.split(None,1)
       message = (x[0:]+[None])[0]
       params  = (x[1:]+[None])[0]

       if message=='STATUS' or message=='EVENT':
          lvl = 1
       else:
          lvl = logging.DEBUG

       if not(data=='PAUSE' or data=='RESUME' or (data.startswith('STATE') and self.state == AceClient.STATE_RUNNING )):
          self.logger.log(lvl, "<<%s", data)

       mmethod = '_'+message
       if hasattr(self, mmethod):
          getattr(self, mmethod)(params)
       # read next response from engine
       self.stream.read_until( "\r\n", callback=self._on_read )

   def _HELLOTS(self, params):
       k = {}
       for p in params.split():
           t = p.split('=')
           k[t[0]]=t[1]
       response_key = hashlib.sha1( k['key'] + self.product_key ).hexdigest()
       self.write( "READY key=%s" % (self.product_key.split('-')[0] + '-' + response_key) )

   def _STATE(self, params):
       st = int(params)
       if st==0:
          self.state = AceClient.STATE_IDLE
          if self.on_stop!=None:
             self.on_stop()
       elif st==1:
          self.state = AceClient.STATE_STARTING
       elif st==2:
          self.state = AceClient.STATE_RUNNING

   def _STATUS(self, params):
       t = params.split(";")
       if t[0]=="main:err":
          self.logger.error("engine error: %s", t[2] )

   def _START(self, params):
       self.state = AceClient.STATE_RUNNING
       self.video_url = params.split()[0]
       if self.on_video!=None:
          self.on_video( self, self.video_url )

   def _AUTH(self, params):
       self.state = AceClient.STATE_IDLE
       #self.write( bytes('USERDATA [{"gender": 1}, {"age": 3}]') )
       if self.on_ready!=None:
          self.on_ready( self )

   def _EVENT(self, params):
       data = params.split(' ')
       if data[0]=='livepos':
          self.livepos = {x.split('=')[0]:x.split('=')[1] for x in data[1:] }
       pass

   def start(self, datatype, **params):
       command = ""
       if datatype=="PID":
          #test
          #self.write( bytes("LOADASYNC 1 PID %s" % params.get('content_id')) )
          command = "START PID %s %s output_format=http" % ( params.get("content_id"), params.get("file_indexes","0") )

       self.content_id = params.get("content_id")
       self.video_url = None

       self.on_video = params.get("on_video",None)
       self.on_stop  = params.get("on_stop",None)

       self.write( bytes(command) )

   def stop(self):
       self.write( "STOP" )

   def shutdown(self):
       pass

   def close(self):
       try:
          self.stop()
          self.shutdown()
          self.stream.close()
       except:
          pass


class BaseRequestHandler(tornado.web.RequestHandler):
   request_id = 0

   def initialize(self, manager ):
       self.manager = manager

   def gen_request_id(self):
       if self.request_id == BaseRequestHandler.request_id:
          self.request_id = BaseRequestHandler.request_id
          BaseRequestHandler.request_id = self.request_id + 1
       return self.request_id

   def find_channel(self, string):
       self.logger.info("Searching channel %s", string )
       result = self.manager.find_channel(string)
       if len(result)>0:
          res = result[0]
          self.logger.info("Finded channel %s, uid=%s, content_id=%s", res.name, res.id, res.content_id )
          return res
       else:
          return None
   
   @tornado.web.asynchronous
   def get(self, *args, **kwargs):
       self.gen_request_id()
       self.logger = logging.getLogger('req').getChild( "%05d" % self.request_id )

       self.logger.info("%s %s %s", self.request.method, unicode(self.request.uri,'utf-8'), self.request.version )
       for (k,v) in self.request.headers.get_all():
           self.logger.debug( "%s: %s", k,v ) 
       self.logger.debug("")

   def _handle_request_exception(self, e):
       self.logger.exception("Error while handle request")
       tornado.web.RequestHandler._handle_request_exception(self, e)



class ProxyRequestHandler(BaseRequestHandler):

   def initialize(self, manager, config ):
       BaseRequestHandler.initialize(self, manager)
       self.config = config
       pass

   def _set_timeout(self, timeout ):
       self.ace_timeout_id =  IOLoop.instance().add_timeout( IOLoop.instance().time()+timeout, self.on_ace_timeout, True )

   def _remove_timeout(self):
       if self.ace_timeout_id!=None:
          IOLoop.instance().remove_timeout( self.ace_timeout_id )
          self.ace_timeout_id = None

   @tornado.web.asynchronous
   def get(self, mode, content_id):
       BaseRequestHandler.get(self)
       self.ace = None
       self.ace_timeout_id = None
       self.http = None
       self.size = 0

       self.channel = self.find_channel( content_id )

       if self.channel==None:
          self.set_status(404)
          self.finish()
          return

       self.content_id = self.channel.content_id

       self.ace = AceClient.get_cached( self.content_id )
       if self.ace==None:
          ace_address = ( self.config.ace.split(":")[0], int(self.config.ace.split(":")[1]) if len(self.config.ace.split(":"))>1 else 62062 )
          self.ace = AceClient( 
                ace_address, 
                on_ready = self.on_ace_ready,
                on_close = self.on_ace_timeout,
                cache_timeout = self.config.timeouts['ace_cache'],
                logger = self.logger
          )
          self._set_timeout( self.config.timeouts['ace_init'] )
       else:
          self.ace.on_ready = self.on_ace_ready
          self.ace.on_close = self.on_ace_timeout
          self.ace.on_video = self.on_video_ready
          self.ace.on_stop  = self.on_ace_timeout

          if self.ace.state == AceClient.STATE_RUNNING:
             self.on_video_ready( self.ace, self.ace.video_url )
          else:
             self._set_timeout( self.config.timeouts['ace_ready'] )

   def on_ace_ready(self, ace):
       self._remove_timeout()

       ace.start( 'PID', 
            content_id = self.content_id, 
            on_video   = self.on_video_ready,
            on_stop    = self.on_ace_timeout
       )
       self._set_timeout( self.config.timeouts['ace_ready'] )
       pass

   def on_video_ready(self, ace, url):
       self._remove_timeout()
       self.logger.info( "Video ready: %s", url )
       # Start read data
       self.http = AsyncStreamHttp( url, on_data=self.on_video_data, on_headers=self.on_video_headers )

   def on_ace_timeout( self, error=False ):
       self._remove_timeout()
       if error:
          self.set_status(500)
          self.set_header('Content-Type', 'text/plain' )
          self.write( self.ace.get_log() )
       self.finish()

   def on_finish(self):
       self._remove_timeout()
       if self.get_status() in (200,302):
          self.application.log_request(self)

       if self.http!=None:
          self.logger.debug("Closing video http request")
          self.http.close()
          self.http = None

       # Store current client in cache 
       if self.ace==None:
          return

       self.ace.on_close = None
       if self.config.ace_cache and ( self.ace.state==AceClient.STATE_RUNNING or self.ace.state==AceClient.STATE_STARTING ):
          self.ace.store_cache()
       else:
          self.ace.close()
       self.ace = None
       pass

   def on_connection_close(self):
       self.on_finish()

   def on_video_headers(self, status, headers):
       self.logger.debug(status)

       parsed = status.split(" ",3)
       code   = int(parsed[1])
       reason = parsed[2]

       self.set_status(code, reason)
       # Copy headers
       for h in headers:
           d = h.split(': ',2)
           if (len(d)==2) and (d[0] not in self.config.disabled_headers ):
              self.logger.debug( h )
              self.set_header( d[0], d[1] )
       self.set_header('Content-Type', 'video/mp2ts' )
       self.flush()

   def on_video_data(self, data):
       try:
         self.size = self.size + len(data)
         self.write(data)
         self.flush()
       except:
         pass

"""
class TimeStoringClient:
   cache = {}

   def __init__(self, channel, filename, url, ace, duration, logger):
       self.channel = channel
       self.ace = ace
       self.ace.on_close = None
       self.url = url
       self.duration = duration
       self.time_end = 0
       self.logger = logger if logger!=None else logging.getLogger('rec')

       self.position = 0
       self.start_position = 0

       self.filename = filename
       self.http = AsyncStreamHttp( url, on_data=self.on_video_data, on_headers=self.on_video_headers, on_close=self.on_close )
       self.out = open(filename,"wb")

       self.buffer = str()
       self.chunk_len = 0
       self.total = 0
       self.store_cache()
       pass

   def store_cache(self):
       TimeStoringClient.cache[self.channel.content_id] = self 

   @classmethod
   def get_cache(cls, key):
       if key in TimeStoringClient.cache:
          return TimeStoringClient.cache[key]
       return None

   def stop(self):
       if self.http!=None:
          self.http.close()

   def status(self):
       return  { 'status': 'started' if self.http!=None else 'finished', 
                 'channel': self.channel.name, 
                 'content_id': self.channel.content_id, 
                 'filename': self.filename, 
                 'bytes': self.total,
                 'duration': self.position - self.start_position,
                 'position_ts': self.position,
                 'position_string': datetime.datetime.fromtimestamp(self.position).strftime('%c')
               }

   def on_video_headers(self, status, headers):
       logging.debug(status)

       if self.duration>0:
          self.time_end = int(time.time()) + self.duration
       self.logger.info("Begin storing to %s, duration %d sec", self.filename, self.duration)
       pass

   def on_close(self):
       self.logger.info("Stored %d bytes to %s", self.total, self.filename)
       self.ace.close()
       self.http = None
       pass

   def on_video_data(self, data):
       self.buffer = self.buffer + data
       while len(self.buffer) >= self.chunk_len and len(self.buffer)>0:
          if self.chunk_len==0:
             try:
                offset = self.buffer.index('\r\n')
                if offset>0:
                   self.chunk_len = int( data[:offset], 16 )
                else: 
                   self.chunk_len = 0
                self.buffer = self.buffer[offset+2:]
             except ValueError,e:
                return
          else:
             size = self.chunk_len if len(self.buffer)>=self.chunk_len else len(self.buffer)
             self.total = self.total + size
             chunk = self.buffer[:size]
             self.out.write(chunk)
             self.out.flush()

             self.buffer = self.buffer[size:]
             self.chunk_len = self.chunk_len - size
       pass

       if 'pos' in self.ace.livepos:
          self.position = int( self.ace.livepos['pos'] )
          if self.start_position == 0:
             self.start_position = self.position
       if self.time_end>0 and self.position>self.time_end:
          self.http.close()


class RecordRequestHandler(ProxyRequestHandler):
   @tornado.web.asynchronous
   def get(self, action, content):
       BaseRequestHandler.get(self)

       self.duration = int( self.get_argument('duration',0) )

       self.client = None
       self.channel = self.find_channel( content )

       if self.channel!=None:
          self.client = TimeStoringClient.get_cache( self.channel.content_id )

       if action not in ('start','stop','status') or self.channel==None or (action!='start' and self.client==None ):
          self.set_status(404)
          self.finish()
          return

       if action=='start':
          ProxyRequestHandler.get(self, None, self.channel.id)
          return

       if action=='status':
          self.set_status(200)
          self.write( json.dumps( self.client.status() ) )

       if action=='stop':
          self.client.stop()
          self.set_status(200)
          self.write( json.dumps( self.client.status() ) )

       self.finish()
       pass

   def on_finish(self):
       pass

   def on_video_ready(self, ace, url):
       self._remove_timeout()
       self.logger.info( "Video ready: %s", url )

       self.filename = os.path.join( self.config.store_dir, datetime.datetime.now().strftime("%Y%m%d_%H%M")+"_"+self.channel.name+".ts")

       store_client = TimeStoringClient( self.channel, self.filename, url, self.ace, self.duration, self.logger )
       self.set_status(200)
       self.write( json.dumps( store_client.status() ) )
       self.finish()

   def on_ace_timeout(self, error=False):
       self._remove_timeout()
       if self.ace!=None:
          self.ace.on_close=None
          self.ace.close()

       self.set_status(500)
       status = { 'status': 'failed', 'channel': self.channel.name, 'id': self.request_id }
       self.write( json.dumps(status) )
       self.finish()
       pass
"""

class VlcRecordRequestHandler(ProxyRequestHandler):
   def initialize(self, manager, config, vlc):
       ProxyRequestHandler.initialize(self, manager, config)
       self.vlc = vlc

   def _vlc_response(self, data):
       self.write( data )
       self.finish()

   @tornado.web.asynchronous
   def get(self, action, content):
       BaseRequestHandler.get(self)

       self.channel = self.find_channel( content )
       if action not in ('start','stop','status'):
          self.set_status(400)
          self.finish()
          return

       if self.channel==None and action!="status":
          self.set_status(404)
          self.finish()
          return

       if action=='start':
          ProxyRequestHandler.get(self, None, self.channel.id)
          return

       if action=='stop':
          ace = AceClient.get_cached( self.channel.content_id )
          if ace!=None:
             ace.close()
          self.vlc.send_command("control %s pause\r\ndel %s\r\nshow" % (self.channel.id, self.channel.id), callback=self._vlc_response )
          return 

       if action=='status':
          if self.channel==None:
             self.vlc.send_command("show", callback=self._vlc_response )
          else:
             self.vlc.send_command("show %s" % (self.channel.id), callback=self._vlc_response )
          return 
       pass

   def on_finish(self):
       pass

   def _on_vlc_data(self, data):
       self.logger.debug( data )
       self.set_status(200)
       self.set_header('Content-Type', 'application/json' )
       self.write( json.dumps(data) )
       self.finish()

   def on_video_ready(self, ace, url):
       self._remove_timeout()

       self.logger.info( "Video ready: %s", url )
       self.filename = os.path.join( self.config.store_dir, datetime.datetime.now().strftime("%Y%m%d_%H%M")+"_"+self.channel.name+".mp4" )
       self.vlc.send_command( 
             'new "%s" broadcast input "%s" output #std{access=file,mux=mp4,dst="%s"} enabled\r\ncontrol %s play\r\nshow' % (self.channel.id, url, self.filename, self.channel.id),
             callback=self._vlc_response
        )
       ace.on_close = None
       ace.store_cache(True)

   def on_ace_timeout(self, error=False):
       self._remove_timeout()
       if self.ace!=None:
          self.ace.on_close=None
          self.ace.close()

       if error:
          self.set_status(500)
          self.write( self.ace.get_log() )
       self.finish()
       pass



class PlaylistRequestHandler(BaseRequestHandler):

   def get(self, name):
       BaseRequestHandler.get(self)

       self.logger.info("Searching %s", name )
       result = self.manager.find_channel( name, False )

       self.set_status(200)
       if self.get_argument('json',None)!=None:
          self.set_header('Content-Type', 'application/octet-stream' )
          self.write( json.dumps([ {'id': x.id, 'name': x.name, 'tags': x.tags, 'hd': x.hd, 'content_id': x.content_id, 'logo': x.logo}  for x in result  ] ) )
       else:
         self.set_header('Content-Type', 'audio/x-mpegurl' )
         self.set_header('Content-Disposition', 'attachment; filename="'+name+'.m3u"')
         self.write("#EXTM3U url-tvg=\"http://www.teleguide.info/download/new3/jtv.zip\"\r\n" )

         url = "%s://%s" % (self.request.protocol,self.request.host)
         for item in result:
             self.write("#EXTINF:-1 group-title=\"%s\" tvg-name=\"%s\", %s\r\n" % (",".join( item.tags ), item.name, item.name ) )
             self.write("%s/channel/uuid/%s\r\n" % (url,item.id) )
       self.finish()
   pass


if __name__=="__main__":
   from config import Config
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

   #vlc_process = subprocess.Popen(
   #        shlex.split("vlc -I telnet --clock-jitter -1 --network-caching -1 --sout-mux-caching 2000 --telnet-password admin --telnet-port 4212"),
   #        stdout = subprocess.PIPE, stderr=subprocess.STDOUT
   #)
   #time.sleep(3)
   vlc = VlcClient()
   vlc.connect()

   proxy = tornado.web.Application([
              (r'/(?:%s)?(?:channel|play|c)/(.*?/)?(.*)'  % Config.request_prefix,  ProxyRequestHandler,    { 'manager': manager, 'config': Config} ),
              (r'/(?:%s)?(?:record|rec)/(.*)/(.*)'        % Config.request_prefix,  VlcRecordRequestHandler,{ 'manager': manager, 'config': Config, 'vlc': vlc} ),
              (r'/(?:%s)?(?:p|playlist|search)/(.*)'      % Config.request_prefix,  PlaylistRequestHandler, { 'manager': manager } ),
              (r'/(?:%s)?(.*)'                            % Config.request_prefix,  tornado.web.StaticFileHandler, {"path": "webapp", 'default_filename': 'index.html' } )
      ], log_function = log_request
   )
   proxy.listen( Config.listen )
   try:
      ioloop.start()
   except KeyboardInterrupt, e:
      IOLoop.instance().stop()
   finally:
      #vlc_process.terminate()
      pass
   logging.info("Ace proxy stopped")
