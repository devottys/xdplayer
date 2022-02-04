from collections import defaultdict
import json
import time


class AttrDict(dict):
    def __getattr__(self, k):
        return self.get(k, '')
    def __setattr__(self, k, v):
        self[k] = v


class Animation:
    def __init__(self, fp):
        self.frames = defaultdict(AttrDict)  # frame.id -> frame row
        self.groups = defaultdict(AttrDict)  # group.id -> group row
        self.load_from(fp)

    def iterdeep(self, rows, x=0, y=0, parents=None):
        'Walk rows deeply and generate (row, x, y, [ancestors]) for each row.'
        for r in rows:
            newparents = (parents or []) + [r]
            if r.type == 'frame': continue
            if r.ref:
                assert r.type == 'ref'
                g = self.groups[r.ref]
                yield from self.iterdeep(g.rows, x+r.x, y+r.y, newparents)
            else:
                yield r, x+r.x, y+r.y, newparents
                yield from self.iterdeep(r.rows or [], x+r.x, x+r.y, newparents)

    def load_from(self, fp):
        for line in fp.readlines():
            r = AttrDict(json.loads(line))
            if r.type == 'frame':
                self.frames[r.id].update(r)
            elif r.type == 'group':
                self.groups[r.id].update(r)

            f = self.frames[r.frame]
            if not f.rows:
                f.rows = [r]
            else:
                f.rows.append(r)

        self.total_ms = 0
        if self.frames:
            self.total_ms = sum(f.duration_ms or 0 for f in self.frames.values())

    def draw(self, scr, t, *args, x=0, y=0, loop=False, **kwargs):
        ms = int(t*1000)
        if loop:
            ms %= self.total_ms
        for f in self.frames.values():
            ms -= int(f.duration_ms or 0)
            if ms < 0:
                for r, dx, dy, _ in self.iterdeep(f.rows):
                    scr.addstr(y+dy, x+dx, r.text, scr.colors[r.color])

                return -ms/1000

        if loop:
            return -ms/1000


class AnimationMgr:
    def __init__(self):
        self.library = {}  # animation name -> Animation
        self.active = []  # list of (start_time, Animation, args, kwargs)

    def trigger(self, name, *args, **kwargs):
        self.active.append((time.time(), self.library[name], args, kwargs))

    def load(self, name, fp):
        self.library[name] = Animation(fp)

    def draw(self, scr, now):
        'Draw all active animations on *scr* at time *t*.  Return next t to be called at.'
        times = []
        done = []
        for row in self.active:
            startt, anim, args, kwargs = row
            nextt = anim.draw(scr, now-startt, *args, **kwargs)
            if nextt is None:
                done.append(row)
            else:
                times.append(startt+nextt)
        for row in done:
            self.active.remove(row)
        return min(times) if times else now
