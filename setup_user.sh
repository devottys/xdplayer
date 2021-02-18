#!/bin/bash

TEAMID='teamxd'
TEAMDIR='/opt/teams/teamxd'
XDDIR='/opt/gxd/'
XDDB='/opt/teams/xd.db'

ln -s $TEAMDIR ~/$TEAMID
# user will need to have access to github for this to work
git clone git@github.com:devotees/xdplayer.git

echo -e "TEAMID=$TEAMID\nTEAMDIR=$TEAMDIR\nXDDIR=$XDDIR\nXDDB=$XDDB" >> ~/.bashrc
