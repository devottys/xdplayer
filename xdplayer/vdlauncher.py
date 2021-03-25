#!/usr/bin/env python3

import os
import stat

from visidata import SqliteQuerySheet, Path, Column, date

class vdLauncher(SqliteQuerySheet):
    'Load puzzles started, but not submitted by teamid.'

    @classmethod
    def stat_guesses(cls, fn):
        'Return Path($TEAMDIR/{fn.stem}.xd.guesses.jsonl'
        xdid = Path(fn).stem
        p = Path(os.getenv('TEAMDIR', '.'))/(xdid+'.xd-guesses.jsonl')
        return p.stat()

    @classmethod
    def is_submitted(cls, fn):
        'Return True if exists and is readonly.'
        g = cls.stat_guesses(fn)
        if not g:
            return False
        return not (cls.stat_guesses(fn).st_mode & stat.S_IWUSR)

    @classmethod
    def modtime(cls, fn):
        g = cls.stat_guesses(fn)
        if not g:
            return None
        return g.st_mtime

    @classmethod
    def solve_hours(cls, fn):
        g = cls.stat_guesses(fn)
        if not g:
            return None
        return (g.st_ctime - g.st_mtime)/3600

    query = '''SELECT
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
            WHERE (solvings.submitted = 0 AND solvings.teamid = ?)
            '''

    columns = [
            Column('modtime', width=0, type=date, getter=lambda c,r: vdLauncher.modtime(r[-1])),
            Column('submitted', width=0, getter=lambda c,r: vdLauncher.is_submitted(r[-1])),
            Column('solve_h', type=float, getter=lambda c,r: vdLauncher.solve_hours(r[-1])),
            ]
    _ordering = [('modtime', True)] # sort by reverse modtime initially

    parms = [os.getenv('TEAMID', '')]
