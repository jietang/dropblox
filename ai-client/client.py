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

import traceback
import threading
import platform
import time
import json
import sys
import os

from ws4py.client.threadedclient import WebSocketClient
from subprocess import Popen, PIPE

from logic.Board import Board
import util
import messaging

# Remote server to connect to:
SERVER_URL = 'https://playdropblox.com/'
WEBSOCKET_URL = 'wss://playdropblox.com/ws'

# Subprocess
LEFT_CMD = 'left'
RIGHT_CMD = 'right'
UP_CMD = 'up'
DOWN_CMD = 'down'
ROTATE_CMD = 'rotate'
VALID_CMDS = [LEFT_CMD, RIGHT_CMD, UP_CMD, DOWN_CMD, ROTATE_CMD]
AI_PROCESS_PATH = os.path.join(os.getcwd(), 'dropblox_ai')

# Messaging protocol
CREATE_NEW_GAME_MSG = 'CREATE_NEW_GAME'
NEW_GAME_CREATED_MSG = 'NEW_GAME_CREATED'
AWAITING_NEXT_MOVE_MSG = 'AWAITING_NEXT_MOVE'
SUBMIT_MOVE_MSG = 'SUBMIT_MOVE'
GAME_OVER_MSG = 'GAME_OVER'
DO_NOT_RECONNECT = 1001

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
                    print line # Forward debug output to terminal
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
        if entry_mode == 'local':
            ws = LocalSubscriber(WEBSOCKET_URL)
        else:
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
        except Exception:
            print traceback.format_exc()
    return wrapped

class BaseSubscriber(object):
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
            print "Game over! Your score was: %s" % msg['final_score']
            self.close(code=DO_NOT_RECONNECT, reason="Game over!")
        else:
            print colorred.format("Received unsupported message type")

class LocalServer(object):
    def __init__(self):
        self.game = Board(0)
        self.game.game_started_at = time.time()
        self.game.game_id = 0
        self.game.total_steps = 0

    def request_next_move(self):
        seconds_remaining = util.AI_CLIENT_TIMEOUT - (time.time() - self.game.game_started_at)
        seconds_remaining -= 1 # Tell the client it has one second less than it actually has to account for latency.
        response = {
            'type': messaging.AWAITING_NEXT_MOVE_MSG,
            'game_state': self.game.to_dict(),
            'seconds_remaining': seconds_remaining,
            }
        self.game.total_steps += 1
        return response

    def received_message(self, msg):
        msg = json.loads(str(msg))

        def send_game_over():
            return {
                'type': messaging.GAME_OVER_MSG,
                'game_state': self.game.to_dict(),
                'final_score': self.game.score,
                }

        if self.game.state == 'failed':
            return send_game_over()

        if time.time() - self.game.game_started_at > util.AI_CLIENT_TIMEOUT:
			self.game.state = 'failed'
        else:
			self.game.send_commands(msg['move_list'])

        if self.game.state == 'failed':
            print "RESULTS:", self.game.score
            print "RESULTS_TIME:", self.game.total_steps
            return send_game_over()
        elif self.game.state == 'playing':
            return self.request_next_move()

class LocalSubscriber(BaseSubscriber):
    def __init__(self, *n, **kw):
        self.local_server = LocalServer()
        self.logger = GameStateLogger(0)

    def send_msg(self, msg):
        self.last_message = msg

    def close(self, code, reason):
        print "Code: %s Reason: %s" % (code, reason)
        sys.stdout.flush()
        os._exit(0)

    def connect(self):
        result = self.local_server.request_next_move()
        while result:
            self.received_message(json.dumps(result))
            result = self.local_server.received_message(json.dumps(self.last_message))

class Subscriber(WebSocketClient, BaseSubscriber):
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

    def closed(self, code, reason=None):
        print colorred.format("Connection to server closed. Code=%s, Reason=%s" % (code, reason))

        if code != DO_NOT_RECONNECT and entry_mode == 'compete':
            # Attempt to re-connect
            ws = Subscriber(WEBSOCKET_URL)
            ws.connect()
        else:
            os._exit(0)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print colorred.format("Usage: client.py [compete|practice|local]")
        sys.exit(0)

    entry_mode = sys.argv[1]
    if entry_mode not in ('compete', 'practice', 'local'):
        print colorred.format("Usage: client.py [compete|practice|local]")
        sys.exit(0)

    if entry_mode in ('compete', 'practice'):
        with open('config.txt', 'r') as f:
            team_name = f.readline().rstrip('\n')
            team_password = f.readline().rstrip('\n')
        if team_name == "TEAM_NAME_HERE" or team_password == "TEAM_PASSWORD_HERE":
            print colorred.format("Please specify a team name and password in config.txt")
            sys.exit(0)

    subscriber = SubscriberThread()
    subscriber.daemon = True
    subscriber.start()

    while (True):
        # For some reason, KeyboardInterrupts are only allowed
        # when the websocket subscriber is on a background thread.
        time.sleep(1)
