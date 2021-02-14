#!/usr/bin/env python3

import sys
import textwrap
import time
import string
import curses
from collections import namedtuple, defaultdict

from tui import *

UNFILLED = '.'

opt = OptionsObject(
    fgbgattr = ['white on black', 'underline'],
    fgattr = ['white'],
    bgattr = ['black'],
    gridattr = ['white'],
    unsolvedattr = ['white'],
    acrattr = ['210'],
    downattr = ['74'],
    curacrattr = ['175'],
    curdownattr = ['189'],
    blockattr = ['white'],

    helpattr = ['bold 69'],
    clueattr = ['7'],

    topch = '▁_',
    topattr = ['white', 'underline'],
    botch = '▇⎴',
    botattr = ['black on white'],
    midblankch = '█',
    leftblankch = '▌',
#    rightblankch = '▐',
#    rightch = '▎▌│',
#    leftch = '▊▐│',
#    vline = '│┃|┆┇┊┋',
#    inside_vline = ' │|┆┃┆┇┊┋',
    leftattr = ['', 'reverse'],
    unsolved_char = '· .?□_▁-˙∙•╺‧',
    dirarrow = '→↪⇢⇨',

    hotkeys= False,
)

BoardClue = namedtuple('BoardClue', 'dir num clue answer coords')

def half(fg_coloropt, bg_coloropt):
    return colors['%s on %s' % (opt[fg_coloropt+'attr'][0], opt[bg_coloropt+'attr'][0])]


def log(*args):
    print(*args, file=sys.stderr)
    sys.stderr.flush()


class Crossword:
    def __init__(self, fn):
        self.fn = fn
        self.load()

        self.filldir = 'A'
        self.cursor_x = 0
        self.cursor_y = 0

        self.clue_layout = {}

        self.move_grid(3, len(self.meta))


    def load(self):
        contents = open(self.fn).read()
        metastr, gridstr, cluestr, *notestr = contents.split('\n\n\n')

        self.meta = {}
        for line in metastr.splitlines():
            k, v = line.split(':', maxsplit=1)
            self.meta[k.strip()] = v.strip()

        self.solution = gridstr.splitlines()

        self.grid = [[x for x in row] for row in self.solution]

        self.clues = {}  # 'A1' -> Clue
        for clue in cluestr.splitlines():
            if clue:
                if ' ~ ' in clue:
                    clue, answer = clue.split(' ~ ')
                else:
                    answer = ''
                dirnum, clue = clue.split('. ', maxsplit=1)
                dir, num = dirnum[0], int(dirnum[1:])
                self.clues[dirnum] = BoardClue(dir, num, clue, answer, [])  # final is board positions, filled in below


        self.pos = defaultdict(list)  # (y,x) -> [(dir, num, answer), ...] associated words with that cell
        for dir, num, answer, r, c in self.iteranswers_full():
            for i in range(len(answer)):
                w = self.clues[f'{dir}{num}']
                coord = (r,c+i) if dir == 'A' else (r+i,c)
                self.pos[coord].append(w)
                w[-1].append(coord)

    def move_grid(self, x, y):
        global grid_bottom, grid_right, grid_top, grid_left
        global clue_left, clue_top
        grid_left = x
        grid_top = y
        grid_bottom = grid_top + self.nrows
        grid_right = grid_left + self.ncols*2
        clue_left = grid_right+3
        clue_top = grid_top

    def clear(self):
        self.grid = [['#' if x == '#' else UNFILLED for x in row] for row in self.solution]

    @property
    def acr_clues(self):
        return {k:v for k, v in self.clues.items() if k[0] == 'A'}

    @property
    def down_clues(self):
        return {k:v for k, v in self.clues.items() if k[0] == 'D'}

    @property
    def nrows(self):
        return len(self.grid)

    @property
    def ncols(self):
        return len(self.grid[0])

    @property
    def ncells(self):
        return len([c for r in self.grid for c in r if c != '#'])

    @property
    def nsolved(self):
        return len([c for r in self.grid for c in r if c not in '.#'])

    def cell(self, r, c):
        if r < 0 or c < 0 or r >= self.nrows or c >= self.ncols:
            return '#'
        return self.grid[r][c]

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

    def is_cursor(self, y, x, down=False):
        w = self.pos[(y, x)]
        if not w: return False
        cursor_words = self.pos[(self.cursor_y, self.cursor_x)]
        if not cursor_words: return False
        return sorted(cursor_words)[down] == sorted(w)[down]

    def charcolor(self, y, x, half=True):
        ch = self.cell(y, x)
        if ch == '#':
            return 'block'
        dcurs = self.is_cursor(y, x, down=True)
        acurs = self.is_cursor(y, x, down=False)
        if acurs and dcurs: return 'curacr' if self.filldir == 'A' else 'curdown'
        if acurs: return 'acr'
        if dcurs: return 'down'

    def draw(self, scr):
        h, w = scr.getmaxyx()
        # draw meta
        y = 0
        for k, v in self.meta.items():
            if y >= h-self.nrows-2:
                break
            scr.addstr(y, 1, '%10s: %s' % (k, v))
            y += 1

        self.move_grid(3, max(0, min(h-self.nrows-2, y+1)))

        # draw grid
        d = opt
        cursor_words = self.pos[(self.cursor_y, self.cursor_x)]
        if cursor_words:
            cursor_across, cursor_down = sorted(cursor_words)
        else:
            cursor_across, cursor_down = None, None

        for y, row in enumerate(self.grid):
            for x in range(-1, len(row)):
                ch = self.cell(y, x)
                clr = self.charcolor(y, x)
                fch = self.cell(y, x+1)  # following char
                fclr = self.charcolor(y, x+1) or 'bg' # following color

                ch1 = ch # printed character
                ch2 = opt.leftblankch # printed second half

                attr = opt.fgbgattr

                if clr in "acr down curacr curdown".split():
                    attr = colors[opt[clr+'attr'][0] + ' reverse']
                elif clr:
                    attr = getattr(opt, clr+'attr')

                if ch == UNFILLED:
                    ch1 = opt.unsolved_char
                elif ch == '#':
                    ch1 = opt.midblankch
                    attr = opt.blockattr

                if clr or fclr:
                    attr2 = half(clr or 'bg', fclr or 'bg')  # colour of ch2
                elif not (clr or fclr):
                    attr2 = colors['white on black']
                else:
                    attr2 = colors['black on black']


                if scr:
                    if x >= 0:
                        scr.addstr(grid_top+y, grid_left+x*2, ch1, attr)
                    scr.addstr(grid_top+y, grid_left+x*2+1, ch2, attr2)

        if scr:
            scr.addstr(grid_top-1, grid_left, opt.topch*(self.ncols*2-1), opt.topattr)
            scr.addstr(grid_bottom,grid_left, opt.botch*(self.ncols*2-1), opt.botattr)

        def draw_clues(clue_top, clues, cursor_clue, n):
            'Draw clues around cursor in one direction.'
            dirnums = list(clues.values())
            i = dirnums.index(cursor_clue)
            y=0
            for clue in dirnums[max(i-2,0):]:
                if y >= n:
                    break
                if cursor_clue == clue:
                    attr = (opt.acrattr if clue.dir == 'A' else opt.downattr) | curses.A_REVERSE
                    if self.filldir == clue.dir:
                        scr.addstr(clue_top+y, clue_left-2, f'{opt.dirarrow} ', (opt.acrattr if clue.dir == 'A' else opt.downattr))
                else:
                    attr = opt.clueattr

                dirnum = f'{clue.dir}{clue.num}'
                guess = ''.join([self.grid[r][c] for r, c in self.clues[dirnum][-1]])
                self.clue_layout[dirnum] = y
                dnw = len(dirnum)+2
                maxw = min(w-clue_left-dnw-1, 40)
                for j, line in enumerate(textwrap.wrap(clue.clue + f' [{guess}]', width=maxw)):
                    prefix = f'{dirnum}. ' if j == 0 else ' '*dnw
                    line = prefix + line + ' '*(maxw-len(line))
                    self.clue_layout[clue_top+y] = clue
                    scr.addstr(clue_top+y, clue_left, line, attr)
                    y += 1

        clueh = self.nrows//2-1
        draw_clues(clue_top, self.acr_clues, cursor_across, clueh)
        draw_clues(clue_top+clueh+2, self.down_clues, cursor_down, clueh)

    def draw_hotkeys(self, scr):
        self.hotkeys = {}
        h, w = scr.getmaxyx()
        for i, (k, v) in enumerate(opt.items()):
            key = "0123456789abcdefghijklmnopqrstuvwxyz"[i]
            self.hotkeys[key] = k

            y = grid_top+self.nrows+i+1
            if y < h-1:
                scr.addstr(y, 3, key)
                scr.addstr(y, 5, k)
                scr.addstr(y, 15, ' '.join(map(str, v)))

    def cursorDown(self, n):
        i = n
        while self.cell(self.cursor_y+i, self.cursor_x) == '#' and self.cursor_y+i >= 0 and self.cursor_y+i < self.nrows-1:
            i += n
        if self.cell(self.cursor_y+i, self.cursor_x) == '#' or self.cursor_y+i < 0 or self.cursor_y+i >= self.nrows:
            return
        self.cursor_y += i

    def cursorRight(self, n):
        i = n
        while self.cell(self.cursor_y, self.cursor_x+i) == '#' and self.cursor_x+i >= 0 and self.cursor_x+i < self.ncols:
            i += n
        if self.cell(self.cursor_y, self.cursor_x+i) == '#' or self.cursor_x+i < 0 or self.cursor_x+i >= self.ncols:
            return
        self.cursor_x += i

    def cursorMove(self, n):
        if self.filldir == 'A':
            if self.cell(self.cursor_y, self.cursor_x+n) != '#':
                self.cursorRight(n)
        else:
            if self.cell(self.cursor_y+n, self.cursor_x) != '#':
                self.cursorDown(n)

    def save(self, fn):
        with open(fn, 'w') as fp:
            for y, (k, v) in enumerate(self.meta.items()):
                fp.write('%s: %s\n' % (k,v))
            fp.write('\n\n')

            for y, line in enumerate(self.grid):
                fp.write(''.join(line)+'\n')
            fp.write('\n\n')

            for clue in self.acr_clues.values():
                fp.write(f'{clue.dir}{clue.num}. {clue.clue}\n')
            fp.write('\n')

            for clue in self.down_clues.values():
                fp.write(f'{clue.dir}{clue.num}. {clue.clue}\n')

    def setAtCursor(self, ch):
        self.grid[self.cursor_y][self.cursor_x] = ch
        self.save(self.fn)


class CrosswordPlayer:
    def __init__(self):
        self.statuses = []
        self.xd = None
        self.n = 0

    def status(self, s):
        self.statuses.append(s)

    def play_one(self, scr, xd):
        h, w = scr.getmaxyx()
        xd.draw(scr)
        if self.statuses:
            scr.addstr(h-2, clue_left, self.statuses.pop())
        rstat = '%d%% solved (%d/%d)' % ((xd.nsolved*100/xd.ncells), xd.nsolved, xd.ncells)
        scr.addstr(h-3, clue_left, rstat)

        # draw helpstr
        scr.addstr(h-1, 0, " Arrows move | Tab toggle direction | Ctrl+Q quit | Ctrl+R clear ", opt.helpattr)

        if opt.hotkeys:
            xd.draw_hotkeys(scr)
            scr.addstr(1, w-20, f'{h}x{w}')
        k = getkeystroke(scr)
        if k == '^Q': return True
        if k == 'KEY_RESIZE': h, w = scr.getmaxyx()
        if k == '^L': scr.clear()

        scr.erase()
        if opt.hotkeys:
            scr.addstr(0, w-20, k)
            scr.addstr(0, w-5, str(self.n))
        self.n += 1

        if k == 'KEY_MOUSE':
            devid, x, y, z, bstate = curses.getmouse()
            if grid_top <= y < grid_bottom and grid_left <= x < grid_right:
                x = (x-grid_left)//2
                y = y-grid_top
                if xd.grid[y][x] != '#':
                    xd.cursor_x = x
                    xd.cursor_y = y
            elif y in xd.clue_layout:
                xd.cursor_y, xd.cursor_x = xd.clue_layout[y][-1][0]
            else:
                self.status(f'{bstate}({y},{x})')

        elif k == 'KEY_DOWN': xd.cursorDown(+1)
        elif k == 'KEY_UP': xd.cursorDown(-1)
        elif k == 'KEY_LEFT': xd.cursorRight(-1)
        elif k == 'KEY_RIGHT': xd.cursorRight(+1)
        elif k == '^I': xd.filldir = 'A' if xd.filldir == 'D' else 'D'
        elif k == '^R': xd.clear()
        elif k == '^X':
            opt.hotkeys = not opt.hotkeys
            return

        elif k == 'KEY_BACKSPACE':  # back up and erase
            xd.cursorMove(-1)
            xd.setAtCursor(UNFILLED)
        elif k == ' ':  # erase and advance
            xd.setAtCursor(UNFILLED)
            xd.cursorMove(+1)
        elif k == 'KEY_DC':  # erase in place
            xd.setAtCursor(UNFILLED)
        elif opt.hotkeys and k in xd.hotkeys:
            opt.cycle(xd.hotkeys[k])
        elif k.upper() in string.ascii_uppercase:
            xd.setAtCursor(k.upper())
            xd.cursorMove(+1)


def main(scr):
    curses.use_default_colors()
    curses.raw()
    curses.meta(1)
    curses.curs_set(0)
    curses.mousemask(-1)

    plyr = CrosswordPlayer()
    xd = Crossword(sys.argv[1])
    lastt = 0
    while not plyr.play_one(scr, xd):
        t = time.time()
        if t - lastt > 1:  # every second
            xd.load()
            lastt = t

if '--clear' == sys.argv[1]:
    for fn in sys.argv[2:]:
        xd = Crossword(fn)
        xd.clear()
        xd.save(fn)
else:
    curses.wrapper(main)
