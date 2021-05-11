#!/usr/bin/env python3

'''
    Usage:  TEAMID=teamname xdinject.py <xdid...>

        Inject puzzle into today's mix.
        $TEAMID must be set.
'''

import os
import sys
import sqlite3
import time

def main_inject(fn):
    teamid = os.getenv('TEAMID')

    conn = sqlite3.connect(os.getenv('XDDB', 'xd.db'))
    curs = conn.cursor()

    curs.execute('''INSERT OR REPLACE INTO solvings (xdid, teamid, date_checked, correct, nonblocks, submitted) VALUES (?, ?, ?, ?, ?, ?)''', (xdid, teamid,
                time.strftime("%Y-%m-%d %H:%M:%S"),
                0, 0, 0))

    conn.commit()


if __name__ == '__main__':
    for xdid in sys.argv[1:]:
        main_inject(xdid)
