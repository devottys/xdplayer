#!/usr/bin/env python3

from xdplayer import *
from unittest.mock import Mock

class PlayerTest():
    def __init__(self):
        scr = Mock()
        scr.addstr = Mock()
        scr.move = Mock()
        scr.getmaxyx = lambda: (25, 80)
        scr.colors = []
        self.scr = ScrWrapper(scr)
        self.passed = 0

    def report(self):
        print(f'{self.passed} tests passed')

    def setup(self):
        self.plyr = CrosswordPlayer(["samples/wsj110624.xd"])

    def test_eq(self, a, b):
        assert a == b, f'{a} != {b}'
        self.passed += 1

    def test_cursor_pos(self, xd, x, y):
        self.test_eq((xd.cursor_x, xd.cursor_y), (x,y))

    def move_keystrokes(self, movestr):
        moves = dict(
            R='KEY_RIGHT',
            L='KEY_LEFT',
            U='KEY_UP',
            D='KEY_DOWN',
            SR='KEY_SRIGHT',
            SL='KEY_SLEFT',
        )
        return [moves[i] for i in movestr.split(' ') if i != '']

    def test_move(self, movestr, x, y, filldir='A'):
        keystrokes = self.move_keystrokes(movestr)
        self.scr.getkeystroke = lambda x=keystrokes: x.pop(0)
        self.setup()
        self.plyr.xd.filldir = filldir

        for i in range(len(keystrokes)):
            self.plyr.play_one(self.scr, self.plyr.xd)

        self.test_cursor_pos(self.plyr.xd, x, y)


def test_moves():
    t = PlayerTest()
    t.test_move('R', 1, 0)       # move right without a block in the way
    t.test_move('R '*7, 8, 0)    # move right over a block
    t.test_move('R '*21, 20, 0)  # move right and stop at line break

    t.test_move('R R L', 1, 0)      # move left once without a block in the way
    t.test_move('R '*7 + 'L', 6, 0) # move left over a block
    t.test_move('L', 0, 0)          # move left and stop at left side

    t.test_move('SR', 8, 0)      # skip to the next across in the same row
    t.test_move('SR '*3, 0, 1)   # skip to the next across, wrapping right
    t.test_move('SR '*66, 0, 0)  # wrap around from the last across to the first

    t.test_move('SR SL', 0, 0)          # skip to the previous across in the same row
    t.test_move('SR '*3 + 'SL', 17, 0)  # skip to the previous across, wrapping left
    t.test_move('SL', 14, 20)           # wrap around from the first across to the last

    t.test_move('SR', 1, 0, 'D')       # skip to the next down in the same row
    t.test_move('SR '*19, 7, 2, 'D')   # skip to the next down, wrapping right
    t.test_move('SR '*72, 0, 0, 'D')   # wrap around from the last down to the first

    t.test_move('SR SL', 0, 0, 'D')           # skip to the previous down in the same row
    t.test_move('SR '*19 + 'SL', 20, 0, 'D')  # skip to the previous down, wrapping left
    t.test_move('SL', 14, 18, 'D')            # wrap around from the first down to the last

    t.report()


if __name__ == '__main__':
    test_moves()
