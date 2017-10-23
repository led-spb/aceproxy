# -*- coding: utf-8 -
from aceproxy import Playlist, Channel
import requests, re
import logging
import lxml.cssselect
import lxml.html
import json

class TuchkaTvPlaylist(Playlist):
   def load_cats(self):
       req = self.session.get('http://tuchkatv.ru/')
       tree = lxml.html.fromstring( req.text )

       sel = lxml.cssselect.CSSSelector(u"#slidemenu a:not([target]):not([style])" )
       for item in sel(tree):
           self.parse_channels( u'http://tuchkatv.ru'+item.attrib['href'] )

   def parse_channels(self, url):
       req = self.session.get(url)
       tree = lxml.html.fromstring( req.text )

       sel = lxml.cssselect.CSSSelector(u".maincont > a" )
       for item in sel(tree):
           self.parse_channel( item.attrib['href'] )

   def parse_channel(self, url):
       req = self.session.get(url)

       m = re.search( u'<title>(?:Канал )?(.*?) (?:смотреть|&raquo;|онлайн)', req.text, re.I+re.M+re.U )
       name = url
       if m!=None:
          name = m.group(1)

       for match in re.finditer( '<option value="\/player.php\?id=(.*?)"', req.text, re.I+re.M ):
           stream_url = match.group(1)
           if stream_url!=None and stream_url!="":
              self.logger.debug( "%s %s: %s" % (url, name, stream_url) )
              ch = Channel(
                    id      = self.uuid( name.encode('utf-8')  ),
                    name    = name, 
                    url     = stream_url,
                    tags    = ['tuchka'],
                    hd      = ' HD' in name,
                    logo    = None
              )
              self.add(ch)

   def load(self):
       self.logger = logging.getLogger('tuchkatv')
       self.session = requests.Session()
       self.session.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.66 Safari/537.36',
            'Accept-Charset': 'utf-8'
       }
       self.session.proxies = {'http': 'socks5://192.168.168.2:9050' }
       self.load_cats()
       self.logger.info('Loaded %d channels', len(self.items) )
