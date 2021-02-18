#!/bin/bash

USER="$1"
TEAMID="$2"
TEAMDIR="/opt/teams/$TEAMID"

XDDIR="/opt/gxd/"
XDDB="/opt/teams/xd.db"

mkdir -p $TEAMDIR
chown $USER $TEAMDIR
chmod ugo+rwx $TEAMDIR

echo -e "export TEAMID=$TEAMID\nexport TEAMDIR=$TEAMDIR\nexport XDDIR=$XDDIR\nexport XDDB=$XDDB\nexport PYTHONPATH=/opt/xdplayer" >> /home/$USER/.bashrc
