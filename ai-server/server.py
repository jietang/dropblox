#!/usr/bin/env python
#
# This is the centralized game server for
# our Dropblox AI programming competition.
#

import functools
import json
import os
import re
import sys
import time

import bcrypt
import cherrypy

import competition
import messaging
import model
import util

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket

CURRENT_COMPETITION = competition.Competition()
TESTING_COMPETITIONS = {} # Socket -> Practice competition instance

def seconds_remaining_in_competition(competition):
    return util.AI_CLIENT_TIMEOUT + competition.ts - int(time.time())

class DropbloxWebSocketHandler(WebSocket):
    def __init__(self):
        self.test_competition = None

    def handle_competition_msg_from_team(self, msg, team):
        # RH: slowly turning these into RPCs
        global CURRENT_COMPETITION
        team_name = team[model.Database.TEAM_TEAM_NAME]
        if msg['type'] == messaging.CREATE_NEW_GAME_MSG:
            CURRENT_COMPETITION.register_team(team_name, self)
        elif msg['type'] == messaging.SUBMIT_MOVE_MSG:
            CURRENT_COMPETITION.make_move(team_name, self, msg['move_list'])

    def received_message(self, msg):
        print "received_message %s" % msg
        msg = json.loads(str(msg))
        team = model.Database.authenticate_team(msg['team_name'], msg['team_password'], session_sock=self)
        if not team:
            self.close(code=messaging.DO_NOT_RECONNECT, reason="Incorrect team name or password")
            return

        if msg['entry_mode'] == 'compete':
            self.handle_competition_msg_from_team(msg, team)

    def closed(self, code, reason=None):
        model.Database.report_session_ended(self)
        CURRENT_COMPETITION.disconnect_sock(self)
        if self in TESTING_COMPETITIONS:
            TESTING_COMPETITIONS[self].disconnect_sock(self)
            del TESTING_COMPETITIONS[self]
        
class DropbloxGameServer(object):
    def __init__(self, db):
        self.db = db

    @cherrypy.expose
    def ws(self):
        "Method must exist to serve as a exposed hook for the websocket"
        pass

    def require_team_auth(admin_only=False):
        def wrapper(f):
            @functools.wraps(f)
            def wrapped(self, *args, **kwargs):
                body = cherrypy.request.json
                with self.db.transaction() as trans:
                    cherrypy.request.trans = trans
                    team = trans.authenticate_team(body['team_name'], body['password'])
                    if not team or (admin_only and not team.is_admin):
                        raise cherrypy.HTTPError(401, "You are not authorized to perform this action.")
                    return f(self, *args, team=team, body=body, **kwargs)
                del cherrypy.request.trans
            return cherrypy.tools.json_out()(cherrypy.tools.json_in()(wrapped))
        return wrapper

    @cherrypy.expose
    @require_team_auth(admin_only=True)
    def list_teams(self, team, body):
        trans = cherrypy.request.trans
        current_tournament = trans.get_current_tournament()
        response = {}
        response['team_scores'] = {}
        response['team_connect'] = {}
        response['team_whitelisted'] = {}
        # ordered by team_name
        teams = trans.list_all_teams_for_tournament(current_tournament.id)
        scores_by_team = trans.get_scores_by_team_for_tournament(current_tournament.id)
        for team in teams:
            team_name = team.name
            response['team_scores'][team_name] = scores_by_team.get(team.id, [])
            response['team_connect'][team_name] = team.is_connected
            response['team_whitelisted'][team_name] = team.is_whitelisted_next_round

        print response
        return response

    @cherrypy.expose
    @require_team_auth(admin_only=True)
    def competition_state(self, team, body):
        response = {}
        response['boards'] = {}
        for team in CURRENT_COMPETITION.team_to_game:
            response['boards'][team] = CURRENT_COMPETITION.team_to_game[team].to_dict()

        remaining = len(CURRENT_COMPETITION.team_whitelist) - len(CURRENT_COMPETITION.sock_to_team)
        response['waiting_for_players'] = remaining
        response['round'] = CURRENT_COMPETITION.round
        response['started'] = CURRENT_COMPETITION.started

        return response

    @cherrypy.expose
    @require_team_auth(admin_only=True)
    def start_next_round(self, trans, team, body):
        if CURRENT_COMPETITION.started:
            raise cherrypy.HTTPError(400, "Can't restart a competition!")

        if not len(CURRENT_COMPETITION.team_whitelist):
            raise cherrypy.HTTPError(400, "Can't start a competition with no participants!")

        for team_name in CURRENT_COMPETITION.team_whitelist:
            if not CURRENT_COMPETITION.is_team_connected(team_name):
                raise cherrypy.HTTPError(400, "Team %s is not connected!" % (team_name,))

        CURRENT_COMPETITION.start_competition()
        return {'status': 200, 'message': 'Success!'}

    @cherrypy.expose
    @require_team_auth(admin_only=True)
    def whitelist_team(self, team, body):
        trans = cherrypy.request.trans
        current_tournament = trans.get_current_tournament()
        print body['target_team']
        trans.set_is_whitelisted_team_by_name(current_tournament.id, body['target_team'], True)
        return {'status': 200, 'message': 'Success!'}

    @cherrypy.expose
    @require_team_auth(admin_only=True)
    def blacklist_team(self, team, body):
        trans = cherrypy.request.trans
        current_tournament = trans.get_current_tournament()
        trans.set_is_whitelisted_team_by_name(current_tournament.id, body['target_team'], False)
        return {'status': 200, 'message': 'Success!'}

    @cherrypy.expose
    @require_team_auth(admin_only=True)
    def end_round(self, body):
        global CURRENT_COMPETITION
        if not CURRENT_COMPETITION.started:
          raise cherrypy.HTTPError(400, "This competition hasn't been started yet!")
        CURRENT_COMPETITION.record_remaining_games()
        CURRENT_COMPETITION = competition.Competition()
        return {'status': 200, 'message': 'Success!'}

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

        with self.db.transaction() as trans:
            team = trans.get_team_by_name(body['team_name'])
            if team:
                raise cherrypy.HTTPError(400, "Team name already taken!")

            current_tournament = trans.get_current_tournament()
            if current_tournament is None:
                raise Exception("No tournament in progress!")

            hashed = bcrypt.hashpw(body['password'], bcrypt.gensalt())
            trans.add_team(current_tournament.id, body['team_name'], hashed)
            has_contact_info = False
            for em, nm in [('email%d' % i, 'name%d' % i) for i in range(1,4)]:
                if body[em] and body[nm]:
                    if "@" not in body[em]:
                        raise cherrypy.HTTPError(400, "Malformed email address")
                    trans.add_team_member(current_tournament.id, body['team_name'], body[em], body[nm])
                    has_contact_info = True
            if not has_contact_info:
                raise cherrypy.HTTPError(400, "Need at least one email and name per team")
            return json.dumps({'status': 200, 'message': 'Success!'})

    @cherrypy.expose
    @require_team_auth()
    def login(self, team, body):
        return {'status': 200, 'message': 'Success!'}

    @cherrypy.expose
    @require_team_auth()
    def create_practice_game(self, team, body):
        trans = cherrypy.request.trans
        game = trans.create_practice_game(team.id)
        competition = trans.get_competition_by_id(game.competition_id)
        return {
            'ret': 'ok',
            'game': game.to_dict(),
            'competition_seconds_remaining': seconds_remaining_in_competition(competition),
            }

    @cherrypy.expose
    @require_team_auth()
    def submit_game_move(self, team, body):
        game_id = body['game_id']
        team_id = team.id
        moves_made = body['moves_made']
        move_list = body['move_list']
        trans = cherrypy.request.trans

        game = trans.get_game_by_id(game_id)

        if game is None:
            return {'ret': 'fail',
                    'code': messaging.CODE_GAMES_DOES_NOT_EXIST,
                    'reason': "This team is not active."}

        if game.team_id != team_id:
            return {'ret': 'fail',
                    'code': messaging.CODE_TEAM_NOT_AUTHORIZED,
                    'reason': "Your team is not authorized to submit moves for this game."}

        if game.number_moves_made != moves_made:
            return {'ret': 'fail',
                    'code': messaging.CODE_CONCURRENT_MOVE,
                    'reason': "Someone else has already made this move."}

        competition = trans.get_competition_by_id(game.competition_id)
        game_started_at = int(competition.ts - time.time())

        game_state = game.game_state

        if seconds_remaining_in_competition(competition) <= 0:
                # game is over
                game_state.state = 'failed'
        else:
                # this mutates the in-memory verison
                # of game.game_state
                game_state.send_commands(move_list)

        trans.update_game(game_id,
                          moves_made + 1,
                          game_state,
                          game_state.score,
                          game_state.state == 'failed')

        if game_state.state == 'failed':
            return {'ret': 'fail',
                    'code': messaging.CODE_GAME_OVER,
                    'reason': "Game Is over!",
                    'game_state': game_state.to_dict()}

        assert game_state.state == 'playing'

        return {
            'ret': 'ok',
            'game': game.to_dict(),
            'competition_seconds_remaining':  seconds_remaining_in_competition(competition),
            }
    
    @cherrypy.expose
    @require_team_auth
    def wait_for_game(self, team, body):
        while True:
            time.sleep(1)
        return {'ret': 'ok'}
            

def jsonify_error(status, message, traceback, version):
    response = cherrypy.response
    response.headers['Content-Type'] = 'application/json'
    return json.dumps({'status': status, 'message': message})

def main(argv):
    db_model = model.Database()

    WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = WebSocketTool()

    if len(argv) > 1:
        # read info from a config file
        with open(argv[1]) as f:
            global_config = json.load(f)
            global_config = {k: (str(v) if type(v) is unicode else v)
                             for (k, v) in global_config.iteritems()}
    else:
        global_config = {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 8080,
#            'server.ssl_module': 'pyopenssl',
#            'server.ssl_certificate': '/home/ubuntu/keys/myserver.crt',
#            'server.ssl_private_key': '/home/ubuntu/keys/myserver.key',
#            'server.ssl_certificate_chain': '/home/ubuntu/keys/sslchain.crt',
            }

    config = {
        'global': global_config,
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
        }

    cherrypy.quickstart(DropbloxGameServer(db_model), config=config)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
