"""Install the pinned course toolchain in the Ubuntu guest (never Android directly)."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
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

def checkout(path, url, revision, branch=None, sparse=False):
    fresh = not (path / '.git').exists()
    if fresh:
        if path.exists() and any(path.iterdir()):
            raise RuntimeError(f'{path} neni prazdny Git repozitar; nic nebylo prepsano.')
        run('git', 'init', path)
        run('git', 'remote', 'add', 'origin', url, cwd=path)
    if sparse:
        run('git', 'config', 'remote.origin.promisor', 'true', cwd=path)
        run('git', 'config', 'remote.origin.partialclonefilter', 'blob:none', cwd=path)
        patterns = path / '.git/info/sparse-checkout'
        if not patterns.exists():
            patterns.parent.mkdir(exist_ok=True)
            patterns.write_text('/*\n!/*/\n')
            run('git', 'config', 'core.sparseCheckout', 'true', cwd=path)
            run('git', 'config', 'core.sparseCheckoutCone', 'true', cwd=path)
    if not fresh:
        dirty = subprocess.check_output(['git', '-C', str(path), 'status', '--porcelain'], text=True)
        current = subprocess.run(['git', '-C', str(path), 'rev-parse', '--verify', 'HEAD'], capture_output=True, text=True)
        # A finished checkout at the requested revision may contain the student's work.
        wanted = subprocess.run(['git', '-C', str(path), 'rev-parse', '--verify', revision + '^{commit}'], capture_output=True, text=True)
        if wanted.returncode == 0 and current.returncode == 0 and current.stdout.strip() == wanted.stdout.strip():
            return
        if dirty:
            raise RuntimeError(f'{path} obsahuje zmeny. Nejprve je commitnete nebo zalohujte; aktualizace je zachova.')
    options = ['--depth', '1']
    if branch and not fresh:
        shallow = subprocess.check_output(['git', 'rev-parse', '--is-shallow-repository'], cwd=path, text=True).strip()
        options = ['--unshallow'] if shallow == 'true' else []
    if sparse:
        options.append('--filter=blob:none')
    network('git', 'fetch', *options, 'origin', revision, cwd=path)
    if branch and not subprocess.run(['git', 'show-ref', '--verify', '--quiet', 'refs/heads/' + branch], cwd=path).returncode:
        run('git', 'merge', '--ff-only', 'FETCH_HEAD', cwd=path)
    else:
        run('git', 'checkout', '-b', branch, 'FETCH_HEAD', cwd=path) if branch else run('git', 'checkout', '--detach', 'FETCH_HEAD', cwd=path)

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
    checkout(zephyr, 'https://github.com/zephyrproject-rtos/zephyr.git', CONFIG['zephyr'], sparse=True)
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
    listed = subprocess.check_output(['west', 'list', '-f', '{abspath}'], cwd=zephyr, text=True)
    for location in listed.splitlines():
        project = Path(location)
        if project != zephyr and (project / '.git').exists():
            if subprocess.check_output(['git', '-C', str(project), 'status', '--porcelain'], text=True).strip():
                raise RuntimeError(f'Modul {project.name} obsahuje změny; nejprve je uložte.')
            previous = subprocess.run(['git', '-C', str(project), 'rev-parse', '--verify', 'manifest-rev'], capture_output=True, text=True)
            head = subprocess.check_output(['git', '-C', str(project), 'rev-parse', 'HEAD'], text=True)
            if previous.returncode == 0 and head.strip() != previous.stdout.strip():
                raise RuntimeError(f'Modul {project.name} obsahuje vlastní commity. Automatická aktualizace je nepřepíše.')
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
        if hashlib.file_digest(archive.open('rb'), 'sha256').hexdigest() != CONFIG['esp_qemu_sha256'][arch]:
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
    run('west', 'build', '-b', CONFIG['board'], '-d', 'build-hello_world', 'apps/hello_world', '-o=-j2', '--', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON', cwd=course)
    log = ROOT / 'hello-test.log'
    print('Testuji ESP32 v QEMU (nejvýše 90 sekund)…', flush=True)
    with log.open('w') as output:
        result = subprocess.run(['timeout', '90s', './scripts/run-qemu.sh', 'build-hello_world'], cwd=course, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode not in (0, 124) or 'Hello, squirrels! Zephyr is alive.' not in log.read_text(errors='replace'):
        raise RuntimeError('Test ESP32 selhal. Podrobnosti: /work/hello-test.log')
    version = {**CONFIG, 'host_arch': arch, 'test': 'Hello, squirrels! Zephyr is alive.'}
    (ROOT / 'installed.json').write_text(json.dumps(version, indent=2))
    print('HOTOVO: Zephyr sestaven, ESP32 emulace overena.', flush=True)

if __name__ == '__main__':
    main()
