#!/usr/bin/env python
#
# A competition is modeled as a collection of teams.
# All games within a competition are seeded with the
# same seed.
#

from logic.Board import Board

import messaging
import random
import model
import util
import json

# TODO MOVE THIS
AI_CLIENT_TIMEOUT = 11 # Allow 1 second extra for latency

class Competition(object):

	team_to_game = {}
	team_whitelist = ['myteam']
	common_seed = None

	#add_team() -- called from admin page
	#remove_team() -- called from admin page
	#start_competition() -- called from admin page

	#def start_competition(self):
	#	for team in TEAM_TO_GAME:


	# Called when a team connects via client.py
	def register_team(self, team, sock):
		if not team in self.team_whitelist:
			sock.close(code=messaging.DO_NOT_RECONNECT, reason="This team is not registered for the competition.")

		# All games in a given competition will use the same seed.
		if not self.common_seed:
			self.common_seed = random.randint(1, 1 << 30)

		if not team in self.team_to_game:
			game = Board(seed=self.common_seed)
			game.game_id = util.generate_game_id()
			self.team_to_game[team] = game

		response = {
			'type' : messaging.NEW_GAME_CREATED_MSG,
		}
		sock.send(json.dumps(response))

	@staticmethod
	def request_next_move(game, sock):
		response = {
			'type': messaging.AWAITING_NEXT_MOVE_MSG,
			'game_state': game.to_dict(),
		}
		sock.send(json.dumps(response))
		game.move_requested_at = time.time()

	def start_competition(self):
		pass

	def make_move(self, team, sock, commands):
		if not team in self.team_to_game:
			sock.close(code=messaging.DO_NOT_RECONNECT, reason="This team is not active.")

		game = self.team_to_game[team]
		if time.time() - game.move_requested_at > AI_CLIENT_TIMEOUT:
			commands = ['drop']
		game.send_commands(commands)

		if game.state == 'playing':
			Competition.request_next_move(game, sock)

	
	def unregister_team(self, sock):
		# call this in close
		pass