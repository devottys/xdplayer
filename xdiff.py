#!/usr/bin/env python3

'''
    Usage:  xdiff.py <golden.xd>

        Compare grid in test1.xd (and all others) to grid in <golden.xd> and report results in tabular form.
        $TEAMDIR must be set.
'''

import sys
import sqlite3
import time
from pathlib import Path

from xdplayer import Crossword


def main_diff():
    xd1 = Crossword(sys.argv[1])
    xd2 = Crossword(sys.argv[1])
    xd2.clear()
    xd2.replay_guesses()

    conn = sqlite3.connect(getenv('XDDB', 'xd.db'))
    curs = conn.cursor()
    nonblocks = sum(1 for r in xd1.grid for c in r if c != '#')

    for fn in sys.argv[2:]:
        xd2 = Crossword(fn)
        correct = sum(1 for y, r in enumerate(xd2.grid) for x, c in enumerate(r) if c != '#' and c == xd1.grid[y][x])

        curs.execute('''INSERT INTO solvings VALUES (?, ?, ?, ?)''', (Path(fn).stem,
                time.strftime("%Y-%m-%d %H:%M:%S"),
                correct, nonblocks))

    conn.commit()


if __name__ == '__main__':
    main_diff()