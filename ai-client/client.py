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

# Messaging protocol
CREATE_NEW_GAME_MSG = 'CREATE_NEW_GAME'
NEW_GAME_CREATED_MSG = 'NEW_GAME_CREATED'

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
        else:
            print "Received unsupported message type"

        ai_process = Popen(['grep', 'f'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
        grep_stdout = ai_process.communicate(input='one\ntwo\nthree\nfour\nfive\nsix\n')[0]
        print(grep_stdout)

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