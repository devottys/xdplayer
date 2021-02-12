import curses

colors = None

def getkeystroke(scr):
    k = scr.get_wch()
    if isinstance(k, str):
        if ord(k) >= 32 and ord(k) != 127:  # 127 == DEL or ^?
            return k
        k = ord(k)
    return curses.keyname(k).decode('utf-8')

class ColorMaker:
    def __init__(self):
        global colors
        colors = self
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


class OptionsObject(dict):
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
