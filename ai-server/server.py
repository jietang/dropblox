#!/usr/bin/env python
#
# This is the centralized game server for
# our Dropblox AI programming competition.
#

import competition
import messaging
import cherrypy
import bcrypt
import model
import json
import os

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket

model.Database.initialize_db()
CURRENT_COMPETITION = competition.Competition()
TESTING_COMPETITIONS = {} # Socket -> Practice competition instance

class DropbloxWebSocketHandler(WebSocket):    
    def handle_competition_msg_from_team(self, msg, team):
        team_name = team[model.Database.TEAM_TEAM_NAME]
        if msg['type'] == messaging.CREATE_NEW_GAME_MSG:
            CURRENT_COMPETITION.register_team(team_name, self)
        elif msg['type'] == messaging.SUBMIT_MOVE_MSG:
            CURRENT_COMPETITION.make_move(team_name, self, msg['move_list'])

    def handle_testing_msg_from_team(self, msg, team):
        team_name = team[model.Database.TEAM_TEAM_NAME]
        if msg['type'] == messaging.CREATE_NEW_GAME_MSG:
            test_competition = competition.Competition(is_test_run=True)
            TESTING_COMPETITIONS[self] = test_competition
            test_competition.whitelist_team(team_name)
            test_competition.register_team(team_name, self)
            test_competition.start_competition()
        elif msg['type'] == messaging.SUBMIT_MOVE_MSG:
            TESTING_COMPETITIONS[self].make_move(team_name, self, msg['move_list'])

    def received_message(self, msg):
        print "received_message %s" % msg
        msg = json.loads(str(msg))
        team = model.Database.authenticate_team(msg['team_name'], msg['team_password'])
        if not team:
            self.close(code=messaging.DO_NOT_RECONNECT, reason="Incorrect team name or password")

        if msg['entry_mode'] == 'compete':
            self.handle_competition_msg_from_team(msg, team)
        else:
            self.handle_testing_msg_from_team(msg, team)

    def closed(self, code, reason=None):
        CURRENT_COMPETITION.disconnect_sock(self)
        TESTING_COMPETITIONS[self].disconnect_sock(self)
        del TESTING_COMPETITIONS[self]
        
class DropbloxGameServer(object):
    @cherrypy.expose
    def ws(self):
        "Method must exist to serve as a exposed hook for the websocket"
        pass

    def admin_only(f):
        def wrapped(*args, **kwargs):
            cl = cherrypy.request.headers['Content-Length']
            rawbody = cherrypy.request.body.read(int(cl))
            body = json.loads(rawbody)

            team = model.Database.authenticate_team(body['team_name'], body['password'])
            if not team or not team[model.Database.TEAM_IS_ADMIN]:
                raise cherrypy.HTTPError(401, "You are not authorized to perform this action.")
            else:
                return f(*args, **kwargs)
        return wrapped

    @cherrypy.expose
    @admin_only
    def start_competition(self):        
        CURRENT_COMPETITION.start_competition()
        return json.dumps({'status': 200, 'message': 'Success!'})

    @cherrypy.expose
    #@admin_only
    def list_teams(self):
        response = {}
        for team in model.Database.list_all_teams():
            team_name = team[model.Database.TEAM_TEAM_NAME]
            response[team_name] = model.Database.scores_by_team(team_name)
        return json.dumps(response)

    @cherrypy.expose
    @admin_only
    def competition_state(self):
        response = {}
        for team in CURRENT_COMPETITION.team_to_game():
            response[team] = CURRENT_COMPETITION.team_to_game[team].to_dict()
        return json.dumps(response)

    @cherrypy.expose
    #@admin_only
    def prepare_next_round(self):
        cl = cherrypy.request.headers['Content-Length']
        rawbody = cherrypy.request.body.read(int(cl))
        body = json.loads(rawbody)

        CURRENT_COMPETITION = competition.Competition()
        for team_name in body['next_round_teams']:
            team = model.Database.get_team(team_name)
            if not team:
                raise cherrypy.HTTPError(400, "Team name specified does not exist!")
            CURRENT_COMPETITION.whitelist_team(team_name)

        return json.dumps({'status': 200, 'message': 'Success!'})

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
        return json.dumps({'status': 200, 'message': 'Success!'})

    @cherrypy.expose
    def login(self):
        cl = cherrypy.request.headers['Content-Length']
        rawbody = cherrypy.request.body.read(int(cl))
        body = json.loads(rawbody)
        
        team = model.Database.authenticate_team(body['team_name'], body['password'])
        if not team:
            raise cherrypy.HTTPError(401, "Incorrect team name or password.")

        return json.dumps({'status': 200, 'message': 'Success!'})
                
def jsonify_error(status, message, traceback, version):
    response = cherrypy.response
    response.headers['Content-Type'] = 'application/json'
    return json.dumps({'status': status, 'message': message})

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
            'error_page.default': jsonify_error,
        },
    })
