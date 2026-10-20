#!/data/data/com.termux/files/usr/bin/python
"""Rootless Termux controller. Only this application's container/workspace is used."""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()
WORK = HOME / 'zephyr-work'
STATE = HOME / '.local/state/zephyr-android'
CONTAINER = 'zephyr-ops'
REMOTE = 'https://github.com/Jirkas-prog/termux-zephyr-android.git'
API = 'https://api.github.com/repos/Jirkas-prog/termux-zephyr-android/releases/latest'
ACTIONS = ('install', 'update', 'status', 'build', 'run', 'shell', 'edit', 'backup', 'check-updates')


def run(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def write_state(**value):
    STATE.mkdir(parents=True, exist_ok=True)
    temporary = STATE / 'state.tmp'
    temporary.write_text(json.dumps({**value, 'time': int(time.time())}, ensure_ascii=False))
    temporary.replace(STATE / 'state.json')


def is_busy():
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'operation.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return False
        except BlockingIOError:
            return True


def status():
    state = read_json(STATE / 'state.json')
    busy = is_busy()
    if state.get('phase') == 'running' and not busy:
        state.update(phase='interrupted', message='Operace byla přerušena. Lze ji znovu spustit.')
    log = STATE / 'operation.log'
    tail = ''
    if log.exists():
        with log.open('rb') as stream:
            stream.seek(max(0, log.stat().st_size - 10000))
            tail = stream.read().decode('utf-8', errors='replace')
    return {**state, 'busy': busy, 'installed': read_json(WORK / 'installed.json'),
            'manager_version': read_json(REPO / 'environment.json').get('version'),
            'free_gib': round(shutil.disk_usage(HOME).free / 1024 ** 3, 1),
            'apps': sorted(p.parent.name for p in (WORK / 'zephyr4squirrels/apps').glob('*/CMakeLists.txt')),
            'log': tail}


def guest(*command, **kwargs):
    return run('proot-distro', 'login', '--bind', f'{WORK}:/work', '--bind', f'{REPO}:/manager',
               CONTAINER, '--', *command, **kwargs)


def application(name):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', name):
        raise ValueError('Neplatný název cvičení.')
    base = (WORK / 'zephyr4squirrels/apps').resolve()
    target = (base / name).resolve()
    if target.parent != base or not (target / 'CMakeLists.txt').is_file():
        raise ValueError('Cvičení neexistuje nebo leží mimo pracovní složku.')
    return name


def latest_release():
    request = urllib.request.Request(API, headers={'User-Agent': 'Termux-Zephyr-Android', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    tag = release['tag_name']
    if not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
        raise ValueError('Neplatná verze vydání na GitHubu.')
    return tag


def update_manager():
    if subprocess.check_output(['git', '-C', str(REPO), 'status', '--porcelain'], text=True).strip():
        raise RuntimeError('Správce obsahuje vlastní změny. Automatická aktualizace je nepřepíše.')
    origin = subprocess.check_output(['git', '-C', str(REPO), 'remote', 'get-url', 'origin'], text=True).strip()
    if origin != REMOTE:
        raise RuntimeError('Repozitář správce má jiný origin; automatická aktualizace zastavena.')
    version = read_json(REPO / 'environment.json')['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise RuntimeError('Neplatná místní verze správce.')
    # A clean worktree can still contain private commits. Never detach away from them.
    run('git', '-C', REPO, 'fetch', '--depth', '1', 'origin', 'tag', 'v' + version)
    head = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip()
    released = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'v' + version + '^{commit}'], text=True).strip()
    if head != released:
        raise RuntimeError('Správce obsahuje vlastní commity. Automatická aktualizace je nepřepíše.')
    tag = latest_release()
    if tuple(map(int, tag[1:].split('.'))) < tuple(map(int, version.split('.'))):
        raise RuntimeError('GitHub nabízí starší vydání; prostředí se nevrátí na starší verzi.')
    run('git', '-C', REPO, 'fetch', '--depth', '1', 'origin', 'tag', tag)
    run('git', '-C', REPO, 'checkout', '--detach', tag)
    print('Správce aktualizován na ' + tag, flush=True)


def install():
    # Login is a non-destructive existence check and works across proot-distro layouts.
    exists = subprocess.run(['proot-distro', 'login', CONTAINER, '--', '/bin/true'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    resumed = exists.returncode == 0 or (WORK.exists() and any(WORK.iterdir()))
    required = 1 if resumed else 12
    if shutil.disk_usage(HOME).free < required * 1024 ** 3:
        raise RuntimeError(f'Je potřeba alespoň {required} GiB volného místa. Pro novou instalaci doporučujeme 20 GiB.')
    WORK.mkdir(parents=True, exist_ok=True)
    if exists.returncode:
        run('proot-distro', 'install', read_json(REPO / 'environment.json')['ubuntu'], '--name', CONTAINER)
    guest('/bin/bash', '/manager/scripts/linux-install.sh')


def backup():
    source = WORK / 'zephyr4squirrels'
    if not source.is_dir():
        raise RuntimeError('Nejsou zatím žádná cvičení k zálohování.')
    directory = HOME / 'zephyr-backups'
    directory.mkdir(exist_ok=True)
    name = 'cviceni-' + time.strftime('%Y%m%d-%H%M%S') + '-' + str(time.time_ns() % 1000000000) + '.tar.gz'
    target = directory / name
    temporary = WORK / ('.' + name + '.partial')
    # Archive inside proot: its emulated hard links must become real archive data,
    # not absolute links into the old container's .l2s directory. Ordinary student
    # symlinks remain symlinks (tar is deliberately not passed --dereference).
    # Open the output in native Termux. Android blocks the legacy creat syscall
    # used by GNU tar's compression child; writing through stdout avoids it.
    try:
        with temporary.open('wb') as output:
            guest('/bin/tar', '-czf', '-', '-C', '/work',
                  '--exclude=zephyr4squirrels/build', '--exclude=zephyr4squirrels/build-*', 'zephyr4squirrels', stdout=output)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    print('Záloha: ' + str(target), flush=True)


def execute(action, app):
    if action == 'install':
        install()
    elif action == 'update':
        if (WORK / 'zephyr4squirrels').exists():
            backup()
        update_manager()
        # Load the newly released implementation in a child; parent retains the lock.
        run(sys.executable, REPO / 'scripts/zephyrctl.py', '_install-internal', env={**os.environ, 'ZEPHYR_INTERNAL': '1'})
    elif action == 'backup':
        backup()
    elif action == 'shell':
        guest('/bin/bash', '--rcfile', '/work/env.sh', '-i')
    elif action in ('build', 'run', 'edit'):
        app = application(app)
        guest('/bin/bash', '/manager/scripts/linux-action.sh', action, app)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=(*ACTIONS, '_install-internal'))
    parser.add_argument('--app', default='hello_world')
    args = parser.parse_args()
    if args.action == 'status':
        print(json.dumps(status(), ensure_ascii=False))
        return
    if args.action == 'check-updates':
        print(json.dumps({'latest': latest_release(), 'current': read_json(REPO / 'environment.json')['version']}))
        return
    if os.environ.get('PREFIX') != '/data/data/com.termux/files/usr':
        raise RuntimeError('Tento příkaz spouštějte v Termuxu. Root není potřeba.')
    if args.action == '_install-internal':
        if os.environ.get('ZEPHYR_INTERNAL') != '1':
            raise RuntimeError('Interní příkaz.')
        install()
        return
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'operation.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Již běží jiná operace. Počkejte na její dokončení.')
        interactive = args.action in ('shell', 'run', 'edit')
        with contextlib.ExitStack() as stack:
            if not interactive:
                output = stack.enter_context((STATE / 'operation.log').open('w', buffering=1))
                # Subprocesses inherit the same file descriptors, so progress survives the UI closing.
                sys.stdout.flush()
                os.dup2(output.fileno(), 1)
                os.dup2(output.fileno(), 2)
            write_state(phase='running', action=args.action, message='Probíhá: ' + args.action)
            subprocess.run(['termux-wake-lock'], check=False)
            try:
                execute(args.action, args.app)
                write_state(phase='done', action=args.action, message='Dokončeno: ' + args.action)
            except BaseException as error:
                write_state(phase='error', action=args.action, message=str(error))
                raise
            finally:
                subprocess.run(['termux-wake-unlock'], check=False)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print('CHYBA: ' + str(error), file=sys.stderr)
        sys.exit(1)
