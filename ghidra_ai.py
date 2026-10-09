"""Portable setup, GUI launch and fixture test commands. Python 3.10+."""
import argparse
import getpass
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def find_ghidra(explicit=None):
    value = explicit or os.environ.get('GHIDRA_INSTALL_DIR')
    if value:
        root = Path(value).expanduser().resolve()
        if not (root / 'Ghidra/application.properties').is_file():
            raise ValueError('Not a Ghidra installation: ' + str(root))
        return root
    snap_roots = list(Path('/snap/ghidra').glob('[0-9]*'))
    for root in sorted(snap_roots, key=lambda p: int(p.name), reverse=True):
        if (root / 'ghidra/Ghidra/application.properties').is_file():
            return root / 'ghidra'
    raise ValueError('Supply --ghidra /path/to/ghidra or set GHIDRA_INSTALL_DIR.')


def snap_root(ghidra):
    return ghidra.parent if (ghidra.parent / 'meta/snap.yaml').is_file() else None


def work_directory(args, ghidra):
    if args.work_dir:
        return Path(args.work_dir).expanduser().resolve()
    if snap_root(ghidra):
        return Path.home() / 'snap/ghidra/current/ghidra-ai'
    return Path.home() / 'ghidra-ai-work'


def install_scripts(ghidra, destination=None):
    if destination:
        directory = Path(destination).expanduser().resolve()
    elif snap_root(ghidra):
        directory = Path.home() / 'snap/ghidra/current/ghidra_scripts'
    else:
        directory = Path.home() / 'ghidra_scripts'
    directory.mkdir(parents=True, exist_ok=True)
    for name in ('ai_core.py', 'OpenAIAnalyze.py'):
        source = ROOT / 'ghidra_scripts' / name
        target = directory / name
        if target.is_symlink():
            raise ValueError('Script destination is a symlink; choose --scripts-dir with a real directory: ' + str(target))
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
    return directory


def python_runtime(args, ghidra):
    env = os.environ.copy()
    env['GHIDRA_INSTALL_DIR'] = str(ghidra)
    if args.java_home:
        env['JAVA_HOME'] = str(Path(args.java_home).expanduser().resolve())
    snap = snap_root(ghidra)
    if snap and not args.python:
        config = (snap / 'pyvenv.cfg').read_text()
        version = re.search(r'version\s*=\s*(\d+\.\d+)', config).group(1)
        metadata = (snap / 'meta/snap.yaml').read_text()
        base = re.search(r'^base:\s*(\S+)', metadata, re.M).group(1)
        base_usr = Path('/snap') / base / 'current/usr'
        interpreter = base_usr / ('bin/python' + version)
        if not interpreter.is_file():
            raise ValueError('Snap Python base runtime missing; supply --python and --java-home.')
        jvms = sorted((snap / 'usr/lib/jvm').glob('*'))
        java = next((p for p in jvms if (p / 'bin/java').is_file()), None)
        if not args.java_home and java:
            env['JAVA_HOME'] = str(java)
        env['PYTHONHOME'] = str(base_usr)
        env['PYTHONPATH'] = str(snap / ('lib/python' + version + '/site-packages'))
        env['LD_LIBRARY_PATH'] = str(snap / 'usr/lib/x86_64-linux-gnu') + ':' + env.get('LD_LIBRARY_PATH', '')
        return str(interpreter), env
    return args.python or sys.executable, env


def configure_key(env, provider):
    variable = 'OPENROUTER_API_KEY' if provider == 'openrouter' else 'OPENAI_API_KEY'
    env['AI_PROVIDER'] = provider
    key = env.get(variable) or getpass.getpass(variable + ' (hidden): ')
    if not key.strip():
        raise ValueError('No API key entered.')
    env[variable] = key.strip()


def build_fixtures(work):
    if not sys.platform.startswith('linux') or os.uname().machine != 'x86_64':
        raise ValueError('Fixture build/execution requires Linux x86-64 (including WSL). GUI setup supports other platforms.')
    for tool in ('as', 'ld', 'nm'):
        if not shutil.which(tool):
            raise ValueError('Install GNU binutils; missing command: ' + tool)
    work.mkdir(parents=True, exist_ok=True)
    for name in ('demo', 'flag_demo'):
        obj = work / (name + '.o')
        subprocess.run(['as', str(ROOT / 'examples' / (name + '.s')), '-o', str(obj)], check=True)
        subprocess.run(['ld', str(obj), '-o', str(work / name)], check=True)
    result = subprocess.run([str(work / 'demo')], timeout=3).returncode
    if result != 42:
        raise ValueError('Addition fixture returned an unexpected result.')
    print('PASS: owned demo binary returns 42 (19 + 23)')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['install', 'launch', 'test'])
    parser.add_argument('--ghidra', help='Ghidra installation directory; Snap is detected automatically')
    parser.add_argument('--python', help='Python executable with pyghidra installed')
    parser.add_argument('--java-home', help='JDK directory required by your Ghidra release')
    parser.add_argument('--scripts-dir', help='Script installation directory')
    parser.add_argument('--work-dir', help='Generated binary, project and report directory')
    parser.add_argument('--provider', choices=['openrouter', 'openai'], default='openrouter')
    parser.add_argument('--model', help='Model override; OpenRouter permits only free IDs')
    parser.add_argument('--live', action='store_true', help='Make a live API call during test')
    parser.add_argument('--flag', action='store_true', help='Test flag recovery instead of addition')
    args = parser.parse_args(argv)
    try:
        ghidra = find_ghidra(args.ghidra)
        scripts = install_scripts(ghidra, args.scripts_dir)
        print('Scripts installed: ' + str(scripts))
        if args.command == 'install':
            return 0
        if args.model and args.provider == 'openrouter' and args.model != 'openrouter/free' and not args.model.endswith(':free'):
            raise ValueError('OpenRouter model must be openrouter/free or end in :free.')
        if args.command == 'launch':
            env = os.environ.copy()
            if args.model:
                env['OPENROUTER_MODEL' if args.provider == 'openrouter' else 'OPENAI_MODEL'] = args.model
            if args.java_home:
                env['JAVA_HOME'] = args.java_home
            configure_key(env, args.provider)
            if snap_root(ghidra):
                return subprocess.run(['/snap/bin/ghidra'], env=env).returncode
            interpreter, runtime_env = python_runtime(args, ghidra)
            runtime_env.update({k: v for k, v in env.items() if k in (
                'AI_PROVIDER', 'OPENAI_API_KEY', 'OPENROUTER_API_KEY', 'OPENAI_MODEL', 'OPENROUTER_MODEL')})
            return subprocess.run([interpreter, '-m', 'pyghidra', '-g', '--install-dir', str(ghidra)], env=runtime_env).returncode
        work = work_directory(args, ghidra)
        build_fixtures(work)
        interpreter, env = python_runtime(args, ghidra)
        env['GHIDRA_AI_WORK_DIR'] = str(work)
        env['GHIDRA_AI_SCRIPTS_DIR'] = str(scripts)
        if args.model:
            env['OPENROUTER_MODEL' if args.provider == 'openrouter' else 'OPENAI_MODEL'] = args.model
        # live_smoke prompts in the child process; credentials never enter argv.
        runner = work / 'live_smoke.py'
        shutil.copy2(ROOT / 'tests/live_smoke.py', runner)
        command = [interpreter, str(runner)]
        if args.flag:
            command.append('--flag')
        if args.live:
            command.append('--live')
        if args.provider == 'openrouter':
            command.append('--openrouter')
        return subprocess.run(command, env=env).returncode
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('Error: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
