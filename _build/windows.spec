#!/usr/bin/env python3
# -*- mode: python -*-

import os
import sys
import PyQt5

block_cipher = None

a = Analysis(['..\\baidugrabber\\__main__.py'],
             pathex=[
                 os.path.join(sys.modules['PyQt5'].__path__[0], 'Qt', 'bin'),
                 'C:\\Program Files (x86)\\Windows Kits\\10\\Redist\\ucrt\\DLLs\\x64',
                 '..'
             ],
             binaries=[],
             datas=[
                 ('..\\baidugrabber\\__init__.py', '.'),
                 ('..\\bin\\win32\\*.*', 'bin\\win32'),
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=['numpy'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='baidu-grabber',
          debug=False,
          strip=False,
          upx=False,
          console=False , icon='icons\\baidu-grabber.ico')
