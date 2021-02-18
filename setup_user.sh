#!/bin/bash

TEAMID='teamxd'
TEAMDIR="/opt/teams/$TEAMID"

XDDIR='/opt/gxd/'
XDDB='/opt/teams/xd.db'

mkdir -p $TEAMDIR
ln -s $TEAMDIR ~/$TEAMID

echo -e "TEAMID=$TEAMID\nTEAMDIR=$TEAMDIR\nXDDIR=$XDDIR\nXDDB=$XDDB" >> ~/.bashrc
