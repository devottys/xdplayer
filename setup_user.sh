#!/bin/bash

USER="$1"
TEAMID="$2"
TEAMDIR="/opt/teams/$TEAMID"

XDDIR="/opt/gxd/"
XDDB="/opt/teams/xd.db"

mkdir -p $TEAMDIR
chown $USER $TEAMDIR
chmod ugo+rwx $TEAMDIR

echo -e "TEAMID=$TEAMID\nTEAMDIR=$TEAMDIR\nXDDIR=$XDDIR\nXDDB=$XDDB" >> $home/$USER/.bashrc
