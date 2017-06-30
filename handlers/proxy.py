import logging
from tornado.ioloop import IOLoop
import tornado.web
import tornado.iostream
#import tornado.httpclient
import socket
import urlparse
from base import BaseRequestHandler
from ace import AceClient


class AsyncStreamHttp:
   def __init__( self, url, on_data=None, on_close=None, on_headers=None, ioloop=None ):
       logging.info('Open HTTP connection to %s', url)
       self.ioloop = ioloop or IOLoop.current()
       self.url = url
       self.url_data = urlparse.urlparse(url)

       self.on_data    = on_data
       self.on_close   = on_close
       self.on_headers = on_headers
       self.headers    = []
       self.sock       = socket.socket( socket.AF_INET, socket.SOCK_STREAM, 0 )

       self.stream = tornado.iostream.IOStream( self.sock, io_loop=self.ioloop )
       self.stream.set_close_callback( self._closed )
       self.stream.set_nodelay(1)
       self.stream.connect( (self.url_data.hostname, 80 if self.url_data.port is None else self.url_data.port), self._connected )

   def _connected(self):
       buffer = "%s %s HTTP/1.1\r\nHost: %s\r\n\r\n" % ( "GET", "/" if self.url_data.path==None else self.url_data.path , self.url_data.hostname )
       # write request and read response headers
       self.stream.read_until('\r\n\r\n', self._on_headers)
       self.stream.write( bytes(buffer) )
                                     
   def _on_headers(self, data):
       data = data.split('\r\n')
       self.status  = data[0]
       self.headers = data[1:]

       if self.on_headers!=None:
          self.on_headers( self.status, self.headers )
       # start reading stream
       self._read_data()

   def _read_data(self):
       self.stream.read_until_close( streaming_callback=self.on_data )

   def _closed(self):
       if self.on_close!=None:
          self.on_close()
       pass

   def close(self):
       try:
          self.stream.close()
       except:
          pass
       pass



class ProxyRequestHandler(BaseRequestHandler):

   def initialize(self, manager, config, vlc ):
       BaseRequestHandler.initialize(self, manager)
       self.config = config
       self.vlc = vlc
       pass

   def _set_timeout(self, timeout ):
       self.ace_timeout_id =  IOLoop.current().add_timeout( IOLoop.current().time()+timeout, self.on_ace_timeout, True )

   def _remove_timeout(self):
       if self.ace_timeout_id!=None:
          IOLoop.current().remove_timeout( self.ace_timeout_id )
          self.ace_timeout_id = None

   @tornado.web.asynchronous
   def get(self, mode, content_id):
       BaseRequestHandler.get(self)
       self.closing = False
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
       if self.content_id.startswith("udp://"):
          url = self.content_id.replace("udp://@","/udp/")
          #ch.content_id = url.replace('udp://@','http://127.0.0.1:4022/udp/')
          #self.on_video_ready( None, self.content_id )
          self.size = 1
          self.redirect( url )
       else:
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
       if self.config.transcode!=None and self.vlc!=None:
          ace_url = url
          cmd = 'new "%s" broadcast input "%s" output '+self.config.transcode+' enabled\r\ncontrol %s play'
          vlc_command = cmd % (self.channel.id, ace_url, self.channel.id, self.channel.id)
          self.logger.info('Starting vlc transcode command: %s', vlc_command )

          self.vlc.send_command( vlc_command, callback=self._on_vlc_response )
       else:
          self.http = AsyncStreamHttp( url, on_data=self.on_video_data, on_headers=self.on_video_headers, on_close=self.on_video_close )

   def _on_vlc_response( self, response ):
       IOLoop.current().add_timeout( IOLoop.current().time()+0.5, self._start_vlc_request )

   def _start_vlc_request(self):
       url = "http://127.0.0.1:8717/%s" % self.channel.id
       self.logger.debug( 'Starting http client, url: %s', url )
       self.http = AsyncStreamHttp( url, on_data=self.on_video_data, on_headers=self.on_video_headers, on_close=self.on_video_close )

   def on_video_close(self):
       self.logger.debug('Connection to video stream closed') 
       self.http = None
       if self.closing!=True:
          self.finish()

   def on_ace_timeout( self, error=False ):
       self._remove_timeout()
       if error:
          self.set_status(500)
          self.set_header('Content-Type', 'text/plain' )
          self.write( self.ace.get_log() )
       self.finish()

   def on_finish(self):
       self.closing = True
       self.logger.info("Connection closed")
       self._remove_timeout()

       # change broken channel priority
       if self.size==0 and self.channel!=None:
          self.channel.prio = self.channel.prio + 1

       if self.get_status() in (200,302):
          self.application.log_request(self)

       if self.config.transcode!=None and self.vlc!=None:
          self.logger.info("Stopping VLC broadcast")
          self.vlc.send_command("control %s pause\r\ndel %s" % (self.channel.id, self.channel.id) )

       if self.http!=None:
          self.logger.debug("Closing video stream request")
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
       self.logger.debug("Got video stream: %s", status)

       parsed = status.split(" ",3)
       code   = int(parsed[1])
       reason = parsed[2]

       self.set_status(code, reason)
       # Copy headers
       for h in headers:
           d = h.split(': ',2)
           if (len(d)==2) and ( (d[0] not in self.config.disabled_headers ) ):
              self.logger.debug( h )
              self.set_header( d[0], d[1] )
       if self.config.transcode==None:
          self.set_header('Content-Type', 'video/mp2ts' )
       self.flush()

   def on_video_data(self, data):
       try:
         self.size = self.size + len(data)
         self.write(data)
         self.flush()
       except:
         pass
