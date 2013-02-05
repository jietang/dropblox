#!/usr/bin/env python
#
# Provides persistence to MySQL

import contextlib
import json
import random
import threading
import time

import MySQLdb as mdb
import bcrypt

import util
from logic.board import Board

DB_HOST = '10.35.9.6'
ADMIN_PW = '$2a$12$xmaAYZoZEyqGZWfoXZfZI.ik3mjrzVcGOg3sxvnfFU/lS5n6lgqyy'

class Container(object):
        def __init__(self, **kw):
                for (k, v) in kw.iteritems():
                        setattr(self, k, v)

        def to_dict(self):
                out = {}
                for (k, v) in self.__dict__.iteritems():
                        if hasattr(v, 'to_dict'):
                                out[k] = v.to_dict()
                        else:
                                out[k] = v
                return out

class GameDoesNotExistError(Exception): pass
class TeamNotAuthorizedToChangeGameError(Exception): pass
class GameOverError(Exception):
        def __init__(self, game_state):
                self.game_state = game_state


class OurCursor(mdb.Cursor):
	# Tuple indices for team objects
	TEAM_TEAM_NAME = 1
	TEAM_PASSWORD = 2
	TEAM_IS_ADMIN = 3
	TEAM_TOURNAMENT_ID = 4

	# Tuple indices for score objects
	SCORE_TEAM_NAME = 0
	SCORE_GAME_ID = 1
	SCORE_SEED = 2
	SCORE_SCORE = 3
	SCORE_ROUND = 4

	def add_team(self, tournament_id, team_name, password, is_admin=False):
		sql = 'INSERT INTO teams (team_name, password, is_admin, tournament_id) VALUES(%s, %s, %s);'
		self.execute(sql, (team_name, password, int(bool(is_admin)), tournament_id))

	def add_score(self, team_name, game_id, seed, score, round_num):
		sql = 'INSERT INTO scores (team_name, game_id, seed, score, round) VALUES(%s, %s, %s, %s, %s);'
		self.execute(sql, (team_name, game_id, seed, score, round_num))

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

	def scores_by_team(self):
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

	def get_team_by_name(self, team_name):
		conn = mdb.connect(host=DB_HOST, user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'SELECT id, team_name, password, is_admin, tournament_id FROM teams WHERE team_name=%s'
		cursor = conn.cursor()
		cursor.execute(sql, team_name)
		t = cursor.fetchone()
                if t is None:
                        return None
                return Container(id=t[0], name=t[1], password=t[2], is_admin=t[3],
                                 tournament_id=t[4])

	def list_all_teams(self):
		conn = mdb.connect(host=DB_HOST, user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'SELECT * FROM teams'
		cursor = conn.cursor()
		cursor.execute(sql)
		return cursor.fetchall()

	def authenticate_team(self, team_name, password):
		team = self.get_team_by_name(team_name)
		if team is None:
			return None

		if bcrypt.hashpw(password, team.password) != team.password:
			return None

		return team

        def has_running_test_game(self, tournament_id, team_id):
                sql = """
SELECT EXISTS(
    SELECT 1 FROM game WHERE
    score IS NULL AND
    competition_id = competition.id AND
    team_id = %s
) FROM competition WHERE tournament_id = %s AND is_practice
"""

                self.execute(sql, (team_id, tournament_id))
                return self.fetchone()[0]

        def create_test_game(self, tournament_id, team_id):
                game_seed = random.randint(-2**31, 2**31-1)
                while True:
                        # index is unimportant for practice competitions
                        index = random.randint(-2**31, 2**31-1)

                        try:
                                comp = self._create_competition(tournament_id, index,
                                                                game_seed, True)
                        except self.connection.IntegrityError:
                                continue
                        else:
                                break
                return self._create_game(comp.id, team_id, game_seed)

        def get_game_by_id(self, game_id):
                sql = """
SELECT id, number_moves_made, game_state, team_id, competition_id, score
FROM game
WHERE id = %s
"""
                self.execute(sql, (game_id,))
                game_row = self.fetchone()
                if game_row is None:
                        return None

                return Container(id=game_row[0],
                                 number_moves_made=game_row[1],
                                 game_state=Board.from_dict(json.loads(game_row[2])),
                                 team_id=game_row[3],
                                 competition_id=game_row[4])

        def _update_game(self, game_id, game_state):
                sql = """
UPDATE game SET
number_moves_made = number_moves_made + 1,
game_state = %s,
WHERE id = %s
"""
                self.execute(sql,
                             (json.dumps(game_state.to_dict()), game_id))
                if game_state.state != "failed":
                        return

                sql = """
UPDATE game SET score = %s
WHERE id = %s
"""
                self.execute(sql,
                             (game_state.score, game_id))

        def submit_game_move(self, game_id, team_id, move_list):
                game = self.get_game_by_id(game_id)

		if game is None:
                        raise GameDoesNotExistError()

                if game.team_id != team_id:
                        raise TeamNotAuthorizedToChangeGameError()

                game_state = game.game_state

		if game_state.state == 'failed':
                        raise GameOverError(game_state)

		if time.time() - game_state.game_started_at > util.AI_CLIENT_TIMEOUT:
                        # game is over
			game_state.state = 'failed'
		else:
                        # this mutates the in-memory verison
                        # of game.game_state
			game_state.send_commands(move_list)

                self._update_game(game_id, game_state)

		if game_state.state == 'failed':
                        raise GameOverError(game_state)

                assert game_state.state == 'playing'

        def _create_game(self, competition_id, team_id, game_seed):
                assert isinstance(competition_id, int), "bad competition id%r" % (competition_id,)
                assert isinstance(team_id, int), "bad team id%r" % (team_id,)
                assert isinstance(game_seed, int), "bad game seed id%r" % (game_seed,)
                sql = """
INSERT INTO game (
number_moves_made,
game_state,
team_id,
competition_id,
)
VALUES
(?, ?, ?, ?)
"""
                gs = Board(game_seed)
                self.execute(sql, (0, json.dumps(gs), team_id, competition_id))
                game_id = self.connection.insert_id()
                return Container(id=game_id,
                                 number_moves_made=0,
                                 game_state=gs,
                                 team_id=team_id,
                                 competition_id=competition_id)

        def _create_competition(self, tournament_id, index, game_seed, is_practice):
                # sorry we need hard types, mysql isn't duck-type friendly
                assert isinstance(tournament_id, int), "tournament_id isn't int: %r" % (tournament_id,)
                assert isinstance(index, int), "index isn't int: %r" % (index,)
                assert isinstance(game_seed, int), "seed isn't int: %r" % (game_seed,)
                assert isinstance(is_practice, bool), "is_practice isn't boolt : %r" % (is_practice,)
                sql = """
INSERT INTO competition (tournament_id, index, game_seed, is_pratice) VALUES(%s, %s, %s, %s)
"""
                self.execute(sql, (tournament_id, index, game_seed, int(is_practice)))
                competition_id = self.connection.insert_id()
                return Container(id=competition_id,
                                 tournament_id=tournament_id,
                                 index=index,
                                 game_seed=game_seed,
                                 is_practice=is_practice)

	def report_session_ended(self, session_sock):
		if session_sock in Database.AUTHENTICATED_SOCKETS:
			del Database.AUTHENTICATED_SOCKETS[session_sock]

        def _init_db(self):
                def create_tournament_table():
                        sql = """
CREATE TABLE IF NOT EXISTS tournament (
 id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
 school_name VARCHAR(255) NOT NULL,
 date INTEGER NOT NULL,
 UNIQUE (school_name)
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
 UNIQUE (tournament_id, team_name)
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
 UNIQUE (tournament_id, is_practice, index)
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
 score INTEGER,
 UNIQUE (competition_id, team_id)
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

