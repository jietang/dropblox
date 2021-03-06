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
import traceback

import bcrypt
import cherrypy

import messaging
import model
import util

def seconds_remaining_in_competition(competition):
    return util.AI_CLIENT_TIMEOUT + competition.ts - int(time.time())

TEAM_ACTIVE_THRESHOLD = 2
def is_team_active(team):
    return (int(time.time()) - team.is_connected) < TEAM_ACTIVE_THRESHOLD

def sanitize_game_state(game_state_dict):
    for k in list(game_state_dict):
        if k not in ["state", "score", "bitmap", "block", "preview"]:
            del game_state_dict[k]

cached_passwords = {}

class DropbloxGameServer(object):
    def __init__(self, db):
        self.db = db

    def require_team_auth(admin_only=False):
        def wrapper(f):
            @functools.wraps(f)
            def wrapped(self, *args, **kwargs):
                body = cherrypy.request.json
                with self.db.transaction() as trans:
                    cherrypy.request.trans = trans

                    if body['team_name'] in cached_passwords:
                        if cached_passwords[body['team_name']] == body['password']:
                            team = trans.authenticate_team(body['team_name'], body['password'], skip_auth=True)
                        else:
                            team = None
                    else:
                        team = trans.authenticate_team(body['team_name'], body['password'])

                    if not team or (admin_only and not team.is_admin):
                        raise cherrypy.HTTPError(401, "You are not authorized to perform this action.")
                    else:
                        cached_passwords[body['team_name']] = body['password']
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
            response['team_connect'][team_name] = is_team_active(team)
            response['team_whitelisted'][team_name] = team.is_whitelisted_next_round

        return response

    @cherrypy.expose
    @require_team_auth(admin_only=True)
    def competition_state(self, team, body):
        trans = cherrypy.request.trans
        current_tournament = trans.get_current_tournament()
        current_competition_state = trans.get_current_competition_state_for_tournament(current_tournament.id)
        response = {}
        response['boards'] = {}

        total_teams = 0
        connected_teams = 0
        for (team, game) in current_competition_state:
            total_teams += 1
            connected_teams += int(bool(is_team_active(team)))
            if game is not None:
                response['boards'][team.name] = game.game_state.to_dict()

        response['waiting_for_players'] = total_teams - connected_teams
        response['round'] = current_tournament.next_competition_index + 1
        response['started'] = bool(response['boards'])

        return response

    @cherrypy.expose
    @require_team_auth(admin_only=True)
    def start_next_round(self, team, body):
        trans = cherrypy.request.trans
        current_tournament = trans.get_current_tournament()
        next_competition = trans.get_competition_by_index(current_tournament.id,
                                                          current_tournament.next_competition_index)
        
        if (next_competition is not None and
            trans.competition_has_started(next_competition.id)):
            raise cherrypy.HTTPError(400, "Can't restart a competition!")

        whitelisted_teams = trans.get_current_whitelisted_teams(current_tournament.id)
        if not whitelisted_teams:
            raise cherrypy.HTTPError(400, "Can't start a competition with no participants!")

        for team in whitelisted_teams:
            if not is_team_active(team):
                raise cherrypy.HTTPError(400, "Team %s is not connected!" % (team.name,))

        trans.start_next_competition(current_tournament.id)

        return {'status': 200, 'message': 'Success!'}

    @cherrypy.expose
    @require_team_auth(admin_only=True)
    def whitelist_team(self, team, body):
        trans = cherrypy.request.trans
        current_tournament = trans.get_current_tournament()

        next_competition = trans.get_competition_by_index(current_tournament.id,
                                                          current_tournament.next_competition_index)
        if (next_competition is not None and
            trans.competition_has_started(next_competition.id)):
            raise cherrypy.HTTPError(400, "Can't whitelist a team while the competition has already begin!")

        trans.set_is_whitelisted_team_by_name(current_tournament.id, body['target_team'], True)
        return {'status': 200, 'message': 'Success!'}

    @cherrypy.expose
    @require_team_auth(admin_only=True)
    def blacklist_team(self, team, body):
        trans = cherrypy.request.trans
        current_tournament = trans.get_current_tournament()

        next_competition = trans.get_competition_by_index(current_tournament.id,
                                                          current_tournament.next_competition_index)
        if (next_competition is not None and
            trans.competition_has_started(next_competition.id)):
            raise cherrypy.HTTPError(400, "Can't blacklist a team while the competition has already begin!")

        trans.set_is_whitelisted_team_by_name(current_tournament.id, body['target_team'], False)
        return {'status': 200, 'message': 'Success!'}

    @cherrypy.expose
    @require_team_auth(admin_only=True)
    def end_round(self, team, body):
        trans = cherrypy.request.trans
        current_tournament = trans.get_current_tournament()

        next_competition = trans.get_competition_by_index(current_tournament.id,
                                                          current_tournament.next_competition_index)
        if (next_competition is None or
            not trans.competition_has_started(next_competition.id)):
            raise cherrypy.HTTPError(400, "This competition hasn't been started yet!")
        
        for game in trans.games_for_competition(next_competition.id):
            gs = game.game_state
            gs.state = 'failed'
            trans.update_game(game.id, game.number_moves_made,
                              gs, gs.score, True)

        trans.increment_next_competition_index(current_tournament.id)
        trans.reset_whitelist_state(current_tournament.id)

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

            hashed = bcrypt.hashpw(body['password'].encode('utf8'), bcrypt.gensalt())
            trans.add_team(current_tournament.id, body['team_name'], hashed)
            has_contact_info = False
            for (i, (em, nm)) in enumerate([('email%d' % i, 'name%d' % i) for i in range(1,4)]):
                if body[em] and body[nm]:
                    if "@" not in body[em]:
                        raise cherrypy.HTTPError(400, "Malformed email address")
                    trans.add_team_member(current_tournament.id, body['team_name'], body[em], body[nm])
                    has_contact_info = True
                elif body[em] or body[nm]:
                    raise cherrypy.HTTPError(400, "Must fill out both name %d and email address %d or neither of them!" % (i,))
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
        competition = trans.get_competition(game.competition_id)
        game_dict = game.to_dict()
        sanitize_game_state(game_dict['game_state'])
        try:
            try:
                ip = cherrypy.request.headers['X-Real-IP']
            except KeyError:
                ip = cherrypy.request.remote.ip
            trans.update_ip_for_team(team.id, ip)
        except Exception:
            traceback.print_exc()
        return {
            'ret': 'ok',
            'game': game_dict,
            'competition_seconds_remaining': seconds_remaining_in_competition(competition),
            }

    @cherrypy.expose
    @require_team_auth()
    def get_compete_game(self, team, body):
        # check if everyone is connected and ready to go. if not, return "wait"
        trans = cherrypy.request.trans

        current_tournament = trans.get_current_tournament()

        # even if everyone is connected, we will need to wait until the next competition is started first
        competition_index = current_tournament.next_competition_index
        competition = trans.get_competition_by_index(current_tournament.id, competition_index)

        if (competition and
            trans.competition_has_started(competition.id) and
            team.is_whitelisted_next_round):
            # even if everyone is connected, we will need to wait until the next competition is started first
            game = trans.get_compete_game(team, competition)
            assert game is not None, "Game should not be None here: %r %r" % (team, competition)
            game_dict = game.to_dict()
            sanitize_game_state(game_dict['game_state'])
            return {
                'ret': 'ok',
                'game': game_dict,
                'competition_seconds_remaining': seconds_remaining_in_competition(competition),
                }

        print 'updating is_connected with time %s' % time.time()
        trans.update_is_connected_team_by_id(team.id, int(time.time()))
        return { 'ret': 'wait' }

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

        competition = trans.get_competition(game.competition_id)
        game_started_at = int(competition.ts - time.time())

        game_state = game.game_state

        made_move = False
        if game_state.state != 'failed':
            if seconds_remaining_in_competition(competition) <= 0:
                # game is over
                game_state.state = 'failed'
            else:
                # this mutates the in-memory version
                # of game.game_state
                game_state.send_commands(move_list)
                made_move = True

        trans.update_game(game_id,
                          moves_made + int(bool(made_move)),
                          game_state,
                          game_state.score,
                          game_state.state == 'failed')

        if game_state.state == 'failed':
            game_state_dict = game_state.to_dict()
            sanitize_game_state(game_state_dict)
            return {'ret': 'fail',
                    'code': messaging.CODE_GAME_OVER,
                    'reason': "Game Is over!",
                    'game_state': game_state_dict}

        assert game_state.state == 'playing'
        game_to_ret = game.to_dict()
        sanitize_game_state(game_to_ret['game_state'])
        return {
            'ret': 'ok',
            'game': game_to_ret,
            'competition_seconds_remaining':  seconds_remaining_in_competition(competition),
            }
    
def jsonify_error(status, message, traceback, version):
    response = cherrypy.response
    response.headers['Content-Type'] = 'application/json'
    return json.dumps({'status': status, 'message': message})

def main(argv):
    db_model = model.Database()

    if len(argv) > 1:
        # read info from a config file
        with open(argv[1]) as f:
            global_config = json.load(f)
            global_config = {k: (str(v) if type(v) is unicode else v)
                             for (k, v) in global_config.iteritems()}
    else:
        global_config = {
            'server.socket_host': '127.0.0.1',
            'server.socket_port': 8080,
            }

    config = {
        'global': global_config,
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
