#!/usr/bin/env python
#
# This is the centralized game server for
# our Dropblox AI programming competition.
#

import competition
import messaging
import cherrypy
import random
import bcrypt
import model
import time
import json
import util
import os

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket

from logic.Board import Board

# Admin
ADMIN_HASHED_PW = "$2a$12$xmaAYZoZEyqGZWfoXZfZI.ik3mjrzVcGOg3sxvnfFU/lS5n6lgqyy"

# Global variables (in-memory state)
GAME_ID_TO_WEBSOCKET = {}
GAMES = {}
COMPETITION_SEED = None
COMPETITION_IN_PROGRESS = False

def start_game(game_id):
    print "starting game with id %s" % game_id
    conn = GAME_ID_TO_WEBSOCKET[game_id]
    if not conn.started:
      msg = {
          'type' : messaging.AWAITING_NEXT_MOVE_MSG,
          'game_state' : GAMES[game_id].to_dict(),
      }
      conn.send(json.dumps(msg))
      conn.move_requested_at = time.time()
      conn.started = True

CURRENT_COMPETITION = competition.Competition()

class DropbloxWebSocketHandler(WebSocket):
    game_id = -1
    started = False
    move_requested_at = None
    
    def handle_competition_msg_from_team(self, msg, team):
        team_name = team[model.Database.TEAM_TEAM_NAME]
        if msg['type'] == messaging.CREATE_NEW_GAME_MSG:
            CURRENT_COMPETITION.register_team(team_name, self)
        elif msg['type'] == messaging.SUBMIT_MOVE_MSG:
            CURRENT_COMPETITION.make_move(team_name, self, msg['move_list'])

    def handle_testing_msg_from_team(self, msg, team):
        pass

    def received_message(self, msg):
        print "received_message %s" % msg
        msg = json.loads(str(msg))
        team = model.Database.authenticate_team(msg['team_name'], msg['team_password'])
        if not team:
            self.close(code=messaging.DO_NOT_RECONNECT, reason="Incorrect team name or password")

        if msg['entry_mode'] == 'compete':
            self.handle_competition_msg_from_team(msg, team)
            return

        self.handle_testing_msg_from_team(msg, team)

        #if COMPETITION_IN_PROGRESS:
        #    if msg['type'] != SUBMIT_MOVE_MSG:
        #        self.close(code=DO_NOT_RECONNECT, reason='A competition is currently in progress')
        #        return

        if msg['type'] == messaging.CREATE_NEW_GAME_MSG:
            #if COMPETITION_SEED and 'team_name' not in msg:
            #    self.close(code=DO_NOT_RECONNECT, reason='A team name must be provided to enter the competition')
            #    return

            self.game_id = util.generate_game_id()
            GAME_ID_TO_WEBSOCKET[self.game_id] = self
            GAMES[self.game_id] = Board(seed=COMPETITION_SEED)
            print "GAME_ID_TO_WEBSOCKET: %s" % GAME_ID_TO_WEBSOCKET
            response = {
                'type' : messaging.NEW_GAME_CREATED_MSG,
            }
            #if 'team_name' not in msg:
                # Game IDs are hidden during competition
            response['game_id'] = self.game_id
            print "sending " + str(response)
            self.send(json.dumps(response))
        elif msg['type'] == messaging.CONNECT_TO_EXISTING_GAME_MSG:
            if msg['game_id'] in GAMES:
                self.game_id = msg['game_id']
                GAME_ID_TO_WEBSOCKET[self.game_id] = self
                self.started = True

                game = GAMES[self.game_id]
                if game.state == 'playing':
                    response = {
                        'type': messaging.AWAITING_NEXT_MOVE_MSG,
                        'game_state': game.to_dict(),
                    }
                    self.send(json.dumps(response))
                    self.move_requested_at = time.time()
            else:
                self.close(code=messaging.DO_NOT_RECONNECT, reason='Game no longer exists')
        elif msg['type'] == messaging.SUBMIT_MOVE_MSG:
            game = GAMES[self.game_id]

            commands = msg['move_list']
            if time.time() - self.move_requested_at > AI_CLIENT_TIMEOUT:
                commands = ['drop']
            game.send_commands(commands)
            if game.state == 'playing':
              response = {
                  'type': messaging.AWAITING_NEXT_MOVE_MSG,
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
            global COMPETITION_SEED
            global COMPETITION_IN_PROGRESS
            COMPETITION_SEED = None
            COMPETITION_IN_PROGRESS = False
            for conn in GAME_ID_TO_WEBSOCKET.values():
                conn.close(code=messaging.DO_NOT_RECONNECT, reason="Clearing all games")
            GAMES.clear()
        else:
            return 'Incorrect password!'

    @cherrypy.expose
    def open_competition(self, password, seed):
        if bcrypt.hashpw(password, ADMIN_HASHED_PW) == ADMIN_HASHED_PW:
            for conn in GAME_ID_TO_WEBSOCKET.values():
                conn.close(code=messaging.DO_NOT_RECONNECT, reason="Clearing all games")
            GAMES.clear()

            global COMPETITION_SEED
            COMPETITION_SEED = seed
        else:
            return 'Incorrect password!'

    @cherrypy.expose
    def begin_competition(self, password):
        if not COMPETITION_SEED:
            return 'Must call /open_competition with a seed first!'
        if bcrypt.hashpw(password, ADMIN_HASHED_PW) == ADMIN_HASHED_PW:
            global COMPETITION_IN_PROGRESS
            COMPETITION_IN_PROGRESS = True
            for game_id in GAME_ID_TO_WEBSOCKET:
                start_game(game_id)
        else:
            return 'Incorrect password!'

    @cherrypy.expose
    def signup(self):
        cl = cherrypy.request.headers['Content-Length']
        rawbody = cherrypy.request.body.read(int(cl))
        body = json.loads(rawbody)

        if len(body['team_name']) < 5:
            raise cherrypy.HTTPError(400, "Team name must be at least 5 characters long!")

        if len(body['password']) < 5:
            raise cherrypy.HTTPError(400, "Password must be at least 5 characters long!") 
        
        team = model.Database.get_team(body['team_name'])
        if team:
            raise cherrypy.HTTPError(400, "Team name already taken!")

        hashed = bcrypt.hashpw(body['password'], bcrypt.gensalt())
        model.Database.add_team(body['team_name'], hashed)
        return "Success"

    @cherrypy.expose
    def login(self):
        cl = cherrypy.request.headers['Content-Length']
        rawbody = cherrypy.request.body.read(int(cl))
        body = json.loads(rawbody)
        
        team = model.Database.authenticate_team(body['team_name'], body['password'])
        if not team:
            raise cherrypy.HTTPError(401, "Incorrect team name or password")

        return "Success"
                

if __name__ == '__main__':
    WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = WebSocketTool()

    model.Database.initialize_db()

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
