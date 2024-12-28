#!/bin/bash
TARGET_FN=$1
if [[ -f "$FILE" ]]; then
	echo "$TARGET_FN does not exist"
	exit 1
fi

OUT_DIR=$2
if [[ ! -d "$OUT_DIR" ]]; then
	echo "$OUT_DIR does not exist"
	exit 1
fi

while read t; do
	echo $t
	HAS_FILE_INPUT=$(man $t | grep '\[OPTION\]... \[FILE\]...')
	if [ -z "$HAS_FILE_INPUT" ]; then
		echo -n "HAS_FILE_INPUT=0" > $OUT_DIR/"$t".fileinput
	else
		echo -n "HAS_FILE_INPUT=1" > $OUT_DIR/"$t".fileinput
	fi
done < $TARGET_FN


