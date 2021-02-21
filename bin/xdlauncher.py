#!/usr/bin/env python3

import os
import subprocess
import stat

import visidata
from visidata import SqliteQuerySheet, Path, vd, Column, SuspendCurses, date, VisiData


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

def solvetime(fn):
    g = stat_guesses(fn)
    if not g:
        return None
    return g.st_ctime - g.st_mtime

class xdLauncher(SqliteQuerySheet):
    query='''SELECT xdmeta.xdid,
                    solvings.teamid,
                    solvings.correct,
                    solvings.nonblocks,
                    size,
                    title,
                    author,
                    editor,
                    copyright,
                    date_published,
                    path
                FROM xdmeta
                LEFT OUTER JOIN solvings ON xdmeta.xdid = solvings.xdid'''
    columns = [
        Column('modtime', width=0, type=date, getter=lambda c,r: modtime(r[-1])),
        Column('submitted', width=0, getter=lambda c,r: is_submitted(r[-1])),
        Column('solve_secs', type=int, getter=lambda c,r: solvetime(r[-1])),
    ]
    _ordering = [('modtime', True)]  # sort by reverse modtime initially
    def openRow(self, row):
        with SuspendCurses():
            return subprocess.call(['python3', '-m', 'xdplayer', row[-1]])


visidata.run(xdLauncher('xd_launcher', source=Path(os.getenv('XDDB', 'xd.db'))))
