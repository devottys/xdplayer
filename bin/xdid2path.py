#!/usr/bin/env python3

import sys
import os
import sqlite3

conn = sqlite3.connect(os.getenv('XDDB', 'xd.db'))
curs = conn.cursor()
r = curs.execute('SELECT path FROM xdmeta WHERE xdid=?', (sys.argv[1],)).fetchone()
if r:
    print(r[0])

