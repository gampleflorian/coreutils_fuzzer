import subprocess
import argparse
import os
import socket
import json
import time
import shlex
import multiprocessing
from multiprocessing.pool import ThreadPool


def call_proc(cmd, env):
    print("running %s" % cmd)
    p = subprocess.Popen(shlex.split(cmd), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return (out, err)

parser = argparse.ArgumentParser()
parser.add_argument('-t', '--target', required=True, help="The coreutils target")
parser.add_argument('-i', '--input', required=True, help="List of directories containing input corpora", nargs="+")
parser.add_argument('-td', '--tdir', default='/coreutils_aflpp/bin', help="Directory containing coreutils targets compiled with afl")
parser.add_argument('-e', '--env', default='/fuzz_data/make_check/processed', help="Directory holding the target.envmeta and target.hasfileinput files generated with prep_env.py and check_file_input.sh")
parser.add_argument('-o', '--output', default='/fuzz_data/fuzzings/', help="Output directory to store minimized corpora")
parser.add_argument('-nt', default=multiprocessing.cpu_count(), help="Number of threads", type=int)

args = parser.parse_args()
target = args.target
target_dir = args.tdir
env_dir = args.env
output_dir = args.output

# sanitiy checks
if not os.path.isdir(target_dir):
    print("Target dir No exist %s" % target_dir)
    exit(1)
if not os.path.isdir(env_dir):
    print("Env dir No exist %s" % env_dir)
    exit(1)

if target == '[':
    target = '\\['
target_path = os.path.join(target_dir, target)
if not os.path.isfile(target_path):
    print("Target path no exist %s" % target_path)
    exit(1)

env_path = os.path.join(env_dir, "%s.envmeta" % target)
if not os.path.isfile(env_path):
    print("Env path No exist %s" % env_path)
    exit(1)

fileinp_path = os.path.join(env_dir, "%s.fileinput" % target)
if not os.path.isfile(fileinp_path):
    print("Fileinp No exist %s" % fileinp_path)
    exit(1)

envs_dict = {}
envs = open(env_path, "r").read()
envs = envs.rstrip()
for env in envs.split(" "):
    try:
        env_name, env_val = env.split('=')
        env_val = env_val.replace("\"", "")
        envs_dict[env_name] = env_val
    except:
        pass
fileinp = open(fileinp_path, "r").read()
fileinp = fileinp.rstrip()
for env in fileinp.split(" "):
    try:
        env_name, env_val = env.split('=')
        env_val = env_val.replace("\"", "")
        envs_dict[env_name] = env_val
    except:
        pass

if "ENV_FUZZ_COUNT" not in envs_dict.keys():
    print("Warning env might be broken (no fuzz count)")
    envs_dict["ENV_FUZZ_COUNT"] = '0'
if "HAS_FILE_INPUT" not in envs_dict.keys():
    print("Warning env might be broken (no file input)")
    envs_dict["HAS_FILE_INPUT"] = '0'

envs_dict["AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES"] = '1'
envs_dict["AFL_AUTORESUME"] = '1'
#envs_dict["AFL_FORCE_UI"] = '1'
envs_dict["AFL_NO_UI"] = '1'
envs_dict["AFL_IMPORT_FIRST"] = '1'
envs_dict["AFL_TESTCACHE_SIZE"] = '2000'
envs_dict["AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES"] = '1'
envs_dict["AFL_SKIP_CPUFREQ"] = '1'
envs_dict["FUZZ_ISFUZZING"] = '1'
print("ENV:")
print(json.dumps(envs_dict, indent=2))


progs = []
pool = ThreadPool(args.nt)
for inp_i, input_dir in enumerate(args.input):
    output_dir_i = os.path.join(output_dir, "cmin_%d" % inp_i)
    if not os.path.exists(output_dir_i):
        os.mkdir(output_dir_i)
    if not os.path.isdir(input_dir):
        print("Input dir No exist %s" % input_dir)
        exit(1)

    cmd_cmin = [
            '/usr/local/bin/afl-cmin',
            '-t', '1000',
            '-i', input_dir,
            '-o', output_dir_i,
            '--',
            target_path
            ]
    progs.append(pool.apply_async(call_proc, (" ".join(cmd_cmin), envs_dict)))

pool.close()
pool.join()

print('-' * 80)
for p in progs:
    out, err = p.get()
    print('.'*80)
    try:
        print(out.decode("utf-8"))
    except:
        pass
    print('.'*80)
    try:
        print(err.decode("utf-8"))
    except:
        pass
