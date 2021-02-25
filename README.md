# Crossword Player

![xddemo](xddemo.gif)

- requires Python3, no external library dependencies
- works in the terminal using curses
- supports [.xd](http://saul.pw/data/) and .puz files
- Usage: python3 -m /path/to/xdplayer/xdplayer/ <file.xd>

We offer you two crosswords to play with in `samples/`.

## Commands

- move cursor with arrows or click on a grid square or a clue to jump to that location in the grid

- A-Z: put answer in grid
- Backspace, Space, Delete: erase backward, forward, in-place
- TAB: change fill direction (across/down)

xdplayer *autosaves* your progress. It will create and restore from a **crosswordfilename-guesses.jsonl**
in the current directory or in the location set by a `TEAMDIR` shell environment variable.


- Ctrl+S: commits to and checks your solution. The **crosswordfilename-guesses.jsonl** will be set to read-only, and "wrong" entries will be underlined.
- Ctrl+X: enable hotkeys to cycle through display configurable options. These options are all set at the top of `xdplayer/__init__.py`, should you wish to modify them.
- Ctrl+Q: quit program.
