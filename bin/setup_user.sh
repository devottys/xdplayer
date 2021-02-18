#!/bin/bash

USER="$1"
TEAMID="$2"
TEAMDIR="/opt/teams/$TEAMID"

XDDIR="/opt/gxd/"
XDDB="/opt/teams/xd.db"

mkdir -p $TEAMDIR
chown $USER $TEAMDIR
chmod ugo+rwx $TEAMDIR

cat <<-EOF >> /home/$USER/.bashrc
    export TEAMID=$TEAMID
    export TEAMDIR=$TEAMDIR
    export XDDIR=$XDDIR
    export XDDB=$XDDB
    export PYTHONPATH=/opt/xdplayer
EOF
