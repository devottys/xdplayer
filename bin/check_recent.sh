#!/bin/bash

BINDIR=/opt/xdplayer/bin

TEAMDIR=/opt/teams

for TEAMID in $TEAMDIR/* ; do
  for guesspath in $(find $TEAMID -name \*.jsonl -mmin -60) ; do
    guessfn=$(basename -- "$guesspath")
    xdid=${guessfn%%.xd-guesses.jsonl}
    xdpath="$($BINDIR/xdid2path.py $xdid)"
    TEAMDIR="$TEAMID" $BINDIR/xdiff.py $xdpath
  done
done
