import cherrypy
import json

# TODO: Call ./ai in a Popen object here and store stdin/out pipes
# to it. These pipes will be used by the next_move AJAX call (to
# send data about the board to the AI) and by the AI to request
# game logic API results from this server.

class DropbloxAIServer(object):
  def next_move(self, state_json=None):
    # TODO: This function takes in the board state JSON sent by
    # the game board, which decodes to a complete description of
    # the board state.
    #
    # This function should pass this JSON on to the Popen object,
    # then return when the other process responds.
    return json.dumps({'commands': []})
  next_move.exposed = True

cherrypy.quickstart(DropbloxAIServer(), config={
    'global': {
      'server.socket_port': 1900,
    },
    '/': {
      'tools.staticdir.root': '/Users/skishore/Documents/Projects/dropblox/ai-server',
      'tools.staticdir.on': True,
      'tools.staticdir.dir': 'static',
      'tools.staticdir.index': 'index.html',
    },
  })
