import tornado.web
from base import BaseRequestHandler
import json

class PlaylistRequestHandler(BaseRequestHandler):

   def get(self, name):
       BaseRequestHandler.get(self)

       self.logger.info("Searching %s", name )
       result = self.manager.find_channel( name, False )

       self.set_status(200)
       if self.get_argument('json',None)!=None:
          self.set_header('Content-Type', 'application/json' )
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

