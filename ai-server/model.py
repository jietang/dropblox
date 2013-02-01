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

	CONN = None

	@staticmethod
	def add_team(team_name, password):
		sql = 'INSERT INTO teams (team_name, password, is_admin) VALUES(%s, %s, %s);'
		cursor = CONN.cursor()
		cursor.execute(sql, (team_name, password, 0))
		CONN.commit()

	@staticmethod
	def add_score(team_name, game_id, seed, score, round_num):
		sql = 'INSERT INTO scores (team_name, game_id, seed, score, round) VALUES(%s, %s, %s, %s, %s);'
		cursor = CONN.cursor()
		cursor.execute(sql, (team_name, game_id, seed, score, round_num))
		CONN.commit()

	@staticmethod
	def latest_round():
		sql = 'SELECT MAX(round) FROM scores'
		cursor = CONN.cursor()
		cursor.execute(sql)
		result = cursor.fetchone()[0]
		if result == None:
			result = 0
		return result

	@staticmethod
	def scores_by_team(team_name):
		sql = 'SELECT * FROM scores WHERE team_name=%s ORDER BY round ASC'
		cursor = CONN.cursor()
		cursor.execute(sql, team_name)
		scores = cursor.fetchall()

		result = []
		for score in scores:
			result.append({
				'score' : score[Database.SCORE_SCORE],
				'round' : score[Database.SCORE_ROUND],
			})
		return result

	@staticmethod
	def get_team(team_name):
		sql = 'SELECT * FROM teams WHERE team_name=%s'
		cursor = CONN.cursor()
		cursor.execute(sql, team_name)
		return cursor.fetchone()

	@staticmethod
	def list_all_teams():
		sql = 'SELECT * FROM teams'
		cursor = CONN.cursor()
		cursor.execute(sql)
		return cursor.fetchall()		

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
		global CONN
		CONN = mdb.connect(host='localhost', user='dropblox', passwd='dropblox', db='dropblox')

		def create_team_table():
			sql = 'CREATE TABLE IF NOT EXISTS teams (team_id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT, team_name VARCHAR(64), password CHAR(64), is_admin INTEGER);'
			cursor = CONN.cursor()
			cursor.execute(sql)
			CONN.commit()

		def create_score_table():
			sql = 'CREATE TABLE IF NOT EXISTS scores (team_name VARCHAR(64), game_id VARCHAR(64), seed INTEGER, score INTEGER, round INTEGER, PRIMARY KEY (team_name, round));'
			cursor = CONN.cursor()
			cursor.execute(sql)
			CONN.commit()

		def create_admin_user():
			if not Database.get_team('admin'):
				admin_pw = '$2a$12$xmaAYZoZEyqGZWfoXZfZI.ik3mjrzVcGOg3sxvnfFU/lS5n6lgqyy'
				sql = 'INSERT INTO teams (team_name, password, is_admin) VALUES(%s, %s, %s);'
				cursor = CONN.cursor()
				cursor.execute(sql, ('admin', admin_pw, 1))
				CONN.commit()

		create_team_table()
		create_score_table()
		create_admin_user()