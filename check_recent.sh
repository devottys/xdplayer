#!/bin/bash

for guesspath in $(find $TEAMDIR -name \*.jsonl -mmin +60) ; do
    guessfn=$(basename -- "$guesspath")
    xdid=${guessfn%%-guesses.jsonl}
    xdpath="$(./xdid2path.py $xdid)"
    ./xdiff.py $xdpath
done
