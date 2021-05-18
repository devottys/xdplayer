# $1 -> TEAM; makes all in-progress crosswords by that team read-only

TEAMDIR=/opt/teams/"$1"

for GUESS in $TEAMDIR/*.xd-guesses.jsonl; do
	chmod ugo-w $GUESS
done
