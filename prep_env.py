import sys
import argparse
import itertools
import os

parser = argparse.ArgumentParser()
parser.add_argument('-e', '--envs', required=True, help='list of env files', nargs='*')
parser.add_argument('-i', '--inps', required=True, help='list of input files', nargs='+')
parser.add_argument('-o', '--out', required=True, help='output dir')
args = parser.parse_args()

env_vals = {}
for env_fn in args.envs:
    try:
        env_data = open(env_fn, "r").readlines()
    except:
        print("Err could not open %s" % env_fn)
        continue

    for env_line in env_data:
        if not env_line:
            continue
        try:
            parts = env_line.split(":")
            env_name = parts[0]
            if "LD_PRELOAD" in env_name:
                continue
            env_val = ":".join(parts[1:])
            env_val = env_val.lstrip()
            if env_name not in env_vals.keys():
                env_vals[env_name] = set()
            env_vals[env_name].add(env_val.rstrip())
        except Exception as e:
            print('.' * 80)
            print("ERR")
            print(env_line)
            print(e)
            pass

env_names = list(env_vals.keys())
for inp_fn in args.inps:
    try:
        inp_orig = open(inp_fn, "rb").read()
        for cntr, inp in enumerate(itertools.product(*[list(vals) for vals in [env_vals[env_name] for env_name in env_names]])):
            inp_fn_new = os.path.join(args.out, os.path.basename(inp_fn) + ".withenv_%d" % cntr)
            inp_fd_new = open(inp_fn_new, "wb")
            #sys.stderr.write("Adding env " + str(inp) + "\n")
            for inp_val in inp:
                if "null" in inp_val:
                    inp_fd_new.write(bytes([2]))
                else:
                    #sys.stderr.write("Adding env val " + str(inp_val) + " to " + inp_fn_new + "\n")
                    inp_fd_new.write(inp_val.encode('ascii'))
                inp_fd_new.write(bytes([0]))
            inp_fd_new.write(inp_orig)
            inp_fd_new.close()
    except:
        print("Err could not open %s" % inp_fn)
        continue
print("ENV_FUZZ_COUNT=%d %s" % (len(env_names), " ".join(map(lambda t: "ENV_FUZZ_COUNT_%d=\"%s\"" % (t[0], t[1]), enumerate(env_names)))), end="")

