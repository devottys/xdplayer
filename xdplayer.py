#!/usr/bin/env python3

import sys
import textwrap
import string
import curses
from collections import namedtuple, defaultdict

from tui import *

UNFILLED = '.'

opt = OptionsObject(
    rowattr = ['', 'underline'],
    acrattr = ['210'],
    downattr = ['74'],
    curacrattr = ['175'],
    curdownattr = ['189'],
    blockattr = ['white'],
    helpattr = ['bold 69'],
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
    dirarrow = '→↪⇢⇨',

    ulch = ' ▗',
    urch = ' ▖',
    blch = ' ▝',
    brch = ' ▘',
    hotkeys= False,
)

BoardClue = namedtuple('BoardClue', 'dir num clue answer coords')

class Crossword:
    def __init__(self, fn):
        self.fn = fn
        contents = open(fn).read()
        metastr, gridstr, cluestr, *notestr = contents.split('\n\n\n')

        self.meta = {}
        for line in metastr.splitlines():
            k, v = line.split(':', maxsplit=1)
            self.meta[k.strip()] = v.strip()

        self.filldir = 'A'
        self.solution = gridstr.splitlines()

        self.clear()
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

        self.cursor_x = 0
        self.cursor_y = 0
        self.clue_layout = {}

        self.move_grid(3, len(self.meta))

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

    def is_cursor(self, y, x, down=False):
        w = self.pos[(y, x)]
        if not w: return False
        cursor_words = self.pos[(self.cursor_y, self.cursor_x)]
        if not cursor_words: return False
        return sorted(cursor_words)[down] == sorted(w)[down]

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
            for x, ch in enumerate(row):
                attr = opt.rowattr
                attr2 = opt.rowattr

                ch1 = ch
                if ch == '#':
                    ch1 = opt.midblankch
                else:
                    assert ch == self.grid[y][x]
                    if ch == UNFILLED: ch1 = opt.unsolved_char

                    ch2 = opt.inside_vline

                    words = self.pos[(y,x)]
                    across_word, down_word = sorted(words)
                    if cursor_across == across_word and cursor_down == down_word:
                        attr = attr2 = (opt.curacrattr if self.filldir == 'A' else opt.curdownattr) | curses.A_REVERSE
                    elif cursor_across == across_word:
                        attr = attr2 = opt.acrattr | curses.A_REVERSE
                    elif cursor_down == down_word:
                        attr = attr2 = opt.downattr | curses.A_REVERSE

                # calc ch2 -- A2B
                ch2 = opt.inside_vline
                fch = self.cell(y, x+1)
                bch = self.cell(y, x-1)
                acursordown = cursor_down == down_word
                acursoracr = cursor_across == across_word
                fcursordown = self.is_cursor(y, x+1, down=True)
                fcursoracr = self.is_cursor(y, x+1, down=False)

                attr2 = attr

                if ch == '#' and fch == '#': ch2 = opt.midblankch
                elif fch == '#': ch2 = opt.rightblankch
                elif ch == '#': ch2 = opt.leftblankch

                if acursordown:
                    # we are in Down Tab
                    if fch == '#' and ch != '#':
                        # if the vertical cursor is flush against a block to its right
                        ch2 = opt.rightblankch
                        attr2 = colors['white on ' + opt['downattr'][0]]
                    else:
                        if fcursoracr:
                            attr2 = colors[opt['downattr'][0] + ' on ' + opt['acrattr'][0]]

                if acursoracr:
                    if fch == '#' and ch != '#':
                        # make the right edge of across, flush with border
                        attr2 = colors['white on ' + opt['acrattr'][0]]
                        ch2 = opt.rightblankch
                    else:
                        if fcursordown:
                            attr2 = colors[opt['acrattr'][0] + ' on ' + opt['downattr'][0]]


                if fcursordown and not acursoracr:
                    # ensure the vertical line is centered, when away from a border
                    attr2 = colors[opt['downattr'][0]]
                    ch2 = opt.rightblankch

                # if it is an intersecting point between vertical and horizontal
                if cursor_across == across_word and cursor_down == down_word and fch != '#' and ch != '#':
                    ch2 = opt.midblankch
                    attr2 = (opt.curacrattr if self.filldir == 'A' else opt.curdownattr)

                def color(fg_optname, bg_optname):
                    return colors[opt[fg_optname][0] + ' on ' + opt[bg_optname][0]]

                if fcursordown and fcursoracr:
                    ch2 = opt.rightblankch
                    attr2 = color('curacrattr' if self.filldir == 'A' else 'curdownattr', 'acrattr')
                elif fcursordown and ch == '#':
                    ch2 = opt.rightblankch
                    attr2 = color('downattr', 'blockattr')
                elif fcursoracr and ch == '#':
                    ch2 = opt.rightblankch
                    attr2 = color('acrattr', 'blockattr')


                if scr:
                    scr.addstr(grid_top+y, grid_left+x*2, ch1, attr)
                    scr.addstr(grid_top+y, grid_left+x*2+1, ch2, attr2)

                if x == 0:
                    ch1 = opt.leftblankch
                    if acursordown:
                        cn = 'white on ' + opt['downattr'][0]
                        attr = colors['white on ' + opt['downattr'][0]]
                        ch1 = opt.leftblankch
                    if acursoracr:
                        cn = 'white on ' + opt['acrattr'][0]
                        attr = colors[cn]
                        ch1 = opt.leftblankch
                    elif ch == '#':
                        ch1 = opt.midblankch

                    scr.addstr(grid_top+y, grid_left-1, ch1, attr)

                if x == len(row)-1:
                    if ch == '#':
                        ch2 = opt.midblankch
                        attr = color('blockattr', 'blockattr')
                    elif acursoracr and acursordown:
                        ch2 = opt.leftblankch
                        attr = color('curacrattr' if self.filldir == 'A' else 'curdownattr', 'blockattr')
                    elif acursoracr:
                        ch2 = opt.leftblankch
                        attr = color('acrattr', 'blockattr')
                    elif acursordown:
                        ch2 = opt.leftblankch
                        attr = color('downattr', 'blockattr')

                    scr.addstr(grid_top+y, grid_right-1, ch2, attr)

        if scr:
            scr.addstr(grid_top-1, grid_left, opt.topch*(self.ncols*2-1), opt.topattr)
            scr.addstr(grid_bottom,grid_left, opt.botch*(self.ncols*2-1), opt.rowattr | opt.botattr)

            scr.addstr(grid_top-1, grid_left-1, opt.ulch)
            scr.addstr(grid_bottom,grid_left-1, opt.blch)
            scr.addstr(grid_top-1, grid_right-1, opt.urch)
            scr.addstr(grid_bottom,grid_right-1, opt.brch)

            scr.move(0,0)

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

        # draw helpstr
        scr.addstr(h-1, 0, " Arrows move | Tab toggle direction | Ctrl+S save | Ctrl+Q quit | Ctrl+R reset", opt.helpattr)

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
            xd.grid[xd.cursor_y][xd.cursor_x] = UNFILLED
        elif k == ' ':  # erase and advance
            xd.grid[xd.cursor_y][xd.cursor_x] = UNFILLED
            xd.cursorMove(+1)
        elif k == 'KEY_DC':  # erase in place
            xd.grid[xd.cursor_y][xd.cursor_x] = UNFILLED
        elif k == '^S':
            xd.save(xd.fn)
            self.status('saved (%d%% solved)' % (xd.nsolved*100/xd.ncells))
        elif opt.hotkeys and k in xd.hotkeys:
            opt.cycle(xd.hotkeys[k])
        elif k.upper() in string.ascii_uppercase:
            xd.grid[xd.cursor_y][xd.cursor_x] = k.upper()
            xd.cursorMove(+1)



def main(scr):
    curses.use_default_colors()
    curses.raw()
    curses.meta(1)
    curses.curs_set(0)
    curses.mousemask(-1)

    plyr = CrosswordPlayer()
    xd = Crossword(sys.argv[1])
    while not plyr.play_one(scr, xd):
        pass

if '--clear' == sys.argv[1]:
    for fn in sys.argv[2:]:
        xd = Crossword(fn)
        xd.clear()
        xd.save(fn)
else:
    curses.wrapper(main)
