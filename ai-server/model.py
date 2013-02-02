#!/usr/bin/env python
#
# Provides persistence to MySQL

import MySQLdb as mdb
import bcrypt

class Database(object):

	# Tuple indices for team objects
	TEAM_TEAM_NAME = 1
	TEAM_PASSWORD = 2
	TEAM_IS_ADMIN = 3

	# Tuple indices for score objects
	SCORE_TEAM_NAME = 0
	SCORE_GAME_ID = 1
	SCORE_SEED = 2
	SCORE_SCORE = 3
	SCORE_ROUND = 4

	AUTHENTICATED_SOCKETS = {}
	AUTHENTICATED_TEAMS = {}

	@staticmethod
	def add_team(team_name, password):
		conn = mdb.connect(host='localhost', user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'INSERT INTO teams (team_name, password, is_admin) VALUES(%s, %s, %s);'
		cursor = conn.cursor()
		cursor.execute(sql, (team_name, password, 0))
		conn.commit()

	@staticmethod
	def add_score(team_name, game_id, seed, score, round_num):
		conn = mdb.connect(host='localhost', user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'INSERT INTO scores (team_name, game_id, seed, score, round) VALUES(%s, %s, %s, %s, %s);'
		cursor = conn.cursor()
		cursor.execute(sql, (team_name, game_id, seed, score, round_num))
		conn.commit()

	@staticmethod
	def latest_round():
		conn = mdb.connect(host='localhost', user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'SELECT MAX(round) FROM scores'
		cursor = conn.cursor()
		cursor.execute(sql)
		result = cursor.fetchone()[0]
		if result == None:
			result = 0
		return result

	@staticmethod
	def scores_by_team():
		conn = mdb.connect(host='localhost', user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'SELECT * FROM scores ORDER BY team_name ASC, round ASC'
		cursor = conn.cursor()
		cursor.execute(sql)
		scores = cursor.fetchall()

		team_to_scores = {}
		for score in scores:
			if score[Database.SCORE_TEAM_NAME] not in team_to_scores:
				team_to_scores[score[Database.SCORE_TEAM_NAME]] = []
			team_to_scores[score[Database.SCORE_TEAM_NAME]].append({
				'score' : score[Database.SCORE_SCORE],
				'round' : score[Database.SCORE_ROUND],
			})
		return team_to_scores

	@staticmethod
	def get_team(team_name):
		conn = mdb.connect(host='localhost', user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'SELECT * FROM teams WHERE team_name=%s'
		cursor = conn.cursor()
		cursor.execute(sql, team_name)
		return cursor.fetchone()

	@staticmethod
	def list_all_teams():
		conn = mdb.connect(host='localhost', user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'SELECT * FROM teams'
		cursor = conn.cursor()
		cursor.execute(sql)
		return cursor.fetchall()		

	@staticmethod
	def authenticate_team(team_name, password, session_sock=None):
		team = Database.get_team(team_name)
		if not team:
			return None

		if Database.AUTHENTICATED_TEAMS.get(team_name) == password:
			return team
		if session_sock and session_sock in Database.AUTHENTICATED_SOCKETS:
			if Database.AUTHENTICATED_SOCKETS[session_sock] == team[Database.TEAM_TEAM_NAME]:
				return team # This socket has already authenticated, no need to bcrypt password check again (since it is very slow)

		if not bcrypt.hashpw(password, team[Database.TEAM_PASSWORD]) == team[Database.TEAM_PASSWORD]:
			return None

		Database.AUTHENTICATED_TEAMS[team_name] = password
		if session_sock:
			Database.AUTHENTICATED_SOCKETS[session_sock] = team[Database.TEAM_TEAM_NAME]
		return team

	@staticmethod
	def report_session_ended(session_sock):
		if session_sock in Database.AUTHENTICATED_SOCKETS:
			del Database.AUTHENTICATED_SOCKETS[session_sock]

	@staticmethod
	def initialize_db():
		conn = mdb.connect(host='localhost', user='dropblox', passwd='dropblox', db='dropblox')

		def create_team_table():
			sql = 'CREATE TABLE IF NOT EXISTS teams (team_id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT, team_name VARCHAR(64), password CHAR(64), is_admin INTEGER);'
			cursor = conn.cursor()
			cursor.execute(sql)
			conn.commit()

		def create_score_table():
			sql = 'CREATE TABLE IF NOT EXISTS scores (team_name VARCHAR(64), game_id VARCHAR(64), seed INTEGER, score INTEGER, round INTEGER, PRIMARY KEY (team_name, round));'
			cursor = conn.cursor()
			cursor.execute(sql)
			conn.commit()

		def create_admin_user():
			if not Database.get_team('admin'):
				admin_pw = '$2a$12$xmaAYZoZEyqGZWfoXZfZI.ik3mjrzVcGOg3sxvnfFU/lS5n6lgqyy'
				sql = 'INSERT INTO teams (team_name, password, is_admin) VALUES(%s, %s, %s);'
				cursor = conn.cursor()
				cursor.execute(sql, ('admin', admin_pw, 1))
				conn.commit()

		create_team_table()
		create_score_table()
		create_admin_user()
