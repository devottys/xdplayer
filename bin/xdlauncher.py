#!/usr/bin/env python3

import os
import subprocess
import stat

import visidata
from visidata import SqliteQuerySheet, Path, vd, Column, SuspendCurses, date, VisiData
from visidata import copy, ColumnItem, IndexSheet


def stat_guesses(fn):
    'Return Path($TEAMDIR/{fn.stem}.xd-guesses.jsonl'
    xdid = Path(fn).stem
    p = Path(os.getenv('TEAMDIR', '.'))/(xdid+'.xd-guesses.jsonl')
    return p.stat()

def is_submitted(fn):
    'Return True if exists and is readonly.'
    g = stat_guesses(fn)
    if not g:
        return False
    return not (stat_guesses(fn).st_mode & stat.S_IWUSR)

def modtime(fn):
    g = stat_guesses(fn)
    if not g:
        return None
    return g.st_mtime

def solve_hours(fn):
    g = stat_guesses(fn)
    if not g:
        return None
    return (g.st_ctime - g.st_mtime)/3600


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

class xdLauncherAll(SqliteQuerySheet):
    # 3rd sheet: puzzles for this date, + started by all teams
    query=launcher_select+'''
                WHERE solvings.teamid is not null
                OR SUBSTR(DATE('now'), 6, 5) = SUBSTR(date_published, 6, 5)
                '''
    columns = [
        Column('modtime', width=0, type=date, getter=lambda c,r: modtime(r[-1])),
        Column('submitted', width=0, getter=lambda c,r: is_submitted(r[-1])),
        Column('solve_h', type=float, getter=lambda c,r: solve_hours(r[-1])),
    ]
    _ordering = [('modtime', True)]  # sort by reverse modtime initially
    def openRow(self, row):
        with SuspendCurses():
            return subprocess.call(['python3', '-m', 'xdplayer', row[-1]])

class xdLauncherWIP(xdLauncherAll):
    'Load puzzles for this date in history, plus those started but not submitted by teamid.'
    query=launcher_select+'''
                WHERE (solvings.submitted = 0 AND solvings.teamid = ?) OR (SUBSTR(DATE('now'), 6, 5) = SUBSTR(date_published, 6, 5))
                '''
    parms = [os.getenv('TEAMID', '')]

class xdLauncherStarted(xdLauncherAll):
    # 2nd sheet -> puzzles started by all teams
    query=launcher_select+'''WHERE solvings.teamid is not null'''

class xdLauncher(IndexSheet):
    rowtype = 'views'
    def iterload(self):
        self.rows = []
        yield xdLauncherWIP('play_next', source=self.source)
        yield xdLauncherStarted('started_puzzles', source=self.source)
        yield xdLauncherAll('all_puzzles', source=self.source)


visidata.run(xdLauncher('xd_launcher', source=Path(os.getenv('XDDB', 'xd.db'))))
