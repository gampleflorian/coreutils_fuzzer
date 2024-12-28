#!/bin/bash
TARGET_FN=$1
if [[ -f "$FILE" ]]; then
	echo "$TARGET_FN does not exist"
	exit 1
fi

while read target; do
	TMP_FUZZ_DATA="$PWD/fuzz_data_tmp/$target"
	H_OUT_DIR="$PWD/fuzzings/$target/min"
	T_OUT_DIR="/fuzzings/$target/min"
	T_INP_DIRS="$(find fuzzings/$target/out -type d -name queue -exec echo -n /{}" " \; )"
	echo "--------------------------------------------------------------------------------"
	echo "Target    : $target"
	echo "Output dir: $H_OUT_DIR:$T_OUT_DIR"
	echo "Input dirs: $T_INP_DIRS"
	echo "Fuzz data : $TMP_FUZZ_DATA"
	mkdir -p $TMP_FUZZ_DATA
	mkdir -p $H_OUT_DIR
	cp $PWD/fuzz_data/make_check/processed/"$target".fileinput $TMP_FUZZ_DATA
	cp $PWD/fuzz_data/make_check/processed/"$target".envmeta $TMP_FUZZ_DATA
	cp $PWD/run_cmin_multi.py $TMP_FUZZ_DATA
	docker run --rm \
		-e OUTP_DIR=$T_OUT_DIR \
		-e INP_DIRS="$T_INP_DIRS" \
		-e FUZZ_TARGET=$target \
		-v $TMP_FUZZ_DATA:/fuzz_data \
		-v $PWD/fuzzings/$target:/fuzzings/$target \
		-t coreutils_argenv_fuzz:latest \
		/bin/bash -c 'python3 /fuzz_data/run_cmin_multi.py -t "$FUZZ_TARGET" -e /fuzz_data -nt 16 --tdir /coreutils_afpp/bin/ -i $INP_DIRS -o $OUTP_DIR'
done < $TARGET_FN
