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
parser.add_argument('-td', '--tdir', default='/coreutils_aflpp/bin', help="Directory containing coreutils targets compiled with afl")
parser.add_argument('--lafdir', default='/coreutils_aflpp_laf/bin', help="Directory containing coreutils targets compiled with afl and compcov")
parser.add_argument('--rqdir', default='/coreutils_aflpp_rq/bin', help="Directory containing coreutils targets compiled with afl and redqueen")
parser.add_argument('-e', '--env', default='/fuzz_data/make_check/processed', help="Directory holding the target.envmeta and target.hasfileinput files generated with prep_env.py and check_file_input.sh")
parser.add_argument('-f', '--fuzz', default='/fuzz_data/fuzzings/', help="Fuzzing output directory")
parser.add_argument('-x', '--xxx', default=3600, help="Stop after x seconds", type=int)
parser.add_argument('-nt', default=multiprocessing.cpu_count(), help="Number of threads", type=int)

args = parser.parse_args()
target = args.target
target_dir = args.tdir
env_dir = args.env
fuzz_dir = args.fuzz

hostname = socket.gethostname()

# sanitiy checks
if args.nt < 1:
    print("Give me at least 1 thread")
    exit(1)
if not os.path.isdir(target_dir):
    print("No exist %s" % target_dir)
    exit(1)
if not os.path.isdir(env_dir):
    print("No exist %s" % env_dir)
    exit(1)
if not os.path.isdir(fuzz_dir):
    print("No exist %s" % fuzz_dir)
    exit(1)

target_compcov_dir = args.lafdir
if not os.path.isdir(target_compcov_dir):
    print("No exist %s" % target_compcov_dir)
    target_compcov_dir = target_dir
target_compcov_path = os.path.join(target_compcov_dir, target)
if not os.path.isfile(target_compcov_path):
    print("No exist %s" % target_compcov_path)
    exit(1)

target_complog_dir = args.rqdir
if not os.path.isdir(target_complog_dir):
    print("No exist %s" % target_complog_dir)
    target_complog_dir = target_dir
target_complog_path = os.path.join(target_complog_dir, target)
if not os.path.isfile(target_complog_path):
    print("No exist %s" % target_complog_path)
    exit(1)

target_path = os.path.join(target_dir, target)
if not os.path.isfile(target_path):
    print("No exist %s" % target_path)
    exit(1)

env_path = os.path.join(env_dir, "%s.envmeta" % target)
if not os.path.isfile(env_path):
    print("No exist %s" % env_path)
    exit(1)

fileinp_path = os.path.join(env_dir, "%s.fileinput" % target)
if not os.path.isfile(fileinp_path):
    print("Fileinp No exist %s" % fileinp_path)
    exit(1)

fuzz_dir_target = os.path.join(fuzz_dir, target)
if not os.path.isdir(fuzz_dir_target):
    os.mkdir(fuzz_dir_target)
output_corpus_path = os.path.join(fuzz_dir_target, 'out')
input_corpus_path = os.path.join(fuzz_dir_target, 'in')

if not os.path.isdir(output_corpus_path):
    os.mkdir(output_corpus_path)

if not os.path.isdir(input_corpus_path):
    print("Warning no input dir, creating new. Did you forget to run_cmin.py?")
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

pool = ThreadPool(args.nt)

p_afl = []
cmd_afl = []
cmd_fuzz_main = [
        '/usr/local/bin/afl-fuzz',
        '-M', 'main-'+hostname,
        '-t', '5000',
        '-V', "%d" % (args.xxx+30),
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_path,
        ]
cmd_afl.append(cmd_fuzz_main)

cmd_fuzz_det = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-Det',
        '-D',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_compcov_path,
        ]
cmd_afl.append(cmd_fuzz_det)

cmd_fuzz_z = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-Z',
        '-Z',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_complog_path,
        ]
cmd_afl.append(cmd_fuzz_z)

cmd_fuzz_mopt0 = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-mopt0',
        '-L', '0',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_path,
        ]
cmd_afl.append(cmd_fuzz_mopt0)

cmd_fuzz_mopt1 = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-mopt1',
        '-L', '0',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_complog_path,
        ]
cmd_afl.append(cmd_fuzz_mopt1)

cmd_fuzz_mopt2 = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-mopt2',
        '-L', '0',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_compcov_path,
        ]
cmd_afl.append(cmd_fuzz_mopt2)

cmd_fuzz_pexplore = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-pexplore',
        '-p', 'explore',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_path,
        ]
cmd_afl.append(cmd_fuzz_pexplore)

cmd_fuzz_pcoe = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-pcoe',
        '-p', 'coe',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_path,
        ]
cmd_afl.append(cmd_fuzz_pcoe)

cmd_fuzz_plin = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-plin',
        '-p', 'lin',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_complog_path,
        ]
cmd_afl.append(cmd_fuzz_plin)

cmd_fuzz_pquad = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-pquad',
        '-p', 'quad',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_compcov_path,
        ]
cmd_afl.append(cmd_fuzz_pquad)

cmd_fuzz_pexploit = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-pexploit',
        '-p', 'exploit',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_path,
        ]
cmd_afl.append(cmd_fuzz_pexploit)

cmd_fuzz_prare = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-prare',
        '-p', 'rare',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_path,
        ]
cmd_afl.append(cmd_fuzz_prare)

cmd_fuzz_x0 = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-x0',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_compcov_path,
        ]
cmd_afl.append(cmd_fuzz_x0)

cmd_fuzz_x1 = [
        '/usr/local/bin/afl-fuzz',
        '-S', target+'-x1',
        '-t', '5000',
        '-V', "%d" % args.xxx,
        '-i', input_corpus_path,
        '-o', output_corpus_path,
        '--', target_complog_path,
        ]
cmd_afl.append(cmd_fuzz_x1)

for i, cmd in enumerate(cmd_afl):
    p_afl.append(pool.apply_async(call_proc, (" ".join(cmd), envs_dict)))
    if i==0:
        time.sleep(3)
    if(i>=args.nt-1):
        print("Max number of fuzzers reached, stopping")
        break

pool.close()
pool.join()

print('-' * 80)
print("AFLFUZZ")
for p in p_afl:
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
