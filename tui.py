import curses

colors = None

def getkeystroke(scr):
    k = None
    while k is None:
        try:
            k = scr.get_wch()
        except curses.error:
            pass
    if isinstance(k, str):
        if ord(k) >= 32 and ord(k) != 127:  # 127 == DEL or ^?
            return k
        k = ord(k)
    return curses.keyname(k).decode('utf-8')

class ColorMaker:
    def __init__(self):
        self.attrs = {}
        self.color_attrs = {}


    def get_color(self, fg, bg):
        if not self.color_attrs:
            self.color_attrs[''] = curses.color_pair(0)

        if not self.color_attrs.get((fg,bg), None):
            try:
                c = len(self.color_attrs)
                curses.init_pair(c, fg, bg)
                self.color_attrs[(fg,bg)] = curses.color_pair(c)
            except curses.error as e:
                pass # curses.init_pair gives a curses error on Windows
        return self.color_attrs[(fg,bg)]

    def __getitem__(self, colornamestr):
        return self._colornames_to_cattr(colornamestr)

    def to_name(self, attr):
        for k, v in self.color_attrs.items():
            if v == attr:
                return k
        return 'unknown'

    def _colornames_to_cattr(self, colornamestr):
        if not colornamestr:
            return 0
        fgbg = [0,0]
        attr = 0  # other attrs
        bg = False
        for colorname in colornamestr.split(' '):
            if colorname == 'on': bg = True
            elif hasattr(curses, 'A_'+colorname.upper()):
                attr |= getattr(curses, 'A_'+colorname.upper())
            elif not fgbg[bg]:
                if colorname.isdigit():
                    fgbg[bg] = int(colorname)
                else:
                    fgbg[bg] = getattr(curses, 'COLOR_'+colorname.upper(), 0)
        return attr | self.get_color(*fgbg)


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
        except KeyError as e:
            if k.startswith("__"):
                raise AttributeError

            return 0

    def __dir__(self):
        return self.keys()

    def cycle(self, k):
        self[k] = self[k][1:] + [self[k][0]]


colors = ColorMaker()
