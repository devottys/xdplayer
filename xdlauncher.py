#!/usr/bin/env python3

import os
import subprocess

import visidata
from visidata import SqliteQuerySheet, Path, vd, Column, SuspendCurses


class xdLauncher(SqliteQuerySheet):
    query='''SELECT xdmeta.xdid,
                    size,
                    title,
                    author,
                    editor,
                    copyright,
                    date_published,
                    solvings.teamid,
                    solvings.correct,
                    solvings.nonblocks,
                    path
                FROM xdmeta
                LEFT OUTER JOIN solvings ON xdmeta.xdid = solvings.xdid'''
    columns = [
        Column('mtime'),
    ]
    def openRow(self, row):
        with SuspendCurses():
            return subprocess.call(['./xdplayer.py', row[-1]])


visidata.run(xdLauncher(source=Path(os.getenv('XDDB', 'xd.db'))))
