# -*- coding: utf-8 -
import logging
from playlists import *

class Config:
   ace      = '127.0.0.1:62062'
   ace_cache = True
   listen   = 6116
   request_prefix = 'iptv/'

   store_dir = '/media/disk/TV/'
   store_muxer = 'ts'
   store_ext   = '.mpg'

   timeouts = {
      'ace_init':  5, 
      'ace_ready': 30,
      'ace_cache': 120,
      'playlist':  30*60*0
   }
   disabled_headers = ['Accept-Ranges', 'Content-Type']
   playlists = [WestcallPlaylist, TuchkaTvPlaylist]

   transcode = None

   loglevel = 'INFO'
   logfile  = 'aceproxy.log'
   loghandlers = ['console', 'file']
   logging  = { 'version': 1,
       'formatters': {
           'default': {
                'format': u'[%(asctime)s][%(levelname)-8s][%(name)-15s] %(message)s'
           }
       },
       'handlers': {
           'console': {
                 'class' : 'logging.StreamHandler'
                ,'formatter': 'default'
           },
           'file': {
                 'class' : 'logging.handlers.RotatingFileHandler'
                ,'formatter': 'default'
                ,'filename': logfile
                ,'maxBytes': 500*1024
                ,'backupCount': 3
           }
       },
       'root': {
          'handlers': loghandlers,
          'level': loglevel,
       }
   }
