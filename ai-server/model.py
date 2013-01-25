#!/usr/bin/env python
#
# Provides persistence to sqlite3

import sqlite3
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

	@staticmethod
	def add_team(team_name, password):
		conn = sqlite3.connect('data.db')
		sql = 'INSERT INTO teams (team_name, password, is_admin) VALUES("%s", "%s", %s);' % (team_name, password, 0)
		conn.execute(sql)
		conn.commit()

	@staticmethod
	def add_score(team_name, game_id, seed, score, round_num):
		conn = sqlite3.connect('data.db')
		sql = 'INSERT INTO scores (team_name, game_id, seed, score, round) VALUES("%s", "%s", %s, %s, %s);' % (team_name, game_id, seed, score, round_num)
		conn.execute(sql)
		conn.commit()

	@staticmethod
	def latest_round():
		conn = sqlite3.connect('data.db')
		sql = 'SELECT MAX(round) FROM scores'
		result = conn.execute(sql).fetchone()[0]
		if result == None:
			result = 0
		return result

	@staticmethod
	def scores_by_team(team_name):
		conn = sqlite3.connect('data.db')
		sql = 'SELECT * FROM scores WHERE team_name="%s" ORDER BY round ASC' % team_name
		scores = conn.execute(sql).fetchall()

		result = []
		for score in scores:
			result.append({
				'score' : score[Database.SCORE_SCORE],
				'round' : score[Database.SCORE_ROUND],
			})
		return result

	@staticmethod
	def get_team(team_name):
		conn = sqlite3.connect('data.db')
		sql = 'SELECT * FROM teams WHERE team_name="%s"' % team_name
		return conn.execute(sql).fetchone()

	@staticmethod
	def list_all_teams():
		conn = sqlite3.connect('data.db')
		sql = 'SELECT * FROM teams'
		return conn.execute(sql).fetchall()		

	@staticmethod
	def authenticate_team(team_name, password):
		team = Database.get_team(team_name)
		if not team:
			return None

		if not bcrypt.hashpw(password, team[Database.TEAM_PASSWORD]) == team[Database.TEAM_PASSWORD]:
			return None

		return team

	@staticmethod
	def initialize_db():
		conn = sqlite3.connect('data.db')

		def create_team_table():
			sql = 'CREATE TABLE IF NOT EXISTS teams (team_id INTEGER PRIMARY KEY NOT NULL, team_name VARCHAR(64), password CHAR(64), is_admin INTEGER);'
			conn.execute(sql)
			conn.commit()

		def create_score_table():
			sql = 'CREATE TABLE IF NOT EXISTS scores (team_name VARCHAR(64), game_id VARCHAR(64), seed INTEGER, score INTEGER, round INTEGER, PRIMARY KEY (team_name, round));'
			conn.execute(sql)
			conn.commit()

		def create_admin_user():
			if not Database.get_team('admin'):
				conn = sqlite3.connect('data.db')
				admin_pw = '$2a$12$xmaAYZoZEyqGZWfoXZfZI.ik3mjrzVcGOg3sxvnfFU/lS5n6lgqyy'
				sql = 'INSERT INTO teams (team_name, password, is_admin) VALUES("%s", "%s", %s);' % ('admin', admin_pw, 1)
				conn.execute(sql)
				conn.commit()

		create_team_table()
		create_score_table()
		create_admin_user()