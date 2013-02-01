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
import re

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket

model.Database.initialize_db()
CURRENT_COMPETITION = competition.Competition()
TESTING_COMPETITIONS = {} # Socket -> Practice competition instance

class DropbloxWebSocketHandler(WebSocket):
    def handle_competition_msg_from_team(self, msg, team):
        global CURRENT_COMPETITION
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
        team = model.Database.authenticate_team(msg['team_name'], msg['team_password'], session_sock=self)
        if not team:
            self.close(code=messaging.DO_NOT_RECONNECT, reason="Incorrect team name or password")
            return

        if msg['entry_mode'] == 'compete':
            self.handle_competition_msg_from_team(msg, team)
        else:
            self.handle_testing_msg_from_team(msg, team)

    def closed(self, code, reason=None):
        model.Database.report_session_ended(self)
        CURRENT_COMPETITION.disconnect_sock(self)
        if self in TESTING_COMPETITIONS:
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
                kwargs['body'] = body
                return f(*args, **kwargs)
        return wrapped

    @cherrypy.expose
    @admin_only
    def list_teams(self, body):
        response = {}
        response['team_scores'] = {}
        response['team_connect'] = {}
        scores_by_team = model.Database.scores_by_team()
        for team in model.Database.list_all_teams():
            team_name = team[model.Database.TEAM_TEAM_NAME]
            scores = []
            if team_name in scores_by_team:
                scores = scores_by_team[team_name]
            response['team_scores'][team_name] = scores
            response['team_connect'][team_name] = CURRENT_COMPETITION.is_team_connected(team_name)

        return json.dumps(response)

    @cherrypy.expose
    @admin_only
    def competition_state(self, body):
        response = {}
        response['boards'] = {}
        for team in CURRENT_COMPETITION.team_to_game:
            response['boards'][team] = CURRENT_COMPETITION.team_to_game[team].to_dict()

        remaining = len(CURRENT_COMPETITION.team_whitelist) - len(CURRENT_COMPETITION.sock_to_team)
        response['waiting_for_players'] = remaining
        response['round'] = CURRENT_COMPETITION.round
        response['started'] = CURRENT_COMPETITION.started

        return json.dumps(response)

    @cherrypy.expose
    @admin_only
    def start_next_round(self, body):
        if CURRENT_COMPETITION.started:
            raise cherrypy.HTTPError(400, "Can't restart a competition!")

        if not len(CURRENT_COMPETITION.team_whitelist):
            raise cherrypy.HTTPError(400, "Can't start a competition with no participants!")

        for team_name in CURRENT_COMPETITION.team_whitelist:
            if not CURRENT_COMPETITION.is_team_connected(team_name):
                raise cherrypy.HTTPError(400, "Team %s is not connected!" % (team_name,))

        CURRENT_COMPETITION.start_competition()
        return json.dumps({'status': 200, 'message': 'Success!'})

    @cherrypy.expose
    @admin_only
    def whitelist_team(self, body):
        CURRENT_COMPETITION.whitelist_team(body['target_team'])
        return json.dumps({'status': 200, 'message': 'Success!'})

    @cherrypy.expose
    @admin_only
    def blacklist_team(self, body):
        CURRENT_COMPETITION.blacklist_team(body['target_team'])
        return json.dumps({'status': 200, 'message': 'Success!'})

    @cherrypy.expose
    @admin_only
    def end_round(self, body):
        global CURRENT_COMPETITION
        if CURRENT_COMPETITION.started:
          return json.dumps({'status': 400, 'message': "This competition hasn't been started yet!"})
        CURRENT_COMPETITION.record_remaining_games()
        CURRENT_COMPETITION = competition.Competition()
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

        if not re.match("^[A-Za-z0-9]*$", body['team_name']):
            raise cherrypy.HTTPError(400, "Team name can only contain letters (A-Za-z) and numbers (0-9)!")

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
            'server.socket_port': 443,
            'server.ssl_module': 'pyopenssl',
            'server.ssl_certificate':'/home/ubuntu/keys/myserver.crt',
            'server.ssl_private_key':'/home/ubuntu/keys/myserver.key',
            'server.ssl_certificate_chain':'/home/ubuntu/keys/sslchain.crt',
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
