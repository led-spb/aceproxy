from proxy import ProxyRequestHandler
from base import BaseRequestHandler
from ace import AceClient
import tornado.web
import json
import datetime
import os.path


class RecordRequestHandler(ProxyRequestHandler):
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
