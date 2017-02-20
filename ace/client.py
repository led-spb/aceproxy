from cStringIO import StringIO
from tornado.ioloop import IOLoop
import tornado.web
import tornado.iostream
import socket
import logging
import hashlib


class AceClient:
   STATE_NOT_READY = 0
   STATE_IDLE = 1
   STATE_STARTING = 2
   STATE_RUNNING = 3

   product_key = 'GhX6cC5YbXMqPgC-s1pxmtvxcnnHuHkaXjklzMpAq-n8586VL6vfl-lrBoI'
   #product_key = 'n51LvQoTlJzNGaFxseRK-uvnvX-sD4Vm5Axwmc4UcoD-jruxmKsuJaH0eVgE'
   cache = {}

   def __init__(self, address, ioloop=None, product_key = None, on_ready=None, on_close=None, cache_timeout=60, logger=None ):
       self._log = StringIO()

       if product_key!=None:
          self.product_key = product_key

       self.ioloop = ioloop or IOLoop.current()
       self.logger = logger or logging.getLogger('ace')

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
          stored.ioloop.remove_timeout( stored.cache_timeout_id )
       return stored

   def store_cache(self, retain=False):
       if retain:
         self.logger.info("Store %s ace client to cache", self.content_id )
       else:
         self.logger.info("Store %s ace client to cache for %d seconds", self.content_id, self.cache_timeout)

       AceClient.cache[self.content_id] = self
       # remove and stop ace after timeout
       if not retain:
          self.cache_timeout_id = self.ioloop.add_timeout( self.ioloop.time()+self.cache_timeout, self._on_cache_timeout )
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

