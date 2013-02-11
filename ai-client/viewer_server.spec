# -*- mode: python -*-
a = Analysis(['../../dropblox/ai-client/viewer_server.py'],
             pathex=['/Users/jie/code/pyinstaller-dev/pyinstaller-pyinstaller-f16d3c3'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          Tree('../../dropblox/ai-client/static', 'static'),
          name=os.path.join('dist', 'viewer_server'),
          debug=False,
          strip=None,
          upx=True,
          console=True )
