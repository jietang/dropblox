#!/usr/bin/env python
#
# This client connects to the centralized game server
# via websocket. After creating a new game on the game
# server, it spaws an AI subprocess called "dropblox_ai."
# For each turn, this client passes in the current game
# state to a new instance of dropblox_ai, waits ten seconds
# for a response, then kills the AI process and sends
# back the move list.
#

import contextlib
import hashlib
import os
import platform
import sys
import threading
import time
import traceback
import urllib2

import cherrypy
import json

from ws4py.client.threadedclient import WebSocketClient
from subprocess import Popen, PIPE, STDOUT

import messaging

class GameOverError(Exception):
    def __init__(self, game_state_dict):
        self.game_state_dict = game_state_dict

# Remote server to connect to:
PROD_HOST = 'playdropblox.com'
PROD_PORT = 443
PROD_SSL = True

SERVER_URL = 'https://playdropblox.com/'
WEBSOCKET_URL = 'wss://playdropblox.com/ws'
#SERVER_URL = 'https://ec2-23-20-109-136.compute-1.amazonaws.com/'
#WEBSOCKET_URL = 'wss://ec2-23-20-109-136.compute-1.amazonaws.com/ws'


# Subprocess
LEFT_CMD = 'left'
RIGHT_CMD = 'right'
UP_CMD = 'up'
DOWN_CMD = 'down'
ROTATE_CMD = 'rotate'
VALID_CMDS = [LEFT_CMD, RIGHT_CMD, UP_CMD, DOWN_CMD, ROTATE_CMD]
AI_PROCESS_PATH = os.path.join(os.getcwd(), 'dropblox_ai')

# Printing utilities
colorred = "\033[01;31m{0}\033[00m"
colorgrn = "\033[1;36m{0}\033[00m"

# Logging AI actions for debug webserver
LOGGING_DIR = os.path.join(os.getcwd(), 'history')

class Command(object):
    def __init__(self, cmd, *args):
        self.cmd = cmd
        self.args = list(args)
        self.process = None

    def run(self, timeout):
        cmds = []
        def target():
            is_windows = platform.system() == "Windows"
            self.process = Popen([self.cmd] + self.args, stdout=PIPE, universal_newlines=True, shell=is_windows)
            for line in iter(self.process.stdout.readline, ''):
                line = line.rstrip('\n')
                if line not in VALID_CMDS:
                    print 'INVALID COMMAND:', line # Forward debug output to terminal
                else:
                    cmds.append(line)

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            print colorred.format('Terminating process')
            self.process.terminate()
            thread.join()
        print colorgrn.format('commands received: %s' % cmds)
        return cmds

class SubscriberThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        ws = Subscriber(WEBSOCKET_URL)
        ws.connect()

class GameStateLogger(object):
    log_dir = None
    turn_num = 0

    def __init__(self, game_id):
        self.log_dir = os.path.join(LOGGING_DIR, '%s_%s' % (game_id, int(time.time())))
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def log_game_state(self, game_state):
        fname = os.path.join(self.log_dir, 'state%s' % (self.turn_num,))
        with open(fname, 'w+') as f:
            f.write(game_state)

    def log_ai_move(self, move_list):
        fname = os.path.join(self.log_dir, 'move%s' % (self.turn_num,))
        with open(fname, 'w+') as f:
            f.write(move_list)
        self.turn_num += 1

def catch_exceptions(f):
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception, e:
            print traceback.format_exc()
    return wrapped

class Subscriber(WebSocketClient):
    game_id = -1
    logger = None

    @catch_exceptions
    def handshake_ok(self):
        self._th.start()
        self._th.join()

    @catch_exceptions
    def send_msg(self, msg):
        msg['team_name'] = team_name
        msg['team_password'] = team_password
        msg['entry_mode'] = entry_mode
        self.send(json.dumps(msg))

    @catch_exceptions
    def opened(self):
        msg = {
            'type' : CREATE_NEW_GAME_MSG,
        }
        self.send_msg(msg)

    @catch_exceptions
    def received_message(self, msg):
        msg = json.loads(str(msg))
        if msg['type'] == NEW_GAME_CREATED_MSG:
            if 'game_id' in msg:
                self.game_id = msg['game_id']
                self.logger = GameStateLogger(self.game_id)
                print colorgrn.format("New game started. Watch at %s#submission_history" % (SERVER_URL,))
            else:
                print colorgrn.format("Waiting for competition to begin")
        elif msg['type'] == AWAITING_NEXT_MOVE_MSG:
            ai_arg_one = json.dumps(msg['game_state'])
            ai_arg_two = json.dumps(msg['seconds_remaining'])
            if self.logger:
                self.logger.log_game_state(ai_arg_one)
            command = Command(AI_PROCESS_PATH, ai_arg_one, ai_arg_two)
            ai_cmds = command.run(timeout=float(ai_arg_two))
            if self.logger:
                self.logger.log_ai_move(json.dumps(ai_cmds))
            response = {
                'type' : SUBMIT_MOVE_MSG,
                'move_list' : ai_cmds,
            }
            self.send_msg(response)
        elif msg['type'] == GAME_OVER_MSG:
            ai_arg = json.dumps(msg['game_state'])
            if self.logger:
                self.logger.log_game_state(ai_arg)
            print colorgrn.format("Game over! Your score was: %s" % msg['final_score'])
            self.close(code=DO_NOT_RECONNECT, reason="Game over!")
        else:
            print colorred.format("Received unsupported message type")

    def closed(self, code, reason=None):
        print colorred.format("Connection to server closed. Code=%s, Reason=%s" % (code, reason))

        if code != DO_NOT_RECONNECT and entry_mode == 'compete':
            # Attempt to re-connect
            ws = Subscriber(WEBSOCKET_URL)
            ws.connect()
        else:
            os._exit(0)

class DropbloxServer(object):
    def __init__(self, team_name, team_password, host, port, ssl):
        # maybe support any transport
        # but whatever
        self.host = host
        self.port = port
        self.ssl = ssl

        self.team_name = team_name
        self.team_password = team_password
        
    def _request(self, path, tbd):
        schema = 'https' if self.ssl else 'http'
        url = '%s://%s:%d%s' % (schema, self.host, self.port, path)
        
        tbd = dict(tbd)
        tbd['team_name'] = self.team_name
        tbd['password'] = self.team_password
        data = json.dumps(tbd)

        req = urllib2.Request(url, data, {
                'Content-Type': 'application/json'
                })

        with contextlib.closing(urllib2.urlopen(req)) as resp:
            if resp.getcode() != 200:
                raise Exception("Bad response: %r" % resp.getcode())
            return json.loads(resp.read())

    def create_practice_game(self):
        return self._request("/create_practice_game", {})

    def get_compete_game(self):
        # return None if game is not ready to go yet
        resp = self._request("/get_compete_game", {})
        return None if resp['ret'] == 'wait' else resp # w00t, magic string

    def submit_game_move(self, game_id, move_list, moves_made):
        resp = self._request("/submit_game_move", {
                'game_id': game_id,
                'move_list': move_list,
                'moves_made': moves_made,
                })
        if resp['ret'] == 'ok':
            return resp

        if resp['ret'] == 'fail':
            if resp['code'] == messaging.CODE_GAME_OVER:
                raise GameOverError(resp['game_state'])
            else:
                raise Exception("Bad move: %r:%r",
                                resp['code'], resp['reason'])
        
        raise Exception("Bad response: %r" % (resp,))

def run_ai(game_state_dict, seconds_remaining, logger=None):
    ai_arg_one = json.dumps(game_state_dict)
    ai_arg_two = json.dumps(seconds_remaining)
    if logger is not None:
        logger.log_game_state(ai_arg_one)
    command = Command(AI_PROCESS_PATH, ai_arg_one, ai_arg_two)
    ai_cmds = command.run(timeout=float(ai_arg_two))
    if logger is not None:
        logger.log_ai_move(json.dumps(ai_cmds))
    return ai_cmds

def run_game(server, game):
    game_id = game['game']['id']
    moves_made = 0

    logger = GameStateLogger(game_id)

    while True:
        ai_cmds = run_ai(game['game']['game_state'],
                         game['competition_seconds_remaining'],
                         logger=logger)

        try:
            game = server.submit_game_move(game_id, ai_cmds, moves_made)
        except GameOverError, e:
            final_game_state_dict = e.game_state_dict
            break
        moves_made += 1

    logger.log_game_state(json.dumps(final_game_state_dict))

    print colorgrn.format("Game over! Your score was: %s" %
                          (final_game_state_dict['score'],))

def run_compete(server):
    # TODO: it might be better for this to be an actual game object
    #       instead of the dictionary serialization of it
    new_game = server.get_compete_game()
    while not new_game:
        time.sleep(0.5)
        new_game = server.get_compete_game()
    run_game(server, new_game)

def run_practice(server):
    # TODO: it might be better for this to be an actual game object
    #       instead of the dictionary serialization of it
    new_game = server.create_practice_game()
    run_game(server, new_game)

def main(argv):
    with open('config.txt', 'r') as f:
        team_name = f.readline().rstrip('\n')
        team_password = f.readline().rstrip('\n')

    if team_name == "TEAM_NAME_HERE" or team_password == "TEAM_PASSWORD_HERE":
        print colorred.format("Please specify a team name and password in config.txt")
        sys.exit(0)

    if (len(sys.argv) != 2 or
        sys.argv[1] not in ["compete", "practice"]):
        print colorred.format("Usage: client.py [compete|practice]")
        sys.exit(0)

    entry_mode = sys.argv[1]

    if (hashlib.md5(os.environ.get('DROPBLOX_DEBUG')).digest() ==
        '\x98w\x01\x0b%O\x08\xfa\x07\xe8\xa3\xe6]\xe9\xf0\xeb'):
        connect_details = ('localhost', 8080, False)
    else:
        connect_details = (PROD_HOST, PROD_PORT, PROD_SSL)

    server = DropbloxServer(team_name, team_password, *connect_details)

    if entry_mode == "practice":
        run_practice(server)
        return 0
    elif entry_mode == "compete":
        run_compete(server)
        return 0
    else:
        print 'wtf? mode = %s' % entry_mode
        return 0

    # subscriber = SubscriberThread()
    # subscriber.daemon = True
    # subscriber.start()

    while (True):
        # For some reason, KeyboardInterrupts are only allowed
        # when the websocket subscriber is on a background thread.
        time.sleep(1)
    
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
