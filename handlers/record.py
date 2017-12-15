from proxy import ProxyRequestHandler
from base import BaseRequestHandler
from ace import AceClient
import tornado.web
import json
import datetime
import os.path
import time

class RecordRequestHandler(ProxyRequestHandler):
   records = {}

   @tornado.web.asynchronous
   def get(self, action, content):
       BaseRequestHandler.get(self)
       if action not in ('start','stop','status'):
          self.set_status(400)
          self.finish()
          return

       self.channel = None
       if content!=None:
          self.channel = self.find_channel( content.strip('/') )

       if self.channel==None and action!="status":
          self.set_status(404)
          self.finish()
          return

       if action=='start':
          ProxyRequestHandler.get(self, None, self.channel.id)
          return

       if action=='stop':
          self.ace = AceClient.get_cached( self.channel.url )
          if self.ace!=None:
             self.ace.close()
          self.vlc.send_command("control %s pause\r\ndel %s\r\nshow" % (self.channel.id, self.channel.id), callback=self._on_vlc_data )
          return 

       if action=='status':
          self.vlc.send_command("show", callback=self._on_vlc_data )
          return 
       pass

   def on_finish(self):
       pass

   def _get_ace_status(self, channel_id):
       result = {}
       channels = self.manager.find_channel( channel_id )
       if len(channels)>0:
          channel = channels[0]
          result['url']      = channel.url
          result['channel']  = channel.name

          if channel.url in AceClient.cache:
             ace = AceClient.cache[ channel.url ]
             result['livepos']    = ace.livepos
       return result

   def _get_record_info(self, channel_id):
       if channel_id in RecordRequestHandler.records:
          filename = RecordRequestHandler.records[channel_id]['filename']
          try:
             RecordRequestHandler.records[channel_id].update( {'recorded': os.stat(filename).st_size} )
          except:
             pass
          return RecordRequestHandler.records[channel_id]
       return {}

   def _get_free_size(self):
       try:
         st = os.statvfs( self.config.store_dir )
         return {'disk_total': st.f_frsize*st.f_blocks, 'disk_avail': st.f_frsize*st.f_bavail }
       except:
         return {'disk_total': 0, 'disk_avail': 0}

   def _on_vlc_data(self, data):
       try:
         if 'show' in data and 'media' in data['show']:
            if type(data['show']['media'])!=dict:
               data['show']['media'] = None
            else:
               for channel_id in data['show']['media']:
                   data['show']['media'][channel_id].update( self._get_ace_status(channel_id) )
                   data['show']['media'][channel_id].update( self._get_record_info(channel_id) )
         data.update( self._get_free_size() )

         self.set_status(200)
         self.set_header('Content-Type', 'application/json' )
         self.write( json.dumps(data, indent=2) )
         self.finish()
       except:
         self.set_status(500)
         self.logger.exception('Error parse VLC response')
         self.finish()

   def on_video_ready(self, ace, url):
       self._remove_timeout()

       url = url.replace("/udp/","udp://@")
       self.logger.debug( "record video ready: %s", url )

       self.filename = os.path.join( self.config.store_dir, datetime.datetime.now().strftime("%Y%m%d_%H%M")+"_"+self.channel.name+self.config.store_ext )
       RecordRequestHandler.records[ self.channel.id ] = { 'filename': self.filename, 'started': time.time()*1000 }

       self.vlc.send_command(
             'new "%s" broadcast input "%s" output #std{access=file,mux=%s,dst="%s"} enabled\r\ncontrol %s play\r\nshow' % (self.channel.id, url, self.config.store_muxer, self.filename, self.channel.id),
             callback=self._on_vlc_data
       )
       if ace!=None:
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
