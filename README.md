# Crossword Player

- requires Python3, no external library dependencies
- works in the terminal using curses
- Usage: xdplayer.py <file.xd>

## Commands

- move cursor with arrows or click on a grid square or a clue

- A-Z: put answer in grid
- Backspace, Space, Delete: erase backward, forward, in-place
- TAB: change fill direction (across/down)

- Ctrl+S: save partial solution to `<file.xd.unsolved>` which may be restored later
- Ctrl+X: enable hotkeys to cycle through configurable options
- Ctrl+Q: quit without saving
