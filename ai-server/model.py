#!/usr/bin/env python
#
# Provides persistence to MySQL

import contextlib
import threading

import MySQLdb as mdb
import bcrypt

DB_HOST = '10.35.9.6'
ADMIN_PW = '$2a$12$xmaAYZoZEyqGZWfoXZfZI.ik3mjrzVcGOg3sxvnfFU/lS5n6lgqyy'

class OurCursor(mdb.Cursor):
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

	def add_team(self, team_name, password, is_admin=False):
		sql = 'INSERT INTO teams (team_name, password, is_admin) VALUES(%s, %s, %s);'
		self.execute(sql, (team_name, password, int(bool(is_admin))))

	def add_score(self, team_name, game_id, seed, score, round_num):
		sql = 'INSERT INTO scores (team_name, game_id, seed, score, round) VALUES(%s, %s, %s, %s, %s);'
		cursor = conn.cursor()
		cursor.execute(sql, (team_name, game_id, seed, score, round_num))
		conn.commit()

	def add_practice_score(self, team_name, game_id, seed, score):
		conn = mdb.connect(host=DB_HOST, user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'INSERT INTO practice_scores (team_name, game_id, seed, score) VALUES(%s, %s, %s, %s);'
		cursor = conn.cursor()
		cursor.execute(sql, (team_name, game_id, seed, score))
		conn.commit()

	def latest_round(self):
		conn = mdb.connect(host=DB_HOST, user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'SELECT MAX(round) FROM scores'
		cursor = conn.cursor()
		cursor.execute(sql)
		result = cursor.fetchone()[0]
		if result == None:
			result = 0
		return result

	def scores_by_team():
		conn = mdb.connect(host=DB_HOST, user='dropblox', passwd='dropblox', db='dropblox')
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
		conn = mdb.connect(host=DB_HOST, user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'SELECT * FROM teams WHERE team_name=%s'
		cursor = conn.cursor()
		cursor.execute(sql, team_name)
		return cursor.fetchone()

	@staticmethod
	def list_all_teams():
		conn = mdb.connect(host=DB_HOST, user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'SELECT * FROM teams'
		cursor = conn.cursor()
		cursor.execute(sql)
		return cursor.fetchall()		

	def authenticate_team(self, team_name, password, session_sock=None):
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

	def report_session_ended(self, session_sock):
		if session_sock in Database.AUTHENTICATED_SOCKETS:
			del Database.AUTHENTICATED_SOCKETS[session_sock]

        def _init_db(self):
                def create_tournament_table():
                        sql = """
CREATE TABLE IF NOT EXISTS tournament (
 id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
 school_name VARCHAR(255) NOT NULL,
 date INTEGER NOT NULL
)
ENGINE=InnoDB
"""
                        self.execute(sql)

		def create_team_table():
			sql = """
CREATE TABLE IF NOT EXISTS teams (
 id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
 team_name VARCHAR(64) NOT NULL,
 password CHAR(64) NOT NULL,,
 is_admin INTEGER NOT NULL, ,
 tournament_id INTEGER NOT NULL,
)
ENGINE=InnoDB
"""
			self.execute(sql)

                def create_competition_table():
                        sql = """
CREATE TABLE IF NOT EXISTS competition (
 id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
 tournament_id INTEGER NOT NULL,
 index INTEGER NOT NULL,
 game_seed INTEGER NOT NULL,
 is_practice INTEGER NOT NULL,
)
ENGINE=InnoDB
"""
                        self.execute(sql)

                def create_game_table():
                        sql = """
CREATE TABLE IF NOT EXISTS game (
 id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
 number_moves_made INTEGER NOT NULL,
 game_state TEXT NOT NULL,
 team_id INTEGER NOT NULL,
 competition_id INTEGER NOT NULL,
 score INTEGER
)
ENGINE=InnoDB
"""
                        self.execute(sql)

		def create_admin_user():
			if self.get_team('admin'):
                                return
                        self.add_team('admin', ADMIN_PW, is_admin=1)

                create_tournament_table()
		create_team_table()
		create_admin_user()
                create_competition_table()
                create_game_table()

class Database(object):
        def __init__(self):
                self.connhub = threading.local()
                self._init_db()

        def _get_conn(self):
                try:
                        # XXX: what if the connection dies un-expectedly
                        #      we should do a quick check of that before
                        #      returning to the user
                        return self.connhub.conn
                except AttributeError:
                        # TODO: could probably use a config
                        self.connhub.conn = mdb.connect(host=DB_HOST,
                                                        user='dropblox',
                                                        passwd='dropblox',
                                                        db='dropblox')
                        return self.connhub.conn

        def _get_cursor(self):
                return self._get_conn().cursor(OurCursor)

        @contextlib.contextmanager
        def transaction(self):
                conn = self._get_conn()
                cursor = conn.cursor(OurCursor)
                cursor.execute("BEGIN TRANSACTION")
                try:
                        yield cursor
                except:
                        conn.rollback()
                        raise
                else:
                        conn.commit()

	def _init_db(self):
                with self.transaction() as trans:
                        trans._init_db()

