#!python
import os
import cherrypy
import json
import random

class Root:
    game_cache = {}
    @cherrypy.expose
    def post_game(self):
        # get post data and print it here
        cl = cherrypy.request.headers['Content-Length']
        rawbody = cherrypy.request.body.read(int(cl))
        body = json.loads(rawbody)
        id_ = str(random.randint(0, 10000))
        self.game_cache[id_] = body
        return "%s" % (id_,)

    @cherrypy.expose
    def view_game(self, id):
        return """
<head>
  <link rel="stylesheet" type="text/css" href="/dropblox.css">
  <link rel="stylesheet" type="text/css" href="/jquery-ui.css">
  <script type="text/javascript" src="/jquery-1.8.3.js"></script>
  <script type="text/javascript" src="/jquery-ui.js"></script>
  <script type="text/javascript" src="/jquery.cookie.js"></script>
  <script type="text/javascript" src="/jquery.zclip.js"></script>
  <script type="text/javascript" src="/board.js"></script>
  <script type="text/javascript" src="/dropblox.js"></script>
  <script type="text/javascript">
  var saved_data = %s;
  </script>
</head>

<body onload="dropblox.initialize()">
  <div id="top-bar">
    <div id="page-title">
      <img src="/images/logo-white.png" />
    </div>
  </div>
  <div id="content">
    <div id="subcontent"></div>
    <div id="rightcontent">
      <div id="history-boards"></div>
      <div id="post-history-boards"></div>
    </div>
  </div>
</body>
""" % repr(json.dumps(self.game_cache.get(id, {})))

if __name__ == '__main__':
    # Set up site-wide config first so we get a log if errors occur.
    cherrypy.config.update({'environment': 'production',
                            'log.error_file': 'site.log',
                            'log.screen': True})

    conf = {'/': {'tools.staticdir.root': os.getcwd(),
                  'tools.staticdir.on': True,
                  'tools.staticdir.dir': 'static',
                  }}

    cherrypy.quickstart(Root(), config=conf)
