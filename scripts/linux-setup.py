"""Install the pinned course toolchain in the Ubuntu guest (never Android directly)."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import time

ROOT = Path('/work')
CONFIG = json.loads((Path(__file__).resolve().parent.parent / 'environment.json').read_text())

def run(*args, cwd=None, **kwargs):
    print('+ ' + ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), cwd=cwd or ROOT, check=True, **kwargs)

def network(*args, **kwargs):
    for attempt in range(3):
        try:
            return run(*args, **kwargs)
        except subprocess.CalledProcessError:
            if attempt == 2:
                raise
            print('Síťová operace selhala; opakuji…', flush=True)
            time.sleep(2 ** (attempt + 1))

def checkout(path, url, revision, branch=None, sparse=False, previous_revision=None):
    def commit(ref):
        result = subprocess.run(['git', '-C', str(path), 'rev-parse', '--verify', ref + '^{commit}'], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None

    fresh = not (path / '.git').exists()
    if fresh:
        if path.exists() and any(path.iterdir()):
            raise RuntimeError(f'{path} neni prazdny Git repozitar; nic nebylo prepsano.')
        run('git', 'init', path)
        run('git', 'remote', 'add', 'origin', url, cwd=path)
    origin = subprocess.check_output(['git', '-C', str(path), 'remote', 'get-url', 'origin'], text=True).strip()
    if origin != url:
        raise RuntimeError(f'{path} má jiný origin. Automatická aktualizace jej nezmění.')
    current = commit('HEAD')
    base_ref = 'refs/zephyr-manager/base'
    base = commit(base_ref)
    # Migrate installations made before the managed base ref was recorded.
    if current and not base and previous_revision:
        base = commit(previous_revision)
        if not base:
            network('git', 'fetch', '--depth', '1', 'origin', previous_revision, cwd=path)
            base = commit('FETCH_HEAD')
    if sparse:
        run('git', 'config', 'remote.origin.promisor', 'true', cwd=path)
        run('git', 'config', 'remote.origin.partialclonefilter', 'blob:none', cwd=path)
        patterns = path / '.git/info/sparse-checkout'
        if not patterns.exists():
            patterns.parent.mkdir(exist_ok=True)
            patterns.write_text('/*\n!/*/\n')
            run('git', 'config', 'core.sparseCheckout', 'true', cwd=path)
            run('git', 'config', 'core.sparseCheckoutCone', 'true', cwd=path)
    wanted = commit(revision)
    if current and wanted == current:
        run('git', 'update-ref', base_ref, wanted, cwd=path)
        return
    options = ['--depth', '1']
    if branch and not fresh:
        shallow = subprocess.check_output(['git', 'rev-parse', '--is-shallow-repository'], cwd=path, text=True).strip()
        options = ['--unshallow'] if shallow == 'true' else []
    if sparse:
        options.append('--filter=blob:none')
    network('git', 'fetch', *options, 'origin', revision, cwd=path)
    wanted = commit('FETCH_HEAD')
    # Repairs must preserve both uncommitted work and commits on a student's branch.
    if current and branch and subprocess.run(['git', 'merge-base', '--is-ancestor', wanted, 'HEAD'], cwd=path).returncode == 0:
        run('git', 'update-ref', base_ref, wanted, cwd=path)
        return
    if current != wanted:
        dirty = subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain'], text=True)
        if dirty:
            raise RuntimeError(f'{path} obsahuje změny. Aktualizace je nepřepíše; nejprve je uložte.')
        if current and not branch and current != base:
            raise RuntimeError(f'{path} obsahuje vlastní nebo neznámé commity. Aktualizace je nepřepíše.')
        if current and branch:
            run('git', 'merge', '--ff-only', wanted, cwd=path)
        else:
            run('git', 'checkout', '-b', branch, wanted, cwd=path) if branch else run('git', 'checkout', '--detach', wanted, cwd=path)
    run('git', 'update-ref', base_ref, wanted, cwd=path)


def validation_source(course):
    # Read the pinned Git objects, never the student's working tree or build folder.
    target = ROOT / 'validation' / CONFIG['course_revision']
    target.mkdir(parents=True, exist_ok=True)
    with subprocess.Popen(['git', '-C', str(course), 'archive', CONFIG['course_revision'],
                           'apps/hello_world', 'scripts/run-qemu.sh'], stdout=subprocess.PIPE) as archive:
        with tarfile.open(fileobj=archive.stdout, mode='r|') as files:
            files.extractall(target, filter='data')
        if archive.wait():
            raise RuntimeError('Nelze připravit původní testovací příklad.')
    return target


def validate_environment(course):
    sample = validation_source(course)
    run('west', 'build', '-p', 'auto', '-b', CONFIG['board'], '-d', 'build-hello_world', 'apps/hello_world', '-o=-j2',
        '--', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', cwd=sample)
    log = ROOT / 'hello-test.log'
    print('Testuji ESP32 v QEMU (nejvýše 90 sekund)…', flush=True)
    with log.open('w') as output:
        result = subprocess.run(['timeout', '90s', './scripts/run-qemu.sh', 'build-hello_world'], cwd=sample,
                                stdout=output, stderr=subprocess.STDOUT)
    if result.returncode not in (0, 124) or 'Hello, squirrels! Zephyr is alive.' not in log.read_text(errors='replace'):
        raise RuntimeError('Test ESP32 selhal. Podrobnosti: /work/hello-test.log')


def protect_module(project):
    if not (project / '.git').exists():
        return
    if subprocess.check_output(['git', '-C', str(project), 'status', '--porcelain'], text=True).strip():
        raise RuntimeError(f'Modul {project.name} obsahuje změny; nejprve je uložte.')
    previous = subprocess.run(['git', '-C', str(project), 'rev-parse', '--verify', 'manifest-rev'], capture_output=True, text=True)
    head = subprocess.run(['git', '-C', str(project), 'rev-parse', '--verify', 'HEAD'], capture_output=True, text=True)
    if head.returncode == 0 and (previous.returncode != 0 or head.stdout.strip() != previous.stdout.strip()):
        raise RuntimeError(f'Modul {project.name} obsahuje vlastní nebo neznámé commity. Automatická aktualizace je nepřepíše.')


def main():
    arch = platform.machine()
    if arch not in CONFIG['esp_qemu_sha256']:
        raise RuntimeError('Podporovane architektury: aarch64, x86_64.')
    workspace = ROOT / 'zephyrproject'
    workspace.mkdir(exist_ok=True)
    venv = workspace / '.venv'
    if not (venv / 'bin/python').exists():
        run('python3', '-m', 'venv', venv)
    os.environ['PATH'] = str(venv / 'bin') + ':' + os.environ['PATH']
    run('python', '-m', 'pip', 'install', 'west')
    zephyr = workspace / 'zephyr'
    installed_file = ROOT / 'installed.json'
    try:
        installed = json.loads(installed_file.read_text())
        if not isinstance(installed, dict):
            installed = {}
    except (OSError, ValueError):
        installed = {}
    checkout(zephyr, 'https://github.com/zephyrproject-rtos/zephyr.git', CONFIG['zephyr'], sparse=True,
             previous_revision=installed.get('zephyr'))
    # Fetch build sources in smaller Git transfers. Failed transfers can be retried
    # without downloading an entire large repository again. Documentation and
    # Zephyr's own test suite can be added later with `git sparse-checkout disable`.
    sparse = subprocess.run(['git', 'config', '--get', 'core.sparseCheckout'], cwd=zephyr, capture_output=True, text=True)
    if sparse.stdout.strip() == 'true':
        directories = subprocess.check_output(['git', 'ls-tree', '-d', '--name-only', 'HEAD'], cwd=zephyr, text=True)
        included = set(subprocess.check_output(['git', 'sparse-checkout', 'list'], cwd=zephyr, text=True).splitlines())
        for directory in directories.splitlines():
            if directory not in ('doc', 'tests') and directory not in included:
                network('git', 'sparse-checkout', 'add', directory, cwd=zephyr)
    if not (workspace / '.west').exists():
        run('west', 'init', '-l', '--mf', 'west.yml', '.', cwd=zephyr)
    # west update checks out manifest revisions; protect edits in modules first.
    listed = subprocess.check_output(['west', 'list', '-f', '{abspath}', *CONFIG['modules']], cwd=zephyr, text=True)
    for location in listed.splitlines():
        protect_module(Path(location))
    # Course targets ESP32; unrelated vendor HALs need not fill a tablet's storage.
    network('west', 'update', '-o=--depth=1', '-n', *CONFIG['modules'], cwd=zephyr)
    run('west', 'zephyr-export', cwd=zephyr)
    run('python', '-m', 'pip', 'install', '-r', 'scripts/requirements-base.txt', cwd=zephyr)
    run('west', 'packages', '-m', 'hal_espressif', '-m', 'mcuboot', 'pip', '--install', cwd=zephyr)
    sdk_version = (zephyr / 'SDK_VERSION').read_text().strip()
    sdk = ROOT / ('zephyr-sdk-' + sdk_version)
    os.environ['ZEPHYR_BASE'] = str(zephyr)
    os.environ['ZEPHYR_SDK_INSTALL_DIR'] = str(sdk)
    compiler = sdk / 'gnu' / CONFIG['toolchain'] / 'bin' / (CONFIG['toolchain'] + '-gcc')
    if not compiler.exists():
        run('west', 'sdk', 'install', '--no-hosttools', '--gnu-toolchains', CONFIG['toolchain'], '--install-dir', sdk, cwd=zephyr)
    release = CONFIG['esp_qemu_release']
    qemu = ROOT / 'espressif-qemu' / release
    if not (qemu / '.release').exists() or (qemu / '.release').read_text().strip() != release:
        name = f"qemu-xtensa-softmmu-esp_develop_{release.removeprefix('esp-develop-').replace('-', '_')}-{arch}-linux-gnu.tar.xz"
        archive = ROOT / (name + '.download')
        run('curl', '-fL', '--retry', '3', '--retry-all-errors', '--connect-timeout', '30', '-o', archive, f'https://github.com/espressif/qemu/releases/download/{release}/{name}')
        with archive.open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() != CONFIG['esp_qemu_sha256'][arch]:
                raise RuntimeError('Kontrolni soucet Espressif QEMU nesouhlasi.')
        qemu.mkdir(parents=True, exist_ok=True)
        run('tar', '-xJf', archive, '-C', qemu, '--strip-components=1')
        (qemu / '.release').write_text(release)
        archive.unlink()
    os.environ['PATH'] = str(qemu / 'bin') + ':' + os.environ['PATH']
    run(qemu / 'bin/qemu-system-xtensa', '--version')
    course = ROOT / 'zephyr4squirrels'
    checkout(course, 'https://github.com/lenkakt/zephyr4squirrels.git', CONFIG['course_revision'], 'moje-cviceni')
    (ROOT / 'env.sh').write_text(f'source /work/zephyrproject/.venv/bin/activate\nexport ZEPHYR_BASE=/work/zephyrproject/zephyr\nexport ZEPHYR_SDK_INSTALL_DIR={sdk}\nexport PATH={qemu}/bin:$PATH\ncd /work/zephyr4squirrels\n')
    validate_environment(course)
    version = {**CONFIG, 'host_arch': arch, 'test': 'Hello, squirrels! Zephyr is alive.'}
    temporary = ROOT / 'installed.tmp'
    temporary.write_text(json.dumps(version, indent=2))
    temporary.replace(installed_file)
    print('HOTOVO: Zephyr sestaven, ESP32 emulace overena.', flush=True)

if __name__ == '__main__':
    main()
