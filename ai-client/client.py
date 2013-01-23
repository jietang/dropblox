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

from ws4py.client.threadedclient import WebSocketClient
from subprocess import Popen, PIPE, STDOUT

# Remote server to connect to:
SERVER_URL = 'http://localhost:9000/'
WEBSOCKET_URL = 'ws://localhost:9000/ws'

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
NEW_GAME_CREATED_MSG = 'NEW_GAME_CREATED'
AWAITNG_NEXT_MOVE_MSG = 'AWAITNG_NEXT_MOVE'
SUBMIT_MOVE_MSG = 'SUBMIT_MOVE'

class Command(object):
    def __init__(self, cmd):
        self.cmd = cmd
        self.process = None

    def run(self, timeout):
        cmds = []
        def target():
            print 'Executing %s' % self.cmd
            self.process = Popen(self.cmd, stdout=PIPE, shell=True)
            for line in iter(self.process.stdout.readline, ''):
                line = line.rstrip('\n')
                if line not in VALID_CMDS:
                    print "Got a bad cmd from subprocess: %s" % line
                elif line != DROP_CMD:
                    cmds.append(line)

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            print 'Terminating process'
            self.process.terminate()
            thread.join()
        print 'commands received: %s' % cmds
        return cmds

class SubscriberThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self) 

    def run(self):
        ws = Subscriber(WEBSOCKET_URL)
        ws.connect()

class Subscriber(WebSocketClient):
    def handshake_ok(self):
        self._th.start()
        self._th.join()

    def opened(self):
        # TODO: Handle reconnecting to established games
        msg = {
            'type' : CREATE_NEW_GAME_MSG,
        }
        self.send(json.dumps(msg))

    def received_message(self, msg):
        print "received_message %s" % msg
        msg = json.loads(str(msg))
        if msg['type'] == NEW_GAME_CREATED_MSG:
            print "New game started at %s%s" % (SERVER_URL, msg['game_id'])
        elif msg['type'] == AWAITNG_NEXT_MOVE_MSG:
            ai_arg = json.dumps(msg['game_state'])
            command = Command(AI_PROCESS_PATH + " " + ai_arg)
            ai_cmds = command.run(timeout=AI_PROCESS_TIMEOUT)
            response = {
                'type' : SUBMIT_MOVE_MSG,
                'move_list' : ai_cmds,
            }
            self.send(json.dumps(response))
        else:
            print "Received unsupported message type"

    def closed(self, code, reason=None):
        print "Connection to server closed. Code=%s, Reason=%s" % (code, reason)

if __name__ == '__main__':
    subscriber = SubscriberThread()
    subscriber.daemon = True
    subscriber.start()

    while (True):
        # For some reason, KeyboardInterrupts are only allowed
        # when the websocket subscriber is on a background thread.
        pass