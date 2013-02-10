#!/usr/bin/env python
#
# Provides persistence to MySQL

import contextlib
import json
import random
import threading
import time

from collections import defaultdict

import MySQLdb as mdb
from MySQLdb.cursors import Cursor
import bcrypt

from logic.Board import Board

DB_HOST = '127.0.0.1'
ADMIN_PW = '$2a$12$xmaAYZoZEyqGZWfoXZfZI.ik3mjrzVcGOg3sxvnfFU/lS5n6lgqyy'
ACCEPTABLE_INT_TYPES = (int, long)

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

	def __repr__(self):
		return 'Container(**%r)' % (self.to_dict(),)

NUM_TEAM_ROWS = 8
def container_from_team_row(row):
	return Container(id=row[0],
			 name=row[1],
			 password=row[2],
			 is_admin=row[3],
			 ts=row[4],
			 is_connected=row[5],
			 is_whitelisted_next_round=row[6],
			 tournament_id=row[7])

def container_from_competition_row(row):
	return Container(id=row[0],
			 tournament_id=row[1],
			 index=row[2],
			 game_seed=row[3],
			 is_practice=row[4],
			 ts=row[5])

def container_from_tournament_row(row):
	return Container(id=row[0],
			 school_name=row[1],
			 date=row[2],
			 next_competition_index=row[3])

def container_from_game_row(row, offset=0):
	return Container(id=row[offset],
			 number_moves_made=row[offset + 1],
			 game_state=Board.from_dict(json.loads(row[offset + 2])),
			 team_id=row[offset + 3],
			 competition_id=row[offset + 4],
			 score=row[offset + 5],
			 finished_ts=row[offset + 6],
			 )

class OurCursor(Cursor):
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

	def _cur_ts(self):
		return int(time.time())

	def add_team(self, tournament_id, team_name, password, is_admin=False):
		sql = 'INSERT INTO teams (team_name, password, is_admin, tournament_id, ts, is_whitelisted_next_round, is_connected) VALUES (%s, %s, %s, %s, %s, 0, 0);'
		self.execute(sql, (team_name, password, int(bool(is_admin)), tournament_id, self._cur_ts()))

	def add_team_member(self, tournament_id, team_name, email, name):
		sql = 'INSERT INTO team_members (team_name, email, name, tournament_id, ts) VALUES (%s, %s, %s, %s, %s);'
		self.execute(sql, (team_name, email, name, tournament_id, self._cur_ts()))

	def get_scores_by_team_for_tournament(self, tournament_id):
		sql = """
SELECT game.team_id, competition.c_index as round, game.score FROM game
LEFT JOIN competition ON
game.competition_id = competition.id
WHERE
competition.tournament_id = %s AND
game.score IS NOT NULL AND
competition.is_practice = 0
"""
		self.execute(sql, (tournament_id,))
		scores = self.fetchall()

		team_to_scores = defaultdict(list)
		for (team_id, round, score) in scores:
			team_to_scores[team_id].append({
					'score' : score,
					'round' : round + 1,
					})
		return team_to_scores

	def get_team_by_name(self, team_name):
		sql = 'SELECT * FROM teams WHERE team_name = %s'
		self.execute(sql, (team_name,))
		t = self.fetchone()
                if t is None:
                        return None
                return container_from_team_row(t)

	def get_team(self, team_id):
		sql = 'SELECT * FROM teams WHERE id = %s'
		self.execute(sql, (team_id,))
		t = self.fetchone()
                if t is None:
                        return None
                return container_from_team_row(t)

	def list_all_teams_for_tournament(self, tournament_id):
		sql = """
SELECT
*
FROM teams
WHERE tournament_id = %s
ORDER BY team_name ASC
"""
		self.execute(sql, (tournament_id,))
		return map(container_from_team_row, self.fetchall())

	def authenticate_team(self, team_name, password):
		team = self.get_team_by_name(team_name)
		if team is None:
			return None

		if bcrypt.hashpw(password, team.password) != team.password:
			return None

		return team

        def has_running_practice_game(self, tournament_id, team_id):
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

	def _create_game_seed(self):
		return random.randint(-2**31, 2**31-1)

        def create_practice_game(self, team_id):
		team = self.get_team(team_id)
		tournament_id = team.tournament_id

                game_seed = self._create_game_seed()
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
SELECT *
FROM game
WHERE id = %s
"""
                self.execute(sql, (game_id,))
                game_row = self.fetchone()
                if game_row is None:
                        return None

                return container_from_game_row(game_row)

        def update_game(self, game_id, moves_made, game_state, score, is_finished):
                sql = """
UPDATE game SET
number_moves_made = %s,
game_state = %s
WHERE id = %s
"""
                self.execute(sql,
                             (moves_made, json.dumps(game_state.to_dict()), game_id))
                if not is_finished:
                        return

                sql = """
UPDATE game SET
score = %s,
finished_ts = %s
WHERE id = %s
"""
                self.execute(sql,
                             (game_state.score, self._cur_ts(), game_id))

	def _empty_game_state(self, game_seed):
		return 

        def _create_game(self, competition_id, team_id, game_seed):
                assert isinstance(competition_id, ACCEPTABLE_INT_TYPES), "bad competition id%r" % (competition_id,)
                assert isinstance(team_id, ACCEPTABLE_INT_TYPES), "bad team id%r" % (team_id,)
                assert isinstance(game_seed, ACCEPTABLE_INT_TYPES), "bad game seed id%r" % (game_seed,)
                sql = """
INSERT INTO game (
number_moves_made,
game_state,
team_id,
competition_id
)
VALUES
(%s, %s, %s, %s)
"""
                gs = Board(game_seed)
                self.execute(sql, (0, json.dumps(gs.to_dict()), team_id, competition_id))
                game_id = self.lastrowid
                return Container(id=game_id,
                                 number_moves_made=0,
                                 game_state=gs,
                                 team_id=team_id,
                                 competition_id=competition_id)

        def _create_competition(self, tournament_id, index, game_seed, is_practice):
                # sorry we need hard types, mysql isn't duck-type friendly
                assert isinstance(tournament_id, ACCEPTABLE_INT_TYPES), "tournament_id isn't int: %r" % (tournament_id,)
		assert tournament_id >= 0, "tournament_id is negative: %r" % (tournament_id,)
                assert isinstance(index, ACCEPTABLE_INT_TYPES), "index isn't int: %r" % (index,)
                assert isinstance(game_seed, ACCEPTABLE_INT_TYPES), "seed isn't int: %r" % (game_seed,)
                assert isinstance(is_practice, bool), "is_practice isn't boolt : %r" % (is_practice,)
                sql = """
INSERT INTO competition (tournament_id, c_index, game_seed, is_practice, ts)
VALUES (%s, %s, %s, %s, %s)
"""
                self.execute(sql, (tournament_id, index, game_seed, int(is_practice), self._cur_ts()))
                competition_id = self.lastrowid
                return Container(id=competition_id,
                                 tournament_id=tournament_id,
                                 index=index,
                                 game_seed=game_seed,
                                 is_practice=is_practice)

	def get_current_tournament(self):
		sql = """
SELECT * FROM tournament
WHERE id = (
    SELECT tournament_id FROM current_tournament
    WHERE id = 0
    LIMIT 1
)
"""
		self.execute(sql)
		row = self.fetchone()
		if row is None:
			return None
		return container_from_tournament_row(row)

	def get_tournament(self, tournament_id):
		sql = """
SELECT * FROM tournament
WHERE id = %s
"""
		self.execute(sql, (tournament_id,))
		row = self.fetchone()
		if row is None:
			return None
		return container_from_tournament_row(row)

	def competition_has_started(self, competition_id):
		sql = """
SELECT EXISTS(
    SELECT 1 FROM
    competition INNER JOIN game
    ON competition.id = game.competition_id
    WHERE
    competition.id = %s
)
"""
		self.execute(sql, (competition_id,))
		(has_started,) = self.fetchone()
		return has_started

	def get_current_whitelisted_teams(self, tournament_id):
		sql = """
SELECT * FROM teams WHERE
teams.tournament_id = %s AND
teams.is_whitelisted_next_round
"""
		self.execute(sql, (tournament_id,))
		return map(container_from_team_row, self.fetchall())

	def get_current_competition_state_for_tournament(self, tournament_id):
		"""
		This method does a lot because all this information is polled
		during the main competition display.

		We want to limit the round trips to MySQL so we do it all
		in one mega query.
		"""
		sql = """
SELECT teams.*, game.* FROM teams LEFT JOIN game ON
teams.id = game.team_id
WHERE
teams.tournament_id = %s AND
teams.is_whitelisted_next_round AND
game.competition_id = (
    SELECT competition.id FROM competition JOIN tournament ON
    competition.tournament_id = tournament.id
    WHERE
    tournament.id = %s AND
    competition.c_index = tournament.next_competition_index
)
"""
		self.execute(sql, (tournament_id, tournament_id))
		rows = self.fetchall()
		return [(container_from_team_row(row),
			 (None if row[NUM_TEAM_ROWS] is None else
			  container_from_game_row(row, offset=NUM_TEAM_ROWS)))
			for row in rows]

	def start_next_competition(self, tournament_id):
		tournament = self.get_tournament(tournament_id)
		next_competition_index = tournament.next_competition_index
                game_seed = self._create_game_seed()

		sql = """
INSERT INTO competition (
    tournament_id,
    c_index, game_seed,
    is_practice, ts
) VALUES
(%s, %s, %s, 0, %s)
"""
		self.execute(sql, (
				tournament_id,
				next_competition_index,
				game_seed,
				int(time.time()),
				))
		competition_id = self.lastrowid

                empty_game = json.dumps(Board(game_seed).to_dict())
		sql = """
INSERT INTO game
(number_moves_made, game_state, team_id, competition_id)
SELECT 0, %s, teams.id, %s FROM teams WHERE
teams.is_whitelisted_next_round AND
teams.tournament_id = %s
"""
		self.execute(sql, (empty_game, competition_id, tournament_id))

	def report_session_ended(self, session_sock):
		if session_sock in Database.AUTHENTICATED_SOCKETS:
			del Database.AUTHENTICATED_SOCKETS[session_sock]

	def get_competition(self, competition_id):
                sql = """
SELECT *
FROM competition
WHERE id = %s
"""
                self.execute(sql, (competition_id,))
                row = self.fetchone()
                if row is None:
                        return None

                return container_from_competition_row(row)

	def get_competition_by_index(self, tournament_id, competition_index):
		sql = """
SELECT *
FROM competition
WHERE
tournament_id = %s AND
c_index = %s
"""
		self.execute(sql, (tournament_id, competition_index))
		row = self.fetchone()
		if row is None:
			return None
		return container_from_competition_row(row)

	def set_is_whitelisted_team_by_name(self, tournament_id, team_name, whitelisted):
                assert isinstance(tournament_id, ACCEPTABLE_INT_TYPES), "tournament id is bad: %r" % (tournament_id,)
                assert isinstance(whitelisted, bool), "whitelisted isn't bool : %r" % (whitelisted,)
		sql = """
UPDATE teams SET
is_whitelisted_next_round = %s
WHERE
team_name = %s AND
tournament_id = %s
"""
		self.execute(sql, (int(whitelisted), team_name, tournament_id))

	def games_for_competition(self, competition_id):
		sql = """
SELECT * FROM game WHERE
competition_id = %s
"""
		self.execute(sql, (competition_id,))
		return map(container_from_game_row, self.fetchall())

	def increment_next_competition_index(self, tournament_id):
		sql = """
UPDATE tournament SET
next_competition_index = next_competition_index + 1
WHERE id = %s
"""
		self.execute(sql, (tournament_id,))

        def _init_db(self):
                def create_tournament_table():
                        sql = """
CREATE TABLE IF NOT EXISTS tournament (
 id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
 school_name VARCHAR(255) NOT NULL,
 date INTEGER NOT NULL,
 next_competition_index INTEGER NOT NULL,
 UNIQUE (school_name)
)
ENGINE=InnoDB
"""
                        self.execute(sql)

                def create_current_tournament_table():
                        sql = """
CREATE TABLE IF NOT EXISTS current_tournament (
 id INTEGER PRIMARY KEY NOT NULL,
 tournament_id INTEGER NOT NULL
)
ENGINE=InnoDB
"""
                        self.execute(sql)

		def create_team_table():
			sql = """
CREATE TABLE IF NOT EXISTS teams (
 id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
 team_name VARCHAR(64) NOT NULL,
 password CHAR(64) NOT NULL,
 is_admin INTEGER NOT NULL,
 tournament_id INTEGER NOT NULL,
 ts INTEGER NOT NULL,
 is_connected INTEGER NOT NULL,
 is_whitelisted_next_round INTEGER NOT NULL,
 UNIQUE (tournament_id, team_name)
)
ENGINE=InnoDB
"""
			self.execute(sql)


		def create_team_member_table():
			sql = """
CREATE TABLE IF NOT EXISTS team_members (
 id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
 team_name VARCHAR(64) NOT NULL,
 email CHAR(64) NOT NULL,
 name CHAR(64) NOT NULL,
 tournament_id INTEGER NOT NULL,
 ts INTEGER NOT NULL,
 UNIQUE (tournament_id, email)
)
ENGINE=InnoDB
"""
			self.execute(sql)


                def create_competition_table():
                        sql = """
CREATE TABLE IF NOT EXISTS competition (
 id INTEGER PRIMARY KEY NOT NULL AUTO_INCREMENT,
 tournament_id INTEGER NOT NULL,
 c_index INTEGER NOT NULL,
 game_seed INTEGER NOT NULL,
 is_practice INTEGER NOT NULL,
 ts INTEGER NOT NULL,
 UNIQUE (tournament_id, is_practice, c_index)
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
 finished_ts INTEGER,
 UNIQUE (competition_id, team_id)
)
ENGINE=InnoDB
"""
                        self.execute(sql)

		def create_admin_user():
			if self.get_team_by_name('admin'):
                                return
                        self.add_team(-1, 'admin', ADMIN_PW, is_admin=1)

                create_tournament_table()
                create_current_tournament_table()
		create_team_table()
		create_team_member_table()
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
                cursor.execute("BEGIN")
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

