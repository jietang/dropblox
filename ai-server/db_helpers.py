#!/usr/bin/env python
#
# Database utility functions

import MySQLdb as mdb
import sys

class DatabaseHelpers(object):

	@staticmethod
	def add_team(team_name, password):
		conn = mdb.connect(host='localhost', user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'INSERT INTO teams (team_name, password, is_admin) VALUES(%s, %s, %s);'
		cursor = conn.cursor()
		cursor.execute(sql, (team_name, password, 0))
		conn.commit()

	@staticmethod
	def setup_test_users():
		for i in range(0, 40):
			team_name = 'team%s' % i
			DatabaseHelpers.add_team(team_name, '$2a$12$zF8T/F5S0sHt90rBbvfW9.6atxwMzsNvWvesxLy5uYj1gJr28/OqO')

	@staticmethod
	def drop_tables():
		conn = mdb.connect(host='localhost', user='dropblox', passwd='dropblox', db='dropblox')
		sql = 'DROP DATABASE dropblox;'
		cursor = conn.cursor()
		cursor.execute(sql)
		conn.commit()
		sql = 'CREATE DATABASE dropblox;'
		cursor = conn.cursor()
		cursor.execute(sql)
		conn.commit()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Usage: db_helpers.py [mock_users|reset_db]"
        sys.exit(0)

    if sys.argv[1] != "mock_users" and sys.argv[1] != "reset_db":
        print "Usage: db_helpers.py [mock_users|reset_db]"
        sys.exit(0)

    if sys.argv[1] == "mock_users":
    	DatabaseHelpers.setup_test_users()
    elif sys.argv[1] == "reset_db":
    	DatabaseHelpers.drop_tables()