from tornado.ioloop import IOLoop
import tornado.web
import tornado.iostream
import socket
import logging
from collections import deque

class VlcClient():
   def __init__(self, host='127.0.0.1', port=4212, password='admin', ioloop = None, on_close=None, on_connected=None):
       self.logger = logging.getLogger('vlc')
       self.ioloop = ioloop or IOLoop.current()

       self.host = host
       self.port = port
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
       #self.stream.read_until( "\r\n> ", callback=self._read_loop )

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
       self.stream.read_until( "\r\n> ", callback=self._callback_wrapper(callback) )

   def _callback_wrapper(self, method):
       def wrapper(data):
           response = unicode(data, 'utf-8', errors='ignore').strip("> ").strip("\r\n")
           self.logger.debug( response )
           if method!=None:
              parsed = self.parse_response(response)
              method( parsed )
           pass
       return wrapper

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
