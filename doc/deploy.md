# Overview of scripts

## Scripts to run

1. (admin) `bin/xdimport.py <path/to/solved/**.xd>`

Add given xd files to $XDDB xdmeta table.

2. (player) `bin/xdlauncher.py`

Browse list of all puzzles, including stats for $TEAMID.
Press Enter to launch xdplayer for the current crossword.

3. (xdlauncher) `python3 -m xdplayer.py <path/to/solved/xdid.xd>`

Interactively solve given .xd file.  Player input is appended to `$TEAMDIR/xdid-guesses.jsonl`.

4. (cron) `bin/check_recent.sh`

Run xdiff.py for every recently modified `<xdid>-guesses.jsonl` in $TEAMDIR.
Must be run separately for every team.

5. (check recent) `bin/xdiff.py <path/to/solved/xdid.xd>`

Compare given golden .xd, with cleared .xd plus replayed `$TEAMDIR/xdid-guesses.jsonl`.

## Helpers

- `bin/xdid2path.py <xdid>`: get solved path from xdid

# Deployment

## 1. admin: install server

- launch instance, login as root
- create ssh key pair: `ssh-keygen`
- add `.ssh/id_rsa.pub` to github.com/saulpw/xdplayer and gxd repo

    mkdir -p /opt/teams



## 2. admin: add crosswords

a.  download software

    git clone https://github.com/devotees/xdplayer.git /opt/xdplayer

    git clone gxd /opt/gxd
        - this takes a bit, bc it needs to resolve all the deltas

    - make sure it can be used by other users: chmod -R o+rx /opt/gxd

    pip3 install git+https://github.com/saulpw/visidata.git@develop

        - you may need to ensure python3-pip is installed on the machine

    ./xdimport.py /opt/gxd/**.xd

        - only the crosswords you want to import

    chmod 0644 /opt/teams/xd.db


b. add cronjob to check solutions hourly

    XDDIR='/opt/gxd' XDDB='/opt/teams/xd.db' /opt/xdplayer/bin/check_recent.sh

- make sure all of the paths within it are correct
- make sure cron can find the various files in xdplayer
- include environment variables:


c. cronjob to git pull gxd daily

## 3. admin: add user

    adduser <username>

        - use apg to generate password

    /opt/xdplayer/setup_user username teamid
        - add ssh key

    - chsh /opt/xdplayer/xdlauncher.py


   - shell is vdlauncher.py

