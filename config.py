import logging
from playlists import *

class Config:
   ace      = '127.0.0.1:62062'
   ace_cache = True
   listen   = 6116
   request_prefix = 'iptv/'
   store_dir = '/home/pi/Downloads/TV/'
   timeouts = {
      'ace_init':  5, 
      'ace_ready': 30,
      'ace_cache': 60,
      'playlist':  30*60
   }
   disabled_headers = ['Accept-Ranges', 'Content-Type']
   playlists = [TorrentStreamPlaylist]

   transcode = None
   #transcode = '#http{mux=ts,dst=:8717/%s} option sout-keep option sout-all'
   #transcode = '#transcode{vcodec=mp4v,acodec=mpga,vb=800,ab=128}:std{access=http,mux=ogg,dst=:8717/%s} option sout-keep option sout-all'
   #transcode = '#transcode{vcodec=theo,vb=800,acodec=vorb,ab=128,channels=2,samplerate=44100}:std{access=http,mux=ogg,dst=:8717/%s} option sout-keep option sout-all'

   loglevel = 'DEBUG'
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
