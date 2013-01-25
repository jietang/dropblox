#!/usr/bin/env python
#
# Provides persistence to sqlite3

import sqlite3
import bcrypt

class Database(object):

	# Tuple indices for team objects
	TEAM_TEAM_NAME = 1
	TEAM_PASSWORD = 2

	# Tuple indices for score objects
	SCORE_TEAM_NAME = 0
	SCORE_GAME_ID = 1
	SCORE_SEED = 2
	SCORE_SCORE = 3
	SCORE_ROUND = 4

	@staticmethod
	def add_team(team_name, password):
		conn = sqlite3.connect('data.db')
		sql = 'INSERT INTO teams (team_name, password) VALUES("%s", "%s");' % (team_name, password)
		conn.execute(sql)
		conn.commit()

	@staticmethod
	def add_score(team_name, game_id, seed, score, round_num):
		conn = sqlite3.connect('data.db')
		sql = 'INSERT INTO scores (team_name, game_id, seed, score, round) VALUES("%s", "%s", %s, %s, %s);' % (team_name, game_id, seed, score, round_num)
		conn.execute(sql)
		conn.commit()

	@staticmethod
	def get_team(team_name):
		conn = sqlite3.connect('data.db')
		sql = 'SELECT * FROM teams WHERE team_name="%s"' % team_name
		return conn.execute(sql).fetchone()

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
			sql = 'CREATE TABLE IF NOT EXISTS teams (team_id INTEGER PRIMARY KEY NOT NULL, team_name VARCHAR(64), password CHAR(64));'
			conn.execute(sql)
			conn.commit()
			print "here"

		def create_score_table():
			sql = 'CREATE TABLE IF NOT EXISTS scores (team_name VARCHAR(64), game_id VARCHAR(64), seed INTEGER, score INTEGER, round INTEGER);'
			conn.execute(sql)
			conn.commit()        	

		create_team_table()
		create_score_table()