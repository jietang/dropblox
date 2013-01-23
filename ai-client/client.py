#!/usr/bin/env python
#
# This client connects to the centralized game server
# via websocket. After creating a new game on the game
# server, it spaws an AI subprocess called "ntris_ai."
# For each turn, this client passes in the current game
# state to a new instance of ntris_ai, waits ten seconds
# for a response, then kills the AI process and sends
# back the move list.
#

import threading
import cherrypy
import json
import os

from ws4py.client.threadedclient import WebSocketClient
from subprocess import Popen, PIPE, STDOUT
from optparse import OptionParser

# Remote server to connect to:
#SERVER_URL = 'http://ec2-107-20-18-153.compute-1.amazonaws.com/'
#WEBSOCKET_URL = 'ws://ec2-107-20-18-153.compute-1.amazonaws.com/ws'
SERVER_URL = 'http://localhost/'
WEBSOCKET_URL = 'ws://localhost/ws'

# Subprocess
LEFT_CMD = 'left'
RIGHT_CMD = 'right'
UP_CMD = 'up'
DOWN_CMD = 'down'
DROP_CMD = 'drop'
ROTATE_CMD = 'rotate'
VALID_CMDS = [LEFT_CMD, RIGHT_CMD, UP_CMD, DOWN_CMD, DROP_CMD, ROTATE_CMD]
AI_PROCESS_PATH = './ntris_ai'
AI_PROCESS_TIMEOUT = 10 # This is enforced server-side so don't change ;)

# Messaging protocol
CREATE_NEW_GAME_MSG = 'CREATE_NEW_GAME'
CONNECT_TO_EXISTING_GAME_MSG = 'CONNECT_TO_EXISTING_GAME'
NEW_GAME_CREATED_MSG = 'NEW_GAME_CREATED'
AWAITING_NEXT_MOVE_MSG = 'AWAITING_NEXT_MOVE'
SUBMIT_MOVE_MSG = 'SUBMIT_MOVE'
DO_NOT_RECONNECT = 1001

# Printing utilities
colorred = "\033[01;31m{0}\033[00m"
colorgrn = "\033[1;36m{0}\033[00m"

class Command(object):
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None

    def run(self, timeout):
        cmds = []
        def target():
            self.process = Popen(self.cmd, stdout=PIPE, shell=True)
            for line in iter(self.process.stdout.readline, ''):
                line = line.rstrip('\n')
                if line not in VALID_CMDS:
                    print line # Forward debug output to terminal
                elif line != DROP_CMD:
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

class Subscriber(WebSocketClient):
    game_id = -1

    def handshake_ok(self):
        self._th.start()
        self._th.join()

    def opened(self):
        msg = {
            'type' : CREATE_NEW_GAME_MSG,
        }
        if team_name:
            msg['team_name'] = team_name

        if self.game_id != -1:
            # We must be reconnecting to a prior game
            msg = {
                'type' : CONNECT_TO_EXISTING_GAME_MSG,
                'game_id' : self.game_id,
            }
        self.send(json.dumps(msg))

    def received_message(self, msg):
        msg = json.loads(str(msg))
        if msg['type'] == NEW_GAME_CREATED_MSG:
            if not team_name:
                self.game_id = msg['game_id']
                print colorgrn.format("New game started at %sgame.html#%s" % (SERVER_URL, msg['game_id']))
            else:
                print colorgrn.format("Waiting for competition to begin")
        elif msg['type'] == AWAITING_NEXT_MOVE_MSG:
            ai_arg = json.dumps(msg['game_state'])
            command = Command(AI_PROCESS_PATH + (" '%s'" % ai_arg))
            ai_cmds = command.run(timeout=AI_PROCESS_TIMEOUT)
            response = {
                'type' : SUBMIT_MOVE_MSG,
                'move_list' : ai_cmds,
            }
            self.send(json.dumps(response))
        else:
            print colorred.format("Received unsupported message type")

    def closed(self, code, reason=None):
        print colorred.format("Connection to server closed. Code=%s, Reason=%s" % (code, reason))

        if code != DO_NOT_RECONNECT:
            # Attempt to re-connect
            ws = Subscriber(WEBSOCKET_URL)
            ws.game_id = self.game_id
            ws.connect()
        else:
            os._exit(0)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-c", "--compete", dest="team_name",
                      help="Enter competition with TEAM_NAME",
                      metavar="TEAM_NAME")
    (options, _) = parser.parse_args()
    team_name = options.team_name

    subscriber = SubscriberThread()
    subscriber.daemon = True
    subscriber.start()

    while (True):
        # For some reason, KeyboardInterrupts are only allowed
        # when the websocket subscriber is on a background thread.
        pass
