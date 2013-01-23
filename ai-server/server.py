#!/usr/bin/env python
#
# This is the centralized game server for
# our Dropblox AI programming competition.
#

import cherrypy
import random
import json

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket

# Messaging protocol
CREATE_NEW_GAME_MSG = 'CREATE_NEW_GAME'
NEW_GAME_CREATED_MSG = 'NEW_GAME_CREATED'

def generate_game_id():
    choices = 'abcdefghijklmnopqrstuvwxyz'
    choices += choices.upper()
    choices += '0123456789'
    while True:
        candidate = ''.join([random.choice(choices) for i in xrange(8)])
        # TODO: check to make sure game doesn't already exist
        break
    return candidate

class DropbloxWebSocketHandler(WebSocket):
    def received_message(self, msg):
        print "received_message %s" % msg
        msg = json.loads(str(msg))
        if msg['type'] == CREATE_NEW_GAME_MSG:
            # TODO create new game instance
            game_id = generate_game_id()
            response = {
                'type' : NEW_GAME_CREATED_MSG,
                'game_id' : game_id,
            }
            self.send(json.dumps(response))
        else:
            print "Received unsupported message type"

    def closed(self, code, reason=None):
        print "Connection to client closed. Code=%s, Reason=%s" % (code, reason)

class DropbloxGameServer(object):
    @cherrypy.expose
    def ws(self):
        "Method must exist to serve as a exposed hook for the websocket"
        pass

if __name__ == '__main__':
    WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = WebSocketTool()

    cherrypy.quickstart(DropbloxGameServer(), config={
        'global': {
            'server.socket_port': 9000,
        },
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': DropbloxWebSocketHandler
        },
        '/': {
            'tools.staticdir.root': '/Users/spoletto/source/dropblox/ai-server',
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'static',
            'tools.staticdir.index': 'index.html',
        },
    })
