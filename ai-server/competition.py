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
		self.started = False
		self.team_to_game = {}
		self.sock_to_team = {}
		self.team_whitelist = set()
		self.common_seed = None
		self.is_test_run = is_test_run
		if not self.is_test_run:
			self.round = model.Database.latest_round() + 1

	def whitelist_team(self, team):
		if self.started:
			return
		self.team_whitelist.add(team)

	def blacklist_team(self, team):
		if self.started:
			return
		if self.is_team_connected(team):
			del self.team_to_game[team]
			for sock, t in self.sock_to_team.items():
				if t == team:
					sock.close(code=messaging.DO_NOT_RECONNECT, reason="You have been blacklisted by the competition organizer.")
					del self.sock_to_team[sock]
		self.team_whitelist.discard(team)

        def is_team_whitelisted(self, team):
                return team in self.team_whitelist

	# Called when a team connects via client.py
	def register_team(self, team, sock):
		if not team in self.team_whitelist:
			sock.close(code=messaging.DO_NOT_RECONNECT, reason="This team is not registered for the competition.")
			return

		if team in self.sock_to_team.values():
			sock.close(code=messaging.DO_NOT_RECONNECT, reason="This team already has a connection to the game server.")
			return
		self.sock_to_team[sock] = team

		# All games in a given competition will use the same seed.
		if not self.common_seed:
			self.common_seed = random.randint(1, 1 << 30)

		if not team in self.team_to_game:
			game = Board(seed=self.common_seed)
			game.game_id = util.generate_game_id()
			self.team_to_game[team] = game
		elif self.started:
			# We must be resuming a broken connection.
			Competition.request_next_move(self.team_to_game[team], sock)
			return

		# Game IDs are visible to the client only in testing.
		if self.is_test_run:
			Competition.notify_game_created(sock, game.game_id)
		else:
			Competition.notify_game_created(sock)

	def is_team_connected(self, team):
		return team in self.sock_to_team.values()
		
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
		seconds_remaining = util.AI_CLIENT_TIMEOUT - (time.time() - game.game_started_at)
		seconds_remaining -= 1 # Tell the client it has one second less than it actually has to account for latency.
		response = {
			'type': messaging.AWAITING_NEXT_MOVE_MSG,
			'game_state': game.to_dict(),
			'seconds_remaining': seconds_remaining,
		}
		sock.send(json.dumps(response))

	@staticmethod
	def send_game_over(game, sock):
		response = {
			'type': messaging.GAME_OVER_MSG,
			'game_state': game.to_dict(),
			'final_score': game.score,
		}
		sock.send(json.dumps(response))

	def record_game(self, team, game):
		if self.is_test_run:
			model.Database.add_practice_score(team, game.game_id, game.seed, game.score)
		else:
			model.Database.add_score(team, game.game_id, game.seed, game.score, self.round)

	def start_competition(self):
		self.started = True
		for sock in self.sock_to_team:
			game = self.team_to_game[self.sock_to_team[sock]]
			game.game_started_at = time.time()
			Competition.request_next_move(game, sock)

	def check_competition_over(self):
		if self.is_test_run:
			return False
		for game in self.team_to_game.values():
			if game.state == 'playing':
				return False
		return True

	def make_move(self, team, sock, commands):
		if not team in self.team_to_game:
			sock.close(code=messaging.DO_NOT_RECONNECT, reason="This team is not active.")
			return

		game = self.team_to_game[team]
		if game.state == 'failed':
			Competition.send_game_over(game, sock)
			return

		if time.time() - game.game_started_at > util.AI_CLIENT_TIMEOUT:
			game.state = 'failed'
		else:
			game.send_commands(commands)

		if game.state == 'failed':
			self.record_game(team, game)
			Competition.send_game_over(game, sock)
		elif game.state == 'playing':
			Competition.request_next_move(game, sock)

	# Called when the competition is forcibly ended.
	def record_remaining_games(self):
		if not self.is_test_run:
			for (team, game) in self.team_to_game.iteritems():
				if game.state == 'playing':
					game.state = 'failed'
					self.record_game(team, game)

	# Called when a socket is closed.
	def disconnect_sock(self, sock):
		if sock in self.sock_to_team:
			del self.sock_to_team[sock]

