#!/bin/bash

BINDIR=/opt/xdplayer

TEAMDIR=/opt/teams

for TEAMID in * ; do
  for guesspath in $(find $TEAMDIR/$TEAMID -name \*.jsonl -mmin -60) ; do
    guessfn=$(basename -- "$guesspath")
    xdid=${guessfn%%.xd-guesses.jsonl}
    xdpath="$($BINDIR/xdid2path.py $xdid)"
    TEAMDIR="$TEAMDIR/$TEAMID" $BINDIR/xdiff.py $xdpath
  done
done
