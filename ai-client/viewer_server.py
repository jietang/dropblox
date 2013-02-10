#!python
import os
import cherrypy

class Root:
    pass


if __name__ == '__main__':
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Set up site-wide config first so we get a log if errors occur.
    cherrypy.config.update({'environment': 'production',
                            'log.error_file': 'site.log',
                            'log.screen': True})

    conf = {'/': {'tools.staticdir.root': os.getcwd(),
                  'tools.staticdir.on': True,
                  'tools.staticdir.dir': 'static',
                  'tools.staticdir.index': 'index.html',
                  }}

    cherrypy.quickstart(Root(), config=conf)
