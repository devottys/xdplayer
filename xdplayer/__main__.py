'''
Usage:
    python3 -m xdplayer <test.xd>
        Play <test.xd> (include any solved in .xd)
        Ctrl+S to save over <test.xd>

    python3 -m xdplayer <test.puz>
        Play <test.puz>, saving a cleared puzzle as test.puz.xd.
        Ctrl+S to save as <test.puz.xd>

    Filling letters in from the grid will append to <test.xd>-guesses.jsonl (chmod).
'''

import os
import sys
import curses

from . import main_player

if __name__ == '__main__':
    if not sys.argv[1:]:
        print(__doc__)
    else:
        os.umask(0)  # so guesses file can be chmod'd
        curses.wrapper(main_player)
