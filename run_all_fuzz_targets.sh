while read i; do
	echo $i
	docker run --rm -e FUZZ_TARGET=$i -v $PWD:/xxx -it coreutils_argenv_fuzz:latest /bin/bash -c 'echo python3 /xxx/run_fuzzer.py -t "$FUZZ_TARGET" -e /xxx/fuzz_data/make_check/processed -f /xxx/fuzzings -nt 16 --tdir /coreutils_afpp/bin/ --lafdir /coreutils_afpp_laf/bin --rqdir /coreutils_afpp_rq/bin -x 2700'
done < coreutil.targets

