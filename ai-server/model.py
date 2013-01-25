#!/usr/bin/env python
#
# Provides persistence to sqlite3

import sqlite3

conn = None

class Database(object):

	@staticmethod
	def add_user(team_name, password):
		sql = 'INSERT INTO users (team_name, password) VALUES("%s", "%s");' % (team_name, password)
		conn.execute(sql)
		conn.commit()

	@staticmethod
	def add_score(team_name, game_id, seed, score, round_num):
		sql = 'INSERT INTO scores (team_name, game_id, seed, score, round) VALUES("%s", "%s", "%s", "%s", "%s");' % (team_name, game_id, seed, score, round_num)
		conn.execute(sql)
		conn.commit()

	@staticmethod
	def initialize_db():
		global conn
		conn = sqlite3.connect('data.db')

		def create_user_table():
			sql = 'CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY NOT NULL, team_name VARCHAR(64), password CHAR(64));'
			conn.execute(sql)
			conn.commit()
			print "here"

		def create_score_table():
			sql = 'CREATE TABLE IF NOT EXISTS scores (team_name VARCHAR(64), game_id VARCHAR(64), seed INTEGER, score INTEGER, round INTEGER);'
			conn.execute(sql)
			conn.commit()        	

		create_user_table()
		create_score_table()