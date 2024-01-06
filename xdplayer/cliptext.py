from contextlib import suppress
import curses
import functools
import unicodedata
import sys

disp_unprintable = '·' # substitute character for unprintables
disp_ambig_width = 1   # width to use for unicode chars marked ambiguous
disp_truncator = '…' # indicator that the contents are only partially visib
disp_oddspace = '\u00b7' # displayable character for odd whitespace

disp_column_fill = ' '

class EscapeException(BaseException):
    'Inherits from BaseException to avoid "except Exception" clauses. Do not use a blanket "except:" or the task will be uncancelable.'
    pass

### Curses helpers

# ZERO_WIDTH_CF is from wcwidth:
# NOTE: created by hand, there isn't anything identifiable other than
# general Cf category code to identify these, and some characters in Cf
# category code are of non-zero width.
# Also includes some Cc, Mn, Zl, and Zp characters
ZERO_WIDTH_CF = set(map(chr, [
    0,       # Null (Cc)
    0x034F,  # Combining grapheme joiner (Mn)
    0x200B,  # Zero width space
    0x200C,  # Zero width non-joiner
    0x200D,  # Zero width joiner
    0x200E,  # Left-to-right mark
    0x200F,  # Right-to-left mark
    0x2028,  # Line separator (Zl)
    0x2029,  # Paragraph separator (Zp)
    0x202A,  # Left-to-right embedding
    0x202B,  # Right-to-left embedding
    0x202C,  # Pop directional formatting
    0x202D,  # Left-to-right override
    0x202E,  # Right-to-left override
    0x2060,  # Word joiner
    0x2061,  # Function application
    0x2062,  # Invisible times
    0x2063,  # Invisible separator
]))

def wcwidth(cc, ambig=1):
        if cc in ZERO_WIDTH_CF:
            return 1
        eaw = unicodedata.east_asian_width(cc)
        if eaw in 'AN':  # ambiguous or neutral
            if unicodedata.category(cc) == 'Mn':
                return 1
            else:
                return ambig
        elif eaw in 'WF': # wide/full
            return 2
        elif not unicodedata.combining(cc):
            return 1
        return 0

# editline helpers

class EnableCursor:
    def __enter__(self):
        with suppress(curses.error):
            curses.mousemask(0)
            curses.curs_set(1)

    def __exit__(self, exc_type, exc_val, tb):
        with suppress(curses.error):
            curses.curs_set(0)
            curses.mousemask(curses.MOUSE_ALL if hasattr(curses, "MOUSE_ALL") else 0xffffffff)


def until_get_wch(scr):
    'Ignores get_wch timeouts'
    ret = None
    while not ret:
        try:
            ret = scr.get_wch()
        except curses.error:
            pass

    return ret


def splice(v:str, i:int, s:str):
    'Insert `s` into string `v` at `i` (such that v[i] == s[0]).'
    return v if i < 0 else v[:i] + s + v[i:]


def clean_printable(s):
    'Escape unprintable characters.'
    return ''.join(c if c.isprintable() else disp_unprintable for c in str(s))


def delchar(s, i, remove=1):
    'Delete `remove` characters from str `s` beginning at position `i`.'
    return s if i < 0 else s[:i] + s[i+remove:]


def editline(scr, y, x, w, i=0, attr=curses.A_NORMAL, value='', fillchar=' ', truncchar='-', unprintablechar='.', completer=lambda text,idx: None, history=[], display=True, updater=lambda val: None, bindings={}, clear=True):
  '''A better curses line editing widget.
  If *clear* is True, clear whole editing area before displaying.
  '''
  with EnableCursor():
    ESC='^['
    TAB='^I'

    insert_mode = True
    first_action = True
    v = str(value)  # value under edit

    # i = 0  # index into v, initial value can be passed in as argument as of 1.2
    if i != 0:
        first_action = False

    left_truncchar = right_truncchar = truncchar

    def find_nonword(s, a, b, incr):
        if not s: return 0
        a = min(max(a, 0), len(s)-1)
        b = min(max(b, 0), len(s)-1)

        if incr < 0:
            while not s[b].isalnum() and b >= a:  # first skip non-word chars
                b += incr
            while s[b].isalnum() and b >= a:
                b += incr
            return min(max(b, -1), len(s))
        else:
            while not s[a].isalnum() and a < b:  # first skip non-word chars
                a += incr
            while s[a].isalnum() and a < b:
                a += incr
            return min(max(a, 0), len(s))


    while True:
        updater(v)

        if display:
            dispval = clean_printable(v)
        else:
            dispval = '*' * len(v)

        dispi = i  # the onscreen offset within the field where v[i] is displayed
        if len(dispval) < w:  # entire value fits
            dispval += fillchar*(w-len(dispval)-1)
        elif i == len(dispval):  # cursor after value (will append)
            dispi = w-1
            dispval = left_truncchar + dispval[len(dispval)-w+2:] + fillchar
        elif i >= len(dispval)-w//2:  # cursor within halfwidth of end
            dispi = w-(len(dispval)-i)
            dispval = left_truncchar + dispval[len(dispval)-w+1:]
        elif i <= w//2:  # cursor within halfwidth of beginning
            dispval = dispval[:w-1] + right_truncchar
        else:
            dispi = w//2  # visual cursor stays right in the middle
            k = 1 if w%2==0 else 0  # odd widths have one character more
            dispval = left_truncchar + dispval[i-w//2+1:i+w//2-k] + right_truncchar

        prew = clipdraw(scr, y, x, dispval[:dispi], attr, w, clear=clear)
        clipdraw(scr, y, x+prew, dispval[dispi:], attr, w-prew+1, clear=clear)
        scr.move(y, x+prew)
        ch = scr.getkeystroke()
        if ch == '':                               continue
        elif ch == 'KEY_IC':                       insert_mode = not insert_mode
        elif ch == '^A' or ch == 'KEY_HOME':       i = 0
        elif ch == '^B' or ch == 'KEY_LEFT':       i -= 1
        elif ch in ('^C', '^Q', ESC):              raise EscapeException(ch)
        elif ch == '^D' or ch == 'KEY_DC':         v = delchar(v, i)
        elif ch == '^E' or ch == 'KEY_END':        i = len(v)
        elif ch == '^F' or ch == 'KEY_RIGHT':      i += 1
        elif ch == '^G':                           vd.show_help = not vd.show_help; continue # not a first keypress
        elif ch in ('^H', 'KEY_BACKSPACE', '^?'):  i -= 1; v = delchar(v, i)
        elif ch in ['^J', '^M']:                   break  # ENTER to accept value
        elif ch == '^K':                           v = v[:i]  # ^Kill to end-of-line
        elif ch == '^O':                           v = vd.launchExternalEditor(v)
        elif ch == '^R':                           v = str(value)  # ^Reload initial value
        elif ch == '^T':                           v = delchar(splice(v, i-2, v[i-1:i]), i)  # swap chars
        elif ch == '^U':                           v = v[i:]; i = 0  # clear to beginning
        elif ch == '^V':                           v = splice(v, i, until_get_wch(scr)); i += 1  # literal character
        elif ch == '^W':                           j = find_nonword(v, 0, i-1, -1); v = v[:j+1] + v[i:]; i = j+1  # erase word
        elif ch == '^Y':                           v = splice(v, i, str(vd.memory.clipval))
        elif ch == '^Z':                           suspend()
        # CTRL+arrow
        elif ch == 'kLFT5':                        i = find_nonword(v, 0, i-1, -1)+1; # word left
        elif ch == 'kRIT5':                        i = find_nonword(v, i+1, len(v)-1, +1)+1; # word right
        elif ch == 'kUP5':                         pass
        elif ch == 'kDN5':                         pass
        elif history and ch == 'KEY_UP':           v, i = history_state.up(v, i)
        elif history and ch == 'KEY_DOWN':         v, i = history_state.down(v, i)
        elif ch in bindings:                       v, i = bindings[ch](v, i)
        elif len(ch) > 1:                          pass
        else:
            if first_action:
                v = ''
            if insert_mode:
                v = splice(v, i, ch)
            else:
                v = v[:i] + ch + v[i+1:]

            i += 1

        if i < 0: i = 0
        # v may have a non-str type with no len()
        v = str(v)
        if i > len(v): i = len(v)
        first_action = False

    return type(value)(v)

@functools.lru_cache(maxsize=100000)
def _dispch(c, oddspacech=None, combch=None, modch=None):
    ccat = unicodedata.category(c)
    if ccat in ['Mn', 'Sk', 'Lm']:
        if unicodedata.name(c).startswith('MODIFIER'):
            return modch, 1
    elif c != ' ' and ccat in ('Cc', 'Zs', 'Zl', 'Cs'):  # control char, space, line sep, surrogate
        return oddspacech, 1
    elif c in ZERO_WIDTH_CF:
        return combch, 1

    return c, dispwidth(c)


@functools.lru_cache(maxsize=100000)
def _clipstr(s, dispw, trunch='', oddspacech='', combch='', modch=''):
    '''Return clipped string and width in terminal display characters.
    Note: width may differ from len(s) if East Asian chars are 'fullwidth'.'''
    w = 0
    ret = ''

    trunchlen = dispwidth(trunch)
    for c in s:
        newc, chlen = _dispch(c, oddspacech=oddspacech, combch=combch, modch=modch)
        if newc:
            ret += newc
            w += chlen
        else:
            ret += c
            w += dispwidth(c)

        if dispw and w > dispw-trunchlen+1:
            ret = ret[:-2] + trunch # replace final char with ellipsis
            w += trunchlen
            break

    return ret, w

#@drawcache
def clipstr(s, dispw, truncator=None, oddspace=None):
    return _clipstr(s, dispw,
            trunch=disp_truncator if truncator is None else truncator,
            oddspacech=disp_oddspace if oddspace is None else oddspace,
            modch='',
            combch='')

@functools.lru_cache(maxsize=100000)
def dispwidth(ss, maxwidth=None):
    'Return display width of string, according to unicodedata width and options.disp_ambig_width.'
    w = 0

    for cc in ss:
        w += wcwidth(cc, disp_ambig_width)
        if maxwidth and w > maxwidth:
            break
    return w


def clipdraw(scr, y, x, s, attr, w=None, clear=True, rtl=False, **kwargs):
    'Draw string `s` at (y,x)-(y,x+w) with curses attr, clipping with ellipsis char.  if rtl, draw inside (x-w, x).  If *clear*, clear whole editing area before displaying. Returns width drawn (max of w).'
    if scr:
        _, windowWidth = scr.getmaxyx()
    else:
        windowWidth = 80
    dispw = 0
    try:
        if w is None:
            w = dispwidth(s, maxwidth=windowWidth)
        w = min(w, (x-1) if rtl else (windowWidth-x-1))
        if w <= 0:  # no room anyway
            return 0
        if not scr:
            return w

        # convert to string just before drawing
        clipped, dispw = clipstr(s, w, **kwargs)
        if rtl:
            # clearing whole area (w) has negative display effects; clearing just dispw area is useless
#            scr.addstr(y, x-dispw-1, disp_column_fill*dispw, attr)
            scr.addstr(y, x-dispw-1, clipped, attr)
        else:
            if clear:
                scr.addstr(y, x, disp_column_fill*w, attr)  # clear whole area before displaying
            scr.addstr(y, x, clipped, attr)
    except Exception as e:
        raise

    return dispw

