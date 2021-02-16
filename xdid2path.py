#!/usr/bin/env python3

import sys
import sqlite3

conn = sqlite3.connect('xdp.db')
curs = conn.cursor()
r = curs.execute('SELECT path FROM xdmeta WHERE xdid=?', (sys.argv[1],)).fetchone()
if r:
    print(r[0])

