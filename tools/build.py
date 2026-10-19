#!/usr/bin/env python3
"""Build the small native Android app using JDK + official Android SDK only."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    subprocess.run(list(map(str, args)), check=True)


def main():
    sdk = Path(os.environ.get('ANDROID_HOME', os.environ.get('ANDROID_SDK_ROOT', '')))
    platform = sdk / 'platforms/android-35/android.jar'
    tools = sdk / 'build-tools/35.0.0'
    if not platform.exists() or not tools.exists():
        raise SystemExit('Install Android SDK platforms;android-35 and build-tools;35.0.0. Set ANDROID_HOME.')
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    # Only disposable children of this build directory are recreated.
    for name in ('generated', 'classes', 'dex'):
        directory = build / name
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir()
    config = json.loads((ROOT / 'environment.json').read_text())
    run(tools / 'aapt2', 'compile', '--dir', ROOT / 'android/res', '-o', build / 'resources.zip')
    run(tools / 'aapt2', 'link', '-I', platform, '--manifest', ROOT / 'android/AndroidManifest.xml',
        '--java', build / 'generated', '--version-code', config['version_code'], '--version-name', config['version'],
        '-o', build / 'unsigned.apk', build / 'resources.zip')
    sources = sorted((ROOT / 'android/src').rglob('*.java')) + sorted((build / 'generated').rglob('*.java'))
    run('javac', '-encoding', 'UTF-8', '--release', '8', '-classpath', platform,
        '-d', build / 'classes', *sources)
    with zipfile.ZipFile(build / 'classes.zip', 'w') as archive:
        for file in sorted((build / 'classes').rglob('*.class')):
            archive.write(file, file.relative_to(build / 'classes'))
    run(tools / 'd8', '--min-api', '24', '--lib', platform, '--output', build / 'dex', build / 'classes.zip')
    with zipfile.ZipFile(build / 'unsigned.apk', 'a', zipfile.ZIP_DEFLATED) as apk:
        for dex in (build / 'dex').glob('*.dex'):
            apk.write(dex, dex.name)
    run(tools / 'zipalign', '-f', '4', build / 'unsigned.apk', build / 'aligned.apk')
    key = os.environ.get('KEYSTORE_PATH')
    alias = os.environ.get('KEY_ALIAS', 'zephyr')
    if not key:
        key = str(build / 'development.jks')
        os.environ['KEYSTORE_PASSWORD'] = 'android'
        if not Path(key).exists():
            run('keytool', '-genkeypair', '-keystore', key, '-alias', alias, '-keyalg', 'RSA', '-keysize', '3072',
                '-validity', '10000', '-dname', 'CN=Zephyr Development', '-storepass:env', 'KEYSTORE_PASSWORD', '-keypass:env', 'KEYSTORE_PASSWORD')
        print('Development signature. Set KEYSTORE_PATH and KEYSTORE_PASSWORD for releases.')
    if not os.environ.get('KEYSTORE_PASSWORD'):
        raise SystemExit('KEYSTORE_PASSWORD is required.')
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    output = dist / 'zephyr-termux.apk'
    run(tools / 'apksigner', 'sign', '--ks', key, '--ks-key-alias', alias, '--ks-pass', 'env:KEYSTORE_PASSWORD',
        '--key-pass', 'env:KEYSTORE_PASSWORD', '--out', output, build / 'aligned.apk')
    run(tools / 'apksigner', 'verify', '--verbose', output)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    (dist / 'SHA256SUMS.txt').write_text(digest + '  zephyr-termux.apk\n')
    print(str(output))


if __name__ == '__main__':
    main()
