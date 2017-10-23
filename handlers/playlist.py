import tornado.web
from base import BaseRequestHandler
import json

class PlaylistRequestHandler(BaseRequestHandler):

   def get(self, name):
       name = name.strip('/') if name!=None else ''
       BaseRequestHandler.get(self)
       self.logger.debug("Searching %s", name )
       result = self.manager.find_channel( name, False )
       uniq=[]

       self.set_status(200)
       if self.get_argument('json',None)!=None:

          self.set_header('Content-Type', 'application/json' )
          response = []
          for item in result:
              if item.id not in uniq:
                 uniq.append( item.id )
                 response.append( {'id': item.id, 'name': item.name, 'tags': item.tags, 'hd': item.hd, 'url': item.url, 'logo': item.logo} )
          self.write( json.dumps(response) )

       else:
         self.set_header('Content-Type', 'audio/x-mpegurl' )
         self.set_header('Content-Disposition', 'attachment; filename="'+name+'.m3u"')
         self.write("#EXTM3U url-tvg=\"http://www.teleguide.info/download/new3/jtv.zip\"\r\n" )

         url = "%s://%s" % (self.request.protocol,self.request.host)
         for item in result:
             if item.id not in uniq:
                uniq.append( item.id )

                self.write("#EXTINF:-1 group-title=\"%s\" tvg-name=\"%s\", %s\r\n" % (",".join( item.tags ), item.name, item.name ) )
                self.write("%s/channel/uuid/%s\r\n" % (url,item.id) )
       self.finish()
   pass

