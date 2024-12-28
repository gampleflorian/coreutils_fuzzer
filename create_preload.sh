for i in $(find /coreutils_preload/bin -type f -executable -printf "%f\n"); do
	HAS_FILE_INPUT=$(grep '\[\\fI\\,OPTION\\/\\fR\]... \[\\fI\\,FILE\\/\\fR\]' /coreutils_preload/share/man/man1/"$i".1)
	if [ -z "$HAS_FILE_INPUT" ]; then
		echo HAS_FILE_INPUT=0 FUZZ_DPRINT=0 ENV_FUZZ_COUNT=0 FUZZ_I_BASEPROG=$i LD_PRELOAD=/usr/local/lib/afl/argvdump64.so /usr/bin/timeout 2 /coreutils_preload/bin/$i \$@ > /coreutils_src/obj-preload/src_preload/$i
	else
		echo HAS_FILE_INPUT=1 FUZZ_DPRINT=0 ENV_FUZZ_COUNT=0 FUZZ_I_BASEPROG=$i LD_PRELOAD=/usr/local/lib/afl/argvdump64.so /usr/bin/timeout 2 /coreutils_preload/bin/$i \$@ > /coreutils_src/obj-preload/src_preload/$i
	fi
	chmod +x /coreutils_src/obj-preload/src_preload/$i
done
