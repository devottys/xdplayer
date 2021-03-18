#!/usr/bin/env python3

from unittest import mock
import sys
import json
import os
import stat
import os.path
import textwrap
import getpass
import time
import string
import curses
from pathlib import Path
from collections import namedtuple, defaultdict

from .tui import *
from .puz2xd import gen_xd
from .ddwplay import AnimationMgr

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
    pc1attr = ['121 on black'],
    pc2attr = ['153 on black'],
    pc3attr = ['220 on black'],
    pc4attr = ['13 on black'],
    pc5attr = ['47 on black'],

    helpattr = ['bold 109', 'bold 108', ],
    clueattr = ['7'],

    sepch = list(' '+c+' ' for c in '·‧˙|.□-∙•╺ '),
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
    'Return curses color code for {fg_coloropt} colored character on a {bg_coloropt} colored background.'
    return colors['%s on %s' % (opt[fg_coloropt+'attr'][0], opt[bg_coloropt+'attr'][0])]


def log(*args):
    print(*args, file=sys.stderr)
    sys.stderr.flush()


class Crossword:
    def __init__(self, fn):
        if fn.endswith('.puz'):
            self.fn = fn[:-4] + '.xd'
            self.load_puz(fn)
        else:
            self.fn = fn
            self.load()

        self.filldir = 'A'
        self.cursor_x = 0
        self.cursor_y = 0
        self.lastpos = 0  # for incremental replay_guesses

        self.clue_layout = {}

        self.move_grid(3, len(self.meta))

    def load(self):
        self.load_xd(open(self.fn).read())

    def load_puz(self, fn):
        self.load_xd('\n'.join(gen_xd(fn)))

    def load_xd(self, contents):
        metastr, gridstr, cluestr, *notestr = contents.split('\n\n\n')

        self.meta = {}
        for line in metastr.splitlines():
            k, v = line.split(':', maxsplit=1)
            self.meta[k.strip()] = v.strip()

        self.solution = gridstr.splitlines()

        self.grid = [[x for x in row] for row in self.solution]
        self.guesser = defaultdict(str)
        self.guessercolors = defaultdict(str)

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

    def grade():
        'Return the number of correct tiles'
        xd1 = Crossword(self.fn)
        xd2 = Crossword(self.fn)
        xd2.clear()
        xd2.replay_guesses()
        return sum(1 for y, r in enumerate(xd2.grid) for x, c in enumerate(r) if c != '#' and c.upper() == xd1.grid[y][x].upper())

    @property
    def guessfn(self):
        xdid = Path(self.fn).stem
        return Path(os.getenv('TEAMDIR', '.'))/(xdid+'.xd-guesses.jsonl')

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

    @property
    def checkable(self):
        try:
            return not (os.stat(self.guessfn).st_mode & stat.S_IWUSR)
        except FileNotFoundError:
            return False

    def mark_done(self):
        os.chmod(self.guessfn, os.stat(self.guessfn).st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))

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
        'Is the cell located in the current down cursor (down=true) or across cursor (down=False)?'
        w = self.pos[(y, x)]
        if not w: return False
        cursor_words = self.pos[(self.cursor_y, self.cursor_x)]
        if not cursor_words: return False
        return sorted(cursor_words)[down] == sorted(w)[down]

    def charcolor(self, y, x, half=True):
        'Return the curses color key for the character at pos y, x (to be used in half() or opt[key + "attr"]).'
        ch = self.cell(y, x)
        if ch == '#':
            return 'block'
        dcurs = self.is_cursor(y, x, down=True)
        acurs = self.is_cursor(y, x, down=False)
        if acurs and dcurs: return 'curacr' if self.filldir == 'A' else 'curdown' # cell is intersect cursor, colored depending on current filldir
        if acurs: return 'acr' # cell is across cursor, but not intersect
        if dcurs: return 'down' # cell is down cursor, but not intersect

    def draw(self, scr):
        if not scr:
            scr = mock.MagicMock(__bool__=mock.Mock(return_value=False))

        h, w = scr.getmaxyx()

        if h < self.nrows+4 or w < self.ncols+20:
            raise Exception(f'terminal is  {w}x{h}; need {self.ncols+20}x{self.nrows+4}')
        self.move_grid(3, max(0, min(h-self.nrows-2, len(self.meta))))

        # draw meta
        y = 0
        for k, v in self.meta.items():
            if y >= grid_top-1:
                break
            scr.addstr(y, 1, '%10s: %s' % (k, v))
            y += 1


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

                attr1 = colors[self.guessercolors.get(self.guesser[(x,y)], 'white') + ' on black']

                if clr in "acr down curacr curdown".split():
                    attr1 = colors[opt[clr+'attr'][0] + ' reverse']
                elif ch != '#':
                    attr1 = getattr(opt, self.guessercolors.get(self.guesser[(x,y)], 'fgbg')+'attr')
                    if self.checkable and self.solution[y][x] != ch:
                        attr1 |= curses.A_UNDERLINE
                    clr = None
                elif clr:
                    attr1 = getattr(opt, clr+'attr')

                if ch == UNFILLED:
                    ch1 = opt.unsolved_char
                elif ch == '#':
                    ch1 = opt.midblankch
                    attr1 = opt.blockattr

                if clr or fclr:
                    attr2 = half(clr or 'bg', fclr or 'bg')  # colour of ch2
                else:
                    attr2 = colors['white on black']


                if x >= 0:
                    scr.addstr(grid_top+y, grid_left+x*2, ch1, attr1)
                scr.addstr(grid_top+y, grid_left+x*2+1, ch2, attr2)

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

        # draw solver list
        for i, (user, color) in enumerate(self.guessercolors.items()):
            s = '%s (%d%%)' % (user, sum(1 for (x,y), u in self.guesser.items() if u == user and self.cell(y, x) != UNFILLED)*100/self.ncells)
            scr.addstr(grid_bottom+i+1, grid_left, s, getattr(opt, color+'attr'))

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
        if self.grid[self.cursor_y][self.cursor_x] == ch:
            return

        with open(self.guessfn, 'a') as fp:
            fp.write(json.dumps(dict(x=self.cursor_x, y=self.cursor_y, ch=ch, user=os.getenv('USER', getpass.getuser()))) + '\n')

        self.grid[self.cursor_y][self.cursor_x] = ch

    def replay_guesses(self):
        if not os.path.exists(self.guessfn):
            return

        with open(self.guessfn) as fp:
            fp.seek(self.lastpos)
            for line in fp.read().splitlines():
                d = json.loads(line)
                x, y, ch = d['x'], d['y'], d['ch']
                self.grid[y][x] = ch
                user = d.get('user', '')
                self.guesser[(x,y)] = user
                if user and user not in self.guessercolors:
                    self.guessercolors[user] = 'pc%d' % (len(self.guessercolors)+1)


            self.lastpos = fp.tell()

        if not os.path.exists(self.guessfn):
            Path(self.guessfn).touch(0o777)


class CrosswordPlayer:
    def __init__(self):
        self.statuses = []
        self.xd = None
        self.n = 0
        self.startt = time.time()
        self.lastpos = 0
        self.animmgr = AnimationMgr()

        self.animmgr.load('bouncyball', open('bouncyball.ddw'))


    def status(self, s):
        self.statuses.append(s)

    def play_one(self, scr, xd):
        h, w = scr.getmaxyx()
        xd.draw(scr)
        if self.statuses:
            scr.addstr(h-2, clue_left, self.statuses.pop())
        solvedamt = '%d/%d' % (xd.nsolved, xd.ncells)

        # draw time on bottom
        secs = time.time()-self.startt
        timestr = '% 2d' % (secs//3600) if secs > 3600 else '  '
        timestr += ' ' if int(secs) % 5 == 0 else ':'
        timestr += '%02d' % ((secs % 3600)//60)

        botline = [timestr, solvedamt] + list("Tab toggle direction | Ctrl+Q quit | Ctrl+S finalize".split(' | '))

        # draw helpstr
        scr.addstr(h-1, 4, opt.sepch.join(botline), opt.helpattr)

        if opt.hotkeys:
            xd.draw_hotkeys(scr)
            scr.addstr(1, w-20, f'{h}x{w}')

        now = time.time()
        nextt = self.animmgr.draw(scr, now)
        timeout = int((nextt-now)*1000)
        if timeout < 0:
            self.status(f'{timeout}')
            scr.timeout(1)
        else:
            scr.timeout(timeout)

        # if crossword is complete, check correct cell count
        if xd.nsolved == xd.ncells:
            correct = xd.grade()

            if correct == xd.ncells:
                xd.mark_done()
                self.status('puzzle complete! nicely done')
            else:
                self.status(f'no cigar! {xd.ncells - correct} are wrong')

        k = getkeystroke(scr)
        scr.erase()
        if k == '^Q': return True
        if not k: return False
        if k == 'KEY_RESIZE': h, w = scr.getmaxyx()
        if k == '^L': scr.clear()

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
        elif k == '^S': xd.mark_done(); self.status('puzzle submitted!')
        elif k == '^X':
            opt.hotkeys = not opt.hotkeys
            return
        elif k == '^R':
            self.animmgr.trigger('bouncyball', x=26, y=2, loop=True)

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
        elif k.upper() in (string.ascii_uppercase+string.digits):
            xd.setAtCursor(k.upper())
            xd.cursorMove(+1)


def main_player(scr):
    curses.use_default_colors()
    curses.raw()
    curses.meta(1)
    curses.curs_set(0)
    curses.mousemask(-1)

    plyr = CrosswordPlayer()
    xd = Crossword(sys.argv[1])
    xd.clear()
    xd.replay_guesses()
    while True:
        try:
            if plyr.play_one(scr, xd):
                break
        except PermissionError as e:
            plyr.status('puzzle submitted! submitted puzzles cannot be changed')

        xd.replay_guesses()  # from other player(s)
