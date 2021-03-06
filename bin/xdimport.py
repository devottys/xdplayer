#!/usr/bin/env python3

# Usage: ./xdimport.py <output_folder> <file.xd/puz ...>

# Record metadata for one or more puzzles to sqlite db 'xdmeta' table.
# Save unsolved versions into <output_folder>.

import os
import sys
import stat
import sqlite3
from pathlib import Path

from xdplayer import Crossword


def main_import():
    conn = sqlite3.connect(os.getenv('XDDB', 'xd.db'))
    curs = conn.cursor()
    curs.execute('''CREATE TABLE IF NOT EXISTS xdmeta (
                    xdid TEXT NOT NULL PRIMARY KEY,
                    path TEXT,
                    size TEXT,
                    title TEXT,
                    author TEXT,
                    editor TEXT,
                    copyright TEXT,
                    date_published TEXT,
                    A1 TEXT,
                    D1 TEXT
                    )''')

    curs.execute('''CREATE TABLE IF NOT EXISTS solvings (
                    xdid TEXT NOT NULL,
                    teamid TEXT NOT NULL,
                    date_checked TEXT,
                    correct INT,
                    nonblocks INT,
                    submitted INT,
                    PRIMARY KEY (xdid, teamid))''')


    for fn in sys.argv[1:]:
        try:
            xd = Crossword(fn)
        except Exception:
            print(f'Skipped {fn}, was not imported')
            continue
        xdid = Path(fn).stem
        for dir, num, answer, r, c in xd.iteranswers_full():
            if dir == 'A' and num == 1:
                a1 = answer
            elif dir == 'D' and num == 1:
                d1 = answer

        try:
            curs.execute('''INSERT INTO xdmeta (xdid, path, size, title, author, editor, copyright, date_published, A1, D1) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (xdid, str(Path(fn).absolute()),
                    f'{xd.ncols}x{xd.nrows}',
                    xd.meta.get('Title', ''),
                    xd.meta.get('Author', ''),
                    xd.meta.get('Editor', ''),
                    xd.meta.get('Copyright', ''),
                    xd.meta.get('Date', ''),
                    a1, d1))
        except sqlite3.IntegrityError:
            print(f"Failed to insert {fn}, already in database")
            continue


    conn.commit()


if __name__ == '__main__':
    main_import()
