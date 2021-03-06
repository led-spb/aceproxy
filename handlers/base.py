import tornado.web
import logging

class BaseRequestHandler(tornado.web.RequestHandler):
   request_id = 0

   def initialize(self, **kwargs):
       for attr, value in kwargs.iteritems():
           setattr(self, attr, value)

   def gen_request_id(self):
       if self.request_id == BaseRequestHandler.request_id:
          self.request_id = BaseRequestHandler.request_id
          BaseRequestHandler.request_id = self.request_id + 1
       return self.request_id

   def find_channel(self, string):
       self.logger.debug("Searching channel %s", string )
       result = self.manager.find_channel(string)
       if len(result)>0:
          res = result[0]
          self.logger.debug("Finded channel %s, uid=%s, url=%s", res.name, res.id, res.url )
          self.logger.debug( str(res) )
          return res
       else:
          return None
   
   @tornado.web.asynchronous
   def get(self, *args, **kwargs):
       self.gen_request_id()
       self.logger = logging.getLogger('req').getChild( "%05d" % self.request_id )

       self.logger.debug("%s %s %s", self.request.method, unicode(self.request.uri,'utf-8'), self.request.version )
       for (k,v) in self.request.headers.get_all():
           self.logger.debug( "%s: %s", k,v ) 
       self.logger.debug("")

   def _handle_request_exception(self, e):
       self.logger.exception("Error while handle request")
       tornado.web.RequestHandler._handle_request_exception(self, e)
