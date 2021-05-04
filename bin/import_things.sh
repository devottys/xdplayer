#!/bin/bash

XDDIR='/opt/gxd'
BINDIR='/opt/xdplayer/bin'

for pub in $(find $XDDIR/* -type d) ; do
	if [[ $pub == *"2021"* ]]; then
		$BINDIR/xdimport.py $pub/*.xd
		echo "imported $pub"
	fi
done
