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
parser.add_argument('-t', '--targets', required=True, help="File with one coreutil target per line")
parser.add_argument('-i', '--input', required=True, help="Directory containing input corpora for all targets")
parser.add_argument('-td', '--tdir', default='/coreutils_aflpp/bin', help="Directory containing coreutils targets compiled with afl")
parser.add_argument('-e', '--env', default='/fuzz_data/make_check/processed', help="Directory holding the target.envmeta and target.hasfileinput files generated with prep_env.py and check_file_input.sh")
parser.add_argument('-f', '--fuzz', default='/fuzz_data/fuzzings/', help="Fuzzing output directory")
parser.add_argument('-nt', default=multiprocessing.cpu_count(), help="Number of threads", type=int)

args = parser.parse_args()
target_dir = args.tdir
env_dir = args.env
input_dir = args.input
fuzz_dir = args.fuzz

# sanitiy checks
if not os.path.isdir(target_dir):
    print("Target dir No exist %s" % target_dir)
    exit(1)
if not os.path.isdir(env_dir):
    print("Env dir No exist %s" % env_dir)
    exit(1)
if not os.path.isdir(input_dir):
    print("Input dir No exist %s" % input_dir)
    exit(1)
if not os.path.isdir(fuzz_dir):
    print("Fuzz dir No exist %s" % fuzz_dir)
    exit(1)

progs = []
pool = ThreadPool(args.nt)
for target in open(args.targets).readlines():
    target = target.rstrip()
    print(target)
    if target == '[':
        target = '\\['
    target_path = os.path.join(target_dir, target)
    if not os.path.exists(target_path):
        print("Target path No exist %s" % target_path)
        continue

    env_path = os.path.join(env_dir, "%s.envmeta" % target)
    if not os.path.isfile(env_path):
        print("Env path No exist %s" % env_path)
        continue

    fileinp_path = os.path.join(env_dir, "%s.fileinput" % target)
    if not os.path.isfile(fileinp_path):
        print("Fileinp No exist %s" % fileinp_path)
        continue

    input_dir_path = os.path.join(input_dir, target)
    if not os.path.isdir(input_dir_path):
        print("Input dir path No exist %s" % input_dir_path)
        continue

    fuzz_dir_target = os.path.join(fuzz_dir, target)
    if not os.path.isdir(fuzz_dir_target):
        os.mkdir(fuzz_dir_target)
    output_corpus_path = os.path.join(fuzz_dir_target, 'out')
    input_corpus_path = os.path.join(fuzz_dir_target, 'in')

    if not os.path.isdir(output_corpus_path):
        os.mkdir(output_corpus_path)

    if not os.path.isdir(input_corpus_path):
        os.mkdir(input_corpus_path)

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


    envs_dict["AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES"] = '1'
    envs_dict["AFL_AUTORESUME"] = '1'
    #envs_dict["AFL_FORCE_UI"] = '1'
    envs_dict["AFL_NO_UI"] = '1'
    envs_dict["AFL_IMPORT_FIRST"] = '1'
    envs_dict["AFL_TESTCACHE_SIZE"] = '3000'
    envs_dict["FUZZ_ISFUZZING"] = '1'

    cmd_cmin = [
            '/usr/local/bin/afl-cmin',
            '-t', '1000',
            '-i', input_dir_path,
            '-o', input_corpus_path,
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
