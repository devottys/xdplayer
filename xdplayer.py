#!/usr/bin/env python3

import sys
import string
import curses
from collections import namedtuple, defaultdict

def getkeystroke(scr):
    k = scr.get_wch()
    if isinstance(k, str):
        if ord(k) >= 32 and ord(k) != 127:  # 127 == DEL or ^?
            return k
        k = ord(k)
    return curses.keyname(k).decode('utf-8')

class ColorMaker:
    def __init__(self):
        self.attrs = {}
        self.color_attrs = {}

        default_bg = curses.COLOR_BLACK

        self.color_attrs['black'] = curses.color_pair(0)

        for c in range(0, 256 or curses.COLORS):
            try:
                curses.init_pair(c+1, c, default_bg)
                self.color_attrs[str(c)] = curses.color_pair(c+1)
            except curses.error as e:
                pass # curses.init_pair gives a curses error on Windows

        for c in 'red green yellow blue magenta cyan white'.split():
            colornum = getattr(curses, 'COLOR_' + c.upper())
            self.color_attrs[c] = curses.color_pair(colornum+1)

        for a in 'normal blink bold dim reverse standout underline'.split():
            self.attrs[a] = getattr(curses, 'A_' + a.upper())

    def __getitem__(self, colornamestr):
        return self._colornames_to_cattr(colornamestr)

    def __getattr__(self, colornamestr):
        return self._colornames_to_cattr(optname).attr

    def _colornames_to_cattr(self, colornamestr):
        color, attr = 0, 0
        for colorname in colornamestr.split(' '):
            if colorname in self.color_attrs:
                if not color:
                    color = self.color_attrs[colorname.lower()]
            elif colorname in self.attrs:
                attr = self.attrs[colorname.lower()]
        return attr | color


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
            v = self[k][0]
            if k.endswith('attr'):
                v = colors[v]
            return v
        except KeyError:
            if k.startswith("__"):
                raise AttributeError

            return None

    def __dir__(self):
        return self.keys()

    def cycle(self, k):
        self[k] = self[k][1:] + [self[k][0]]

class Crossword:
    def __init__(self, fn):
        contents = open(fn).read()
        metastr, gridstr, cluestr, *notestr = contents.split('\n\n\n')

        self.meta = {}
        for line in metastr.splitlines():
            k, v = line.split(':', maxsplit=1)
            self.meta[k.strip()] = v.strip()

        self.filldir = 'A'
        self.solution = gridstr.splitlines()
        self.grid = [
                [ '#' if x == '#' else '.' for x in row ]
                    for row in self.solution 
                ]
        self.acr_clues = {}
        self.down_clues = {}
        for clue in cluestr.splitlines():
            if clue:
                clue, answer = clue.split(' ~ ')
                dirnum, clue = clue.split('. ', maxsplit=1)
                dir, num = dirnum[0], int(dirnum[1:])
                cluetuple = (dir, num, clue, answer)
                if dir == 'A':
                    self.acr_clues[dirnum] = cluetuple
                else:
                    self.down_clues[dirnum] = cluetuple

        self.cursor_x = 0
        self.cursor_y = 0

        global grid_bottom, grid_right, grid_top, grid_left
        global acrclueleft, downclueleft, clue_top
        grid_left = 4
        grid_top = len(self.meta)+2
        grid_bottom = grid_top + self.nrows
        grid_right = grid_left + self.ncols*2
        acrclueleft = 40
        downclueleft = 40
        clue_top = grid_top


        self.options = AttrDict(
            rowattr = ['', 'underline'],
            curattr = ['reverse 217'],
            curacrattr = ['reverse 125'],
            curdownattr = ['reverse 74'],
            clueattr = ['7'],

            topch = '▁_',
            topattr = ['', 'underline'],
            botch = '▇⎴',
            botattr = ['reverse'],
            midblankch = '█',
            leftblankch = '▌',
            rightblankch = '▐',
            rightch = '▎▌│',
            leftch = '▊▐│',
            vline = '│┃|┆┇┊┋',
            inside_vline = ' │|┆┃┆┇┊┋',
            leftattr = ['', 'reverse'],
            unsolved_char = '· .?□_▁-˙∙•╺‧',

            ulch = ' ▗',
            urch = ' ▖',
            blch = ' ▝',
            brch = ' ▘',
            solved = False,
            hotkeys= False,
        )

        self.pos = defaultdict(list)  # (y,x) -> [(dir, num, answer), ...] associated words with that cell
        for dir, num, answer, r, c in self.iteranswers_full():
            for i in range(len(answer)):
                if dir == 'A':
                    self.pos[(r,c+i)].append(self.acr_clues[f'{dir}{num}'])
                else:
                    self.pos[(r+i,c)].append(self.down_clues[f'{dir}{num}'])

    @property
    def nrows(self):
        return len(self.grid)

    @property
    def ncols(self):
        return len(self.grid[0])

    def cell(self, r, c):
        if r < 0 or c < 0 or r >= self.nrows or c >= self.ncols:
            return '#'
        return self.solution[r][c]

    def iteranswers_full(self):
        'Generate ("A" or "D", clue_num, answer, r, c) for each word in the grid.'

        NON_ANSWER_CHARS = '_#'
        clue_num = 1
        for r, row in enumerate(self.solution):
            for c, cell in enumerate(row):
                # compute number shown in box
                new_clue = False
                if self.cell(r, c - 1) in NON_ANSWER_CHARS:  # across clue start
                    ncells = 0
                    answer = ""
                    while self.cell(r, c + ncells) not in NON_ANSWER_CHARS:
                        cellval = self.cell(r, c + ncells)
                        answer += cellval
                        ncells += 1

                    if ncells > 1:
                        new_clue = True
                        yield "A", clue_num, answer, r, c

                if self.cell(r - 1, c) in NON_ANSWER_CHARS:  # down clue start
                    ncells = 0
                    answer = ""
                    while self.cell(r + ncells, c) not in NON_ANSWER_CHARS:
                        cellval = self.cell(r + ncells, c)
                        answer += cellval
                        ncells += 1

                    if ncells > 1:
                        new_clue = True
                        yield "D", clue_num, answer, r, c

                if new_clue:
                    clue_num += 1

    def draw(self, scr):
        # draw meta
        for y, (k, v) in enumerate(self.meta.items()):
            scr.addstr(y, 0, '%s: %s' %(k,v))

        # draw grid
        d = self.options
        cursor_words = self.pos[(self.cursor_y, self.cursor_x)]
        if cursor_words:
            cursor_across, cursor_down = sorted(cursor_words)
        else:
            cursor_across, cursor_down = None, None

        for y, row in enumerate(self.grid):
            for x, ch in enumerate(row):
                attr = d.rowattr
                attr2 = d.rowattr

                if ch == '#':
                    ch = d.midblankch
                    ch2 = d.midblankch if x < len(row)-1 and row[x+1] == '#' else d.leftblankch
                else:
                    if d.solved:
                        ch = self.solution[y][x]
                    else:
                        ch = self.grid[y][x]
                        if ch == '.': ch = d.unsolved_char

                    ch2 = d.inside_vline

                    words = self.pos[(y,x)]
                    across_word, down_word = sorted(words)
                    if cursor_across == across_word and cursor_down == down_word:
                        attr = d.curattr
                        attr2 = d.curattr
                        #ch2 = ' '
                    elif cursor_across == across_word:
                        attr = d.curacrattr
                        attr2 = d.curacrattr
                        #ch2 = ' '
                    elif cursor_down == down_word:
                        attr = d.curdownattr
                        attr2 = d.curdownattr
                        #ch2 = ' '

                if scr:
                    scr.addstr(grid_top+y, grid_left+x*2, ch, attr)
                    scr.addstr(grid_top+y, grid_left+x*2+1, ch2, attr2)

                if x == 0:
                    if ch == '#' or cursor_down == down_word:
                        ch = d.leftblankch
                    else:
                        ch = d.vline
                    scr.addstr(grid_top+y, grid_left-1, ch, attr)

                if x == len(row)-1:
                    if ch == '#' or cursor_down == down_word:
                        ch = d.rightblankch
                    else:
                        ch = d.vline
                    scr.addstr(grid_top+y, grid_right-1, ch, attr)


        if scr:
            scr.addstr(grid_top-1, grid_left, d.topch*(self.ncols*2-1), d.topattr)
            scr.addstr(grid_bottom,grid_left, d.botch*(self.ncols*2-1), d.rowattr | d.botattr)

            scr.addstr(grid_top-1, grid_left-1, d.ulch)
            scr.addstr(grid_bottom,grid_left-1, d.blch)
            scr.addstr(grid_top-1, grid_right-1, d.urch)
            scr.addstr(grid_bottom,grid_right-1, d.brch)

            scr.move(0,0)

        n = 5
        # draw clues around both cursors
        dirnums = list(self.acr_clues.values())
        i = dirnums.index(cursor_across)
        y=0
        for clue in dirnums[max(i-n//2,0):]:
            if y > n:
                break
            dir, num, cluestr, answer = clue
            if cursor_across == clue:
                attr = d.curacrattr
            else:
                attr = d.clueattr
            scr.addstr(clue_top+y, acrclueleft, f'{dir}{num}. {cluestr}', attr)
            y += 1

        y += 1
        dirnums = list(self.down_clues.values())
        i = dirnums.index(cursor_down)
        for clue in dirnums[max(i-n//2,0):]:
            if y > n*2:
                break
            dir, num, cluestr, answer = clue
            if cursor_down == clue:
                attr = d.curdownattr
            else:
                attr = d.clueattr
            scr.addstr(clue_top+y, downclueleft, f'{dir}{num}. {cluestr}', attr)
            y += 1

    def draw_hotkeys(self, scr):
        self.hotkeys = {}
        for y, (k, v) in enumerate(self.options.items()):
            key = "0123456789abcdefghijklmnopqrstuvwxyz"[y]
            self.hotkeys[key] = k

            scr.addstr(grid_top+y, 40, key)
            scr.addstr(grid_top+y, 45, k)
            scr.addstr(grid_top+y, 60, ' '.join(map(str, v)))

    def cursorDown(self, n):
        i = n
        while self.cell(self.cursor_y+i, self.cursor_x) == '#' and self.cursor_y+i >= 0 and self.cursor_y+i < self.nrows-1:
            i += n
        if self.cursor_y+i < 0 or self.cursor_y+i >= self.nrows:
            return
        self.cursor_y += i

    def cursorRight(self, n):
        i = n
        while self.cell(self.cursor_y, self.cursor_x+i) == '#' and self.cursor_x+i >= 0 and self.cursor_x+i < self.ncols:
            i += n
        if self.cursor_x+i < 0 or self.cursor_x+i >= self.ncols:
            return
        self.cursor_x += i

class CrosswordPlayer:
    def __init__(self):
        self.statuses = []
        self.xd = None
        self.n = 0

    def status(self, s):
        self.statuses.append(s)

    def play_one(self, scr, xd):
        h, w = scr.getmaxyx()
        opt = xd.options
        xd.draw(scr)
        if self.statuses:
            scr.addstr(h-1, 10, self.statuses.pop())
        if opt.hotkeys:
            xd.draw_hotkeys(scr)
        k = getkeystroke(scr)
        if k == 'q': return True
        if k == '^L': scr.clear()

        scr.clear()
        scr.addstr(h-1, 0, k)
        scr.addstr(h-1, 40, str(self.n))
        self.n += 1

        if k == 'KEY_MOUSE':
            devid, x, y, z, bstate = curses.getmouse()
            if grid_top <= y < grid_bottom and grid_left <= x < grid_right:
                x = (x-grid_left)//2
                y = y-grid_top
                if xd.grid[y][x] != '#':
                    xd.cursor_x = x
                    xd.cursor_y = y
            else:
                self.status('not on grid')

        elif k == 'KEY_DOWN': xd.cursorDown(+1)
        elif k == 'KEY_UP': xd.cursorDown(-1)
        elif k == 'KEY_LEFT': xd.cursorRight(-1)
        elif k == 'KEY_RIGHT': xd.cursorRight(+1)
        elif k == '^I': xd.filldir = 'A' if xd.filldir == 'D' else 'D'
        elif k == '^X':
            opt.hotkeys = not opt.hotkeys
            return 

        elif k.upper() in string.ascii_uppercase:
            xd.grid[xd.cursor_y][xd.cursor_x] = k.upper()
            if xd.filldir == 'A':
                xd.cursorRight(1)
            else:
                xd.cursorDown(1)

        if opt.hotkeys and k in xd.hotkeys:
            opt.cycle(xd.hotkeys[k])


def main(scr):
    global colors

    curses.use_default_colors()
    curses.raw()
    curses.meta(1)
    curses.mousemask(-1)

    colors = ColorMaker()

    plyr = CrosswordPlayer()
    xd = Crossword(sys.argv[1])
    while not plyr.play_one(scr, xd):
        pass

curses.wrapper(main)
