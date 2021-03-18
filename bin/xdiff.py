#!/usr/bin/env python3

'''
    Usage:  xdiff.py <golden.xd>

        Compare grid in test1.xd (and all others) to grid in <golden.xd> and report results in tabular form.
        $TEAMDIR must be set.
'''

import os
import sys
import stat
import sqlite3
import time
from pathlib import Path

from xdplayer import Crossword

def is_submitted(fn):
    'Return True if exists and is readonly.'
    g = Path(fn).stat()
    if g and not (g.st_mode & stat.S_IWUSR):
        return 1
    return 0

def main_diff(fn):
    xd = Crossword(fn)
    correct = xd.grade()
    teamid = str(xd.guessfn).split('/')[-2]

    conn = sqlite3.connect(os.getenv('XDDB', 'xd.db'))
    curs = conn.cursor()

    curs.execute('''INSERT OR REPLACE INTO solvings (xdid, teamid, date_checked, correct, nonblocks, submitted) VALUES (?, ?, ?, ?, ?, ?)''', (Path(fn).stem, teamid,
                time.strftime("%Y-%m-%d %H:%M:%S"),
                correct, xd.ncells, is_submitted(xd.guessfn)))

    conn.commit()


if __name__ == '__main__':
    main_diff(sys.argv[1])
