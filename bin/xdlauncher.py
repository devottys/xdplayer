#!/usr/bin/env python3

import os
import subprocess
import stat

import visidata
from visidata import SqliteQuerySheet, Path, vd, Column, SuspendCurses, date


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
        Column('modtime', width=0, type=date, getter=lambda c,r: Path(r[-1]).stat()[stat.ST_MTIME]),
    ]
    _ordering = [('modtime', True)]  # sort by reverse modtime initially
    def openRow(self, row):
        with SuspendCurses():
            return subprocess.call(['./xdplayer.py', row[-1]])


visidata.run(xdLauncher('xd_launcher', source=Path(os.getenv('XDDB', 'xd.db'))))
