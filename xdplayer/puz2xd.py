#!/usr/bin/env python3

import sys
from .puz import read as puz_read

BLOCK = '#'

def gen_xd(puzfn, clear=True):
    p = puz_read(puzfn)

    yield 'Title: ' + p.title.strip()
    yield 'Author: ' + p.author.strip()
    yield 'Copyright: ' + p.copyright.strip()
    yield ''
    yield ''

    grid = []
    across = {}
    down = {}

    for i in range(0, len(p.solution), p.width):
        row = [ BLOCK if x in ':.' else ('.' if clear else x) for x in p.solution[i:i+p.width]]
        grid.append(''.join(row))

    yield from grid
    yield ''
    yield ''

    def is_block(x, y):
         return x < 0 or y < 0 or x >= p.width or y >= p.height or grid[y][x] in BLOCK

    i = 0   # index into p.clues
    n = 0   # printed clue number
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            start_across = is_block(x-1, y) and not is_block(x, y) and not is_block(x+1, y)
            start_down = is_block(x, y-1) and not is_block(x, y) and not is_block(x, y+1)

            if start_across or start_down:
                n += 1
            if start_across:
                across[n] = p.clues[i]
                i += 1
            if start_down:
                down[n] = p.clues[i]
                i += 1

    for k, v in across.items():
        yield f'A{k}. {v}'

    yield ''

    for k, v in down.items():
        yield f'D{k}. {v}'


if __name__ == '__main__':
    for line in gen_xd(sys.argv[1], clear=True):
        print(line)
