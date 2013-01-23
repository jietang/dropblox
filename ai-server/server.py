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

from logic.Board import Board

# Messaging protocol
CREATE_NEW_GAME_MSG = 'CREATE_NEW_GAME'
NEW_GAME_CREATED_MSG = 'NEW_GAME_CREATED'
AWAITING_NEXT_MOVE_MSG = 'AWAITING_NEXT_MOVE'
SUBMIT_MOVE_MSG = 'SUBMIT_MOVE'

# Global variables (in-memory state)
GAME_ID_TO_WEBSOCKET = {}
GAMES = {}

def start_game(game_id):
    conn = GAME_ID_TO_WEBSOCKET[game_id]
    if conn:
        msg = {
            'type' : AWAITING_NEXT_MOVE_MSG,
            'game_state' : GAMES[game_id].to_dict(),
        }
        conn.send(json.dumps(msg))

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
    game_id = -1

    def received_message(self, msg):
        print "received_message %s" % msg
        msg = json.loads(str(msg))
        if msg['type'] == CREATE_NEW_GAME_MSG:
            self.game_id = generate_game_id()
            GAME_ID_TO_WEBSOCKET[self.game_id] = self
            GAMES[self.game_id] = Board()
            print "GAME_ID_TO_WEBSOCKET: %s" % GAME_ID_TO_WEBSOCKET
            response = {
                'type' : NEW_GAME_CREATED_MSG,
                'game_id' : self.game_id,
            }
            self.send(json.dumps(response))
        elif msg['type'] == SUBMIT_MOVE_MSG:
            game = GAMES[self.game_id]
            game.send_commands(msg['move_list'])
            msg = {
                'type': AWAITING_NEXT_MOVE_MSG,
                'game_state': game.to_dict(),
            }
            self.send(json.dumps(msg))
        else:
            print "Received unsupported message type"

    def closed(self, code, reason=None):
        print "Connection to client closed. Code=%s, Reason=%s" % (code, reason)
        del GAME_ID_TO_WEBSOCKET[self.game_id]
        print "GAME_ID_TO_WEBSOCKET: %s" % GAME_ID_TO_WEBSOCKET

class DropbloxGameServer(object):
    @cherrypy.expose
    def ws(self):
        "Method must exist to serve as a exposed hook for the websocket"
        pass

    @cherrypy.expose
    def start(self, game_id):
        # TODO: Make this called from a button on the game page
        start_game(game_id)

    @cherrypy.expose
    def game(self, game_id):
        return json.dumps(GAMES[game_id].to_dict())

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
