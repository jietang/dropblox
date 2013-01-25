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
import time

class Competition(object):

	def __init__(self, is_test_run=False):
		self.team_to_game = {}
		self.sock_to_team = {}
		self.team_whitelist = set(['myteam'])
		self.common_seed = None
		self.is_test_run = is_test_run
		if not self.is_test_run:
			self.round = model.Database.latest_round() + 1

	def whitelist_team(self, team):
		self.team_whitelist.add(team)

	def blacklist_team(self, team):
		self.team_whitelist.remove(team)

	# Called when a team connects via client.py
	def register_team(self, team, sock):
		if not team in self.team_whitelist:
			sock.close(code=messaging.DO_NOT_RECONNECT, reason="This team is not registered for the competition.")

		if team in self.sock_to_team.values():
			sock.close(code=messaging.DO_NOT_RECONNECT, reason="This team already has a connection to the game server.")
		self.sock_to_team[sock] = team

		# All games in a given competition will use the same seed.
		if not self.common_seed:
			self.common_seed = random.randint(1, 1 << 30)

		if not team in self.team_to_game:
			game = Board(seed=self.common_seed)
			game.game_id = util.generate_game_id()
			self.team_to_game[team] = game

			# Game IDs are visible to the client only in testing.
			if self.is_test_run:
				Competition.notify_game_created(sock, game.game_id)
			else:
				Competition.notify_game_created(sock)
		else:
			# We must be resuming a broken connection.
			Competition.request_next_move(self.team_to_game[team], sock)
		
	@staticmethod
	def notify_game_created(sock, game_id=None):
		response = {
			'type' : messaging.NEW_GAME_CREATED_MSG,
		}
		if game_id:
			response['game_id'] = game_id
		sock.send(json.dumps(response))

	@staticmethod
	def request_next_move(game, sock):
		response = {
			'type': messaging.AWAITING_NEXT_MOVE_MSG,
			'game_state': game.to_dict(),
		}
		sock.send(json.dumps(response))
		game.move_requested_at = time.time()

	@staticmethod
	def send_game_over(game, sock):
		sock.close(code=messaging.DO_NOT_RECONNECT, reason="Game over! Your score was: %s" % game.score)

	@staticmethod
	def record_game(team, game):
		if not self.is_test_run:
			model.Database.add_score(team, game.game_id, game.seed, game.score, self.round)

	def start_competition(self):
		for sock in self.sock_to_team:
			Competition.request_next_move(self.team_to_game[self.sock_to_team[sock]], sock)

	def make_move(self, team, sock, commands):
		if not team in self.team_to_game:
			sock.close(code=messaging.DO_NOT_RECONNECT, reason="This team is not active.")

		game = self.team_to_game[team]
		if time.time() - game.move_requested_at > util.AI_CLIENT_TIMEOUT:
			commands = ['drop']
		game.send_commands(commands)

		if game.state == 'failed':
			Competition.record_game(team, game)
			Competition.send_game_over(game, sock)
		elif game.state == 'playing':
			Competition.request_next_move(game, sock)

	# Called when a socket is closed.
	def disconnect_sock(self, sock):
		if sock in self.sock_to_team:
			del self.sock_to_team[sock]
		