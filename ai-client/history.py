import cherrypy

class DropbloxDebugServer(object):
  @cherrypy.expose
  def index(self):
    cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
    return 'Success!'

if __name__ == '__main__':
  cherrypy.quickstart(DropbloxDebugServer(), config={
    'global': {
      'server.socket_host': '0.0.0.0',
      'server.socket_port': 9000,
    },
  })
