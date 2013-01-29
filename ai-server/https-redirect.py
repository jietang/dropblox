#!/usr/bin/env python
#
# Redirect HTTP to HTTPS
#

import cherrypy

class HTTPSUpgradeServer(object):
	@cherrypy.expose
	def default(self):
		raise cherrypy.HTTPRedirect("https://playdropblox.com")

if __name__ == '__main__':
    cherrypy.quickstart(HTTPSUpgradeServer(), config={
        'global': {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 80,
        },
    })