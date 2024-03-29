#!/usr/bin/env python3

import os
import sqlite3
import curses
from pathlib import Path
from xdplayer import main_player

launcher_select = '''SELECT
                    solvings.teamid,
                    solvings.correct*100/solvings.nonblocks AS completed,
                    date_published,
                    size,
                    title,
                    author,
                    editor,
                    copyright,
                    xdmeta.xdid,
                    path
                    FROM xdmeta
                    LEFT OUTER JOIN solvings ON xdmeta.xdid = solvings.xdid
                    '''


conn = sqlite3.connect(str(Path(os.getenv('XDDB', 'xd.db')).resolve()))

## Used for NGW to only have crosswords for the previous day, or that were begun
#query = launcher_select+'''
 #               WHERE (solvings.submitted = 0 and solvings.teamid = ?) OR (SUBSTR(DATE('now', '-1 day', 'localtime'), 1, 10) = SUBSTR(date_published, 1, 10))
  #              '''
#parms = [os.getenv('TEAMID', '')]

query = launcher_select
parms = []

results = conn.execute(query, parms)

crossword_paths = [res[-1] for res in results]
os.umask(0) # so guesses file can be chmod'd
curses.wrapper(main_player, *crossword_paths)

