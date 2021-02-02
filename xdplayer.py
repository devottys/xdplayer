#!/usr/bin/env python3

import sys
import curses

class AttrDict(dict):
    'Augment a dict with more convenient .attr syntax.  not-present keys return None.'
    def __init__(self, **kwargs):
        kw = {}
        for k, v in kwargs.items():
            if isinstance(v, list):
                pass
            elif isinstance(v, str):
                v = list(v)
                if ' ' not in v:
                    v.append(' ')
            elif isinstance(v, bool):
                v = [v, not v]
            elif isinstance(v, int):
                v = [v, 0]
            else:
                v = [v]

            assert isinstance(v, list)
            kw[k] = v
        dict.__init__(self, **kw)

    def __getattr__(self, k):
        try:
            return self[k][0]
        except KeyError:
            if k.startswith("__"):
                raise AttributeError
            return None

    def __dir__(self):
        return self.keys()

    def cycle(self, k):
        self[k] = self[k][1:] + [self[k][0]]

grid_top = 2
grid_left = 4

class Crossword:
    def __init__(self, fn):
        contents = open(fn).read()
        metastr, gridstr, cluestr, *notestr = contents.split('\n\n\n')

        self.meta = {}
        for line in metastr.splitlines():
            k, v = line.split(':', maxsplit=1)
            self.meta[k.strip()] = v.strip()

        self.solution = gridstr.splitlines()
        self.grid = [
                [ '#' if x == '#' else '' for x in row ]
                    for row in self.solution 
                ]
        self.clues = cluestr.splitlines()

        global grid_bottom, grid_right
        grid_bottom = grid_top + len(self.grid)
        grid_right = grid_left + len(self.grid[0])*2

        self.options = AttrDict(
            rowattr = [0, curses.A_UNDERLINE],

            topch = '▁_',
            topattr = [0, curses.A_UNDERLINE],
            botch = '▇⎴',
            botattr = curses.A_REVERSE,
            midblankch = '█',
            leftblankch = '▌',
            rightblankch = '▐',
            rightch = '▎▌│',
            leftch = '▊▐│',
            vline = '│┃|┆┇┊┋',
            inside_vline = ' │|┆┃┆┇┊┋',
            leftattr = [0, curses.A_REVERSE],
            unsolved_char = '· .?□_▁-˙∙•╺‧',

            ulch = ' ▗',
            urch = ' ▖',
            blch = ' ▝',
            brch = ' ▘',
            solved = False,
        )

    def draw_meta(self, scr):
        scr.addstr(0, 0, self.meta['Title'])

    def draw_grid(self, scr):
        d = self.options
        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                if ch == '#':
                    mid = (d.midblankch if x > 0 and row[x-1] == '#' else d.rightblankch) + d.midblankch + (d.midblankch if x < len(row)-1 and row[x+1] == '#' else d.leftblankch)
                    scr.addstr(grid_top+y, grid_left+x*2-1, mid, d.rowattr)
                else:
                    ch = self.solution[y][x] if d.solved else d.unsolved_char
                    scr.addstr(grid_top+y, grid_left+x*2, ch, d.rowattr)
                    scr.addstr(grid_top+y, grid_left+x*2+1, d.inside_vline, d.rowattr)

            scr.addstr(grid_top+y, grid_left-1, d.rightblankch if row[0] == '#' else d.vline)
            scr.addstr(grid_top+y, grid_right-1, d.leftblankch if row[-1] == '#' else d.vline)

        scr.addstr(grid_top-1, grid_left, d.topch*(len(self.grid[0])*2-1), d.topattr)
        scr.addstr(grid_bottom,grid_left, d.botch*(len(self.grid[0])*2-1), d.rowattr | d.botattr)

        scr.addstr(grid_top-1, grid_left-1, d.ulch)
        scr.addstr(grid_bottom,grid_left-1, d.blch)
        scr.addstr(grid_top-1, grid_right-1, d.urch)
        scr.addstr(grid_bottom,grid_right-1, d.brch)

        scr.move(0,0)

    def draw_clues(self, scr):
        pass

    def draw(self, scr):
        scr.erase()
        self.draw_meta(scr)
        self.draw_grid(scr)
        self.draw_clues(scr)

def main(scr):
    xd = Crossword(sys.argv[1])
    while True:
        opt = xd.options
        xd.draw(scr)
        hotkeys = {}
        for y, (k, v) in enumerate(opt.items()):
            key = "0123456789abcdefghijklmnopqrstuvwxyz"[y]
            hotkeys[key] = k

            scr.addstr(grid_top+y, 40, key)
            scr.addstr(grid_top+y, 45, k)
            scr.addstr(grid_top+y, 60, ' '.join(map(str, v)))

        k = scr.getkey()

        if k == 'q': return
        if k in hotkeys: opt.cycle(hotkeys[k])

curses.wrapper(main)
