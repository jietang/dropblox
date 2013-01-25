import cherrypy
import json
import os

LOGGING_DIR = os.path.join(os.getcwd(), 'history')

class DropbloxDebugServer(object):
  @cherrypy.expose
  def index(self):
    cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
    response = {'code': 200}
    if not os.path.exists(LOGGING_DIR):
      response['code'] = 401
      response['error'] = (
        '<div>The history directory does not exist yet.<div>'
        '<div class="spaced">It will be created when you test an AI with '
        '<span class="code">python client.py test</span>.<div>'
      )
      return json.dumps(response)
    response['games'] = []
    game_dirs = os.listdir(LOGGING_DIR)
    for game_dir in game_dirs:
      try:
        timestamp = int(game_dir.split('_')[1])
      except IndexError, ValueError:
        pass
      response['games'].append({
        'timestamp': timestamp,
        'game_dir': game_dir,
      })
    if not response['games']:
      response['code'] = 401
      response['error'] = (
        '<div>The history directory exists, but there are no games in it.<div>'
        '<div class="spaced">You can make your AI play a game by running '
        '<span class="code">python client.py test</span>.<div>'
      )
      return json.dumps(response)
    response['games'].sort(key=lambda x: x['timestamp'])
    return json.dumps(response)

if __name__ == '__main__':
  cherrypy.quickstart(DropbloxDebugServer(), config={
    'global': {
      'server.socket_host': '0.0.0.0',
      'server.socket_port': 9000,
    },
  })
