# Deployment

## Environment Variables

    TEAMID=ourteam
    TEAMDIR=/opt/teams/$TEAMID
    XDDIR=/opt/gxd/
    XDDB=/opt/teams/xd.db

## Scripts to run

1. `xdimport.py <path/to/solved/**.xd>`

Add given xd files to $XDDB xdmeta table.

2. `xdlauncher.py`

Browse list of all puzzles, including stats for $TEAMID.
Press Enter to launch xdplayer for the current crossword.

3. `xdplayer.py <path/to/solved/xdid.xd>`

Interactively solve given .xd file.  Player input is appended to `$TEAMDIR/xdid-guesses.jsonl`.

4. `check_recent.sh`

Run xdiff.py for every recently modified `<xdid>-guesses.jsonl` in $TEAMDIR.
Must be run separately for every team.

5. `xdiff.py <path/to/solved/xdid.xd>`

Compare given golden .xd, with cleared .xd plus replayed `$TEAMDIR/xdid-guesses.jsonl`.

## Helpers

- `xdid2path.py <xdid>`: get solved path from xdid
