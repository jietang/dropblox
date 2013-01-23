#!/usr/bin/env python
#
# This is the centralized game server for
# our Dropblox AI programming competition.
#

import cherrypy
import random
import bcrypt
import time
import json
import os

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket

from logic.Board import Board

# Admin
ADMIN_HASHED_PW = "$2a$12$xmaAYZoZEyqGZWfoXZfZI.ik3mjrzVcGOg3sxvnfFU/lS5n6lgqyy"
AI_CLIENT_TIMEOUT = 11 # Allow 1 second extra for latency

# Messaging protocol
CREATE_NEW_GAME_MSG = 'CREATE_NEW_GAME'
CONNECT_TO_EXISTING_GAME_MSG = 'CONNECT_TO_EXISTING_GAME'
NEW_GAME_CREATED_MSG = 'NEW_GAME_CREATED'
AWAITING_NEXT_MOVE_MSG = 'AWAITING_NEXT_MOVE'
SUBMIT_MOVE_MSG = 'SUBMIT_MOVE'
DO_NOT_RECONNECT = 1001

# Global variables (in-memory state)
GAME_ID_TO_WEBSOCKET = {}
GAMES = {}
COMPETITION_SEED = None

def start_game(game_id):
    conn = GAME_ID_TO_WEBSOCKET[game_id]
    if not conn.started:
      msg = {
          'type' : AWAITING_NEXT_MOVE_MSG,
          'game_state' : GAMES[game_id].to_dict(),
      }
      conn.send(json.dumps(msg))
      conn.move_requested_at = time.time()
      conn.started = True

def generate_game_id():
    choices = 'abcdefghijklmnopqrstuvwxyz'
    choices += choices.upper()
    choices += '0123456789'
    while True:
        candidate = ''.join([random.choice(choices) for i in xrange(12)])
        break
    return candidate

class DropbloxWebSocketHandler(WebSocket):
    game_id = -1
    started = False
    move_requested_at = None

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
            }
            if 'team_name' not in msg:
                if not COMPETITION_SEED:
                    response['game_id'] = self.game_id
                else:
                    self.close(code=DO_NOT_RECONNECT, reason='A team name must be provided to enter the competition')
                    return

            self.send(json.dumps(response))
        elif msg['type'] == CONNECT_TO_EXISTING_GAME_MSG:
            if msg['game_id'] in GAMES:
                self.game_id = msg['game_id']
                GAME_ID_TO_WEBSOCKET[self.game_id] = self
                self.started = True

                game = GAMES[self.game_id]
                if game.state == 'playing':
                    response = {
                        'type': AWAITING_NEXT_MOVE_MSG,
                        'game_state': game.to_dict(),
                    }
                    self.send(json.dumps(response))
                    self.move_requested_at = time.time()
            else:
                self.close(code=DO_NOT_RECONNECT, reason='Game no longer exists')
        elif msg['type'] == SUBMIT_MOVE_MSG:
            game = GAMES[self.game_id]

            commands = msg['move_list']
            if time.time() - self.move_requested_at > AI_CLIENT_TIMEOUT:
                commands = ['drop']
            game.send_commands(commands)
            if game.state == 'playing':
              response = {
                  'type': AWAITING_NEXT_MOVE_MSG,
                  'game_state': game.to_dict(),
              }
              self.send(json.dumps(response))
              self.move_requested_at = time.time()
        else:
            print "Received unsupported message type"

    def closed(self, code, reason=None):
        print "Connection to client closed. Code=%s, Reason=%s" % (code, reason)
        if self.game_id in GAME_ID_TO_WEBSOCKET:
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
    def game_state(self, game_id):
        try:
            return json.dumps(GAMES[game_id].to_dict())
        except KeyError:
            return 'Game not found!'

    @cherrypy.expose
    def clear_games(self, password):
        if bcrypt.hashpw(password, ADMIN_HASHED_PW) == ADMIN_HASHED_PW:
            COMPETITION_SEED = None
            for conn in GAME_ID_TO_WEBSOCKET.values():
                conn.close(code=DO_NOT_RECONNECT, reason="Clearing all games")
            GAMES.clear()
        else:
            return 'Incorrect password!'

    @cherrypy.expose
    def open_competition(self, password, seed):
        if bcrypt.hashpw(password, ADMIN_HASHED_PW) == ADMIN_HASHED_PW:
            for conn in GAME_ID_TO_WEBSOCKET.values():
                conn.close(code=DO_NOT_RECONNECT, reason="Clearing all games")
            GAMES.clear()

            COMPETITION_SEED = seed
        else:
            return 'Incorrect password!'

    @cherrypy.expose
    def begin_competition(self, password):
        if bcrypt.hashpw(password, ADMIN_HASHED_PW) == ADMIN_HASHED_PW:
            for game_id in GAME_ID_TO_WEBSOCKET:
                start_game(game_id)
        else:
            return 'Incorrect password!'            

if __name__ == '__main__':
    WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = WebSocketTool()

    cherrypy.quickstart(DropbloxGameServer(), config={
        'global': {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 80,
        },
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': DropbloxWebSocketHandler
        },
        '/': {
            'tools.staticdir.root': os.getcwd(),
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'static',
            'tools.staticdir.index': 'index.html',
        },
    })
