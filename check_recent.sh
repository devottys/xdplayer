#!/bin/bash

BINDIR=/opt/xdplayer

cd /opt/teams/

for TEAMID in * ; do
  for guesspath in $(find $TEAMDIR -name \*.jsonl -mmin -60) ; do
    guessfn=$(basename -- "$guesspath")
    xdid=${guessfn%%.xd-guesses.jsonl}
    xdpath="$(./xdid2path.py $xdid)"
    TEAMDIR="/opt/teams/$TEAMID" $BINDIR/xdiff.py $xdpath
  done
done
