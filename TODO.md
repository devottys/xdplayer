# TODO

## deployment

- each player has their own unix username
- use unix username/password auth mechanism
   - can we use a login which prints some ** (even if wrong number) on password


### processes to create/document


4. user: login/play crossword
5. user: add ssh key

undocumented, one time:

- move our guesses files to /opt/teams/teamxd

### deployment tests

ssh username@dev.saul.pw

### deployment features

- web server for static site
- websocket that forwards a pty (including login)
   - cookie to stay logged in


## xdlauncher features

- lobby/leaderboard
  - generate status/leaderboard from db
    - generate .tsv or otherwise to present in lobby
   - generate static .html, cp to static site

## xdplayer features

- different color grid/blocks (lighter gray?)
- enter arbitrary string for rebus (number, symbol, unicode, multiple letters)


# blog post

1. been wanting multiplayer crossword, pandemic
 - ascii.town
 - inspired by cursewords
   - numbering in grid is very clever
   - blocks don't fill their squares
   - and only one clue visible at a time

2. decided to play with a more compact layout
   - half-blocks to fill out blocks
   - fit in 80x25, and everything that stemmed from that limitation
   - read .xd format

3. Made some design decisions
   - 2x1 instead of 4x2 is properly proportioned but doesn't spend any space on interior box-drawing
   chars
      - though unfortunately this leaves no room for superscript numbers like in cursewords, alas
   - beautiful software
   - contextual clues on side
      - note color matching indication of direction on board and clue
      - shoutout to python stdlib textwrap which continues to be very useful for quickly making polished terminal 

4. Experimentation
   - easy options framework (borrowed from VisiData)
      - one line to define (almost as easy to create as a global variable)
   - status bar important for minimalist print debugging
      -  print = log to file

   - Ctrl+X to set them via hotkeys (simple debug interface, took 10 minutes to write)
   - keep option names regular
     - e.g. all colors end in 'attr' which came in handy when we wanted to have the options object automatically turn them in to curses attributes from a color description ("242 red on white")
   - 
5. where to play sample
   - ssh sample@xd.saul.pw
   - screenshot -- cursewords vs xdplayer
   - any other prior art for terminal-based crossword solving?
   - in terminal?


