import logging
import tornado.web
import json
from base import BaseRequestHandler
from tornado.concurrent import run_on_executor

class ManageRequestHandler(BaseRequestHandler):
   future = None

   @tornado.web.asynchronous
   def get(self, action):
       BaseRequestHandler.get(self)
       result = {}

       if action=='refresh':
          if ManageRequestHandler.future != None and not ManageRequestHandler.future.done():
             result['state'] = 'task already running'
          else:   
             ManageRequestHandler.future = self.refresh_playlists()
             result['state'] = 'scheduled'

          self.set_status(200)
          self.write( json.dumps( result ) )
          self.finish()
          return

       self.set_status(400)
       self.finish()

   @run_on_executor
   def refresh_playlists(self):
       self.manager.update()
