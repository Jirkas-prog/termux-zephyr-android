#!/usr/bin/env python3
"""Run input smoke tests on a connected Android emulator (same signing key as app)."""
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SDK = Path(os.environ['ANDROID_HOME'])
TOOLS = SDK / 'build-tools/35.0.0'
JAR = SDK / 'platforms/android-35/android.jar'
BUILD = ROOT / 'build/android-test'
BUILD.mkdir(parents=True, exist_ok=True)


def run(*args):
    return subprocess.run(list(map(str, args)), check=True)


for directory in ('classes', 'dex'):
    (BUILD / directory).mkdir(exist_ok=True)
run(TOOLS / 'aapt2', 'link', '-I', JAR, '--manifest', ROOT / 'tests/android/AndroidManifest.xml', '-o', BUILD / 'unsigned.apk')
run('javac', '--release', '8', '-encoding', 'UTF-8', '-classpath', str(JAR) + os.pathsep + str(ROOT / 'build/classes'), '-d', BUILD / 'classes', ROOT / 'tests/android/SmokeTests.java')
with zipfile.ZipFile(BUILD / 'classes.zip', 'w') as archive:
    for file in (BUILD / 'classes').rglob('*.class'):
        archive.write(file, file.relative_to(BUILD / 'classes'))
run(TOOLS / 'd8', '--min-api', '24', '--lib', JAR, '--output', BUILD / 'dex', BUILD / 'classes.zip')
with zipfile.ZipFile(BUILD / 'unsigned.apk', 'a') as archive:
    archive.write(BUILD / 'dex/classes.dex', 'classes.dex')
run(TOOLS / 'zipalign', '-f', '4', BUILD / 'unsigned.apk', BUILD / 'aligned.apk')
key = os.environ.get('KEYSTORE_PATH', str(ROOT / 'build/development.jks'))
os.environ.setdefault('KEYSTORE_PASSWORD', 'android')
run(TOOLS / 'apksigner', 'sign', '--ks', key, '--ks-key-alias', 'zephyr', '--ks-pass', 'env:KEYSTORE_PASSWORD',
    '--out', BUILD / 'test.apk', BUILD / 'aligned.apk')
adb = [SDK / 'platform-tools/adb']
if os.environ.get('ANDROID_SERIAL'):
    adb += ['-s', os.environ['ANDROID_SERIAL']]
run(*adb, 'install', '-r', ROOT / 'dist/zephyr-termux.apk')
run(*adb, 'install', '-r', BUILD / 'test.apk')
result = subprocess.run(list(map(str, [*adb, 'shell', 'am', 'instrument', '-w', '-e', 'orientation', os.environ.get('SMOKE_ORIENTATION', 'landscape'), 'cz.zephyr.termux.tests/cz.zephyr.termux.SmokeTests'])), capture_output=True, text=True, check=True)
print(result.stdout)
if 'PASS:' not in result.stdout or 'FAIL:' in result.stdout:
    raise SystemExit('Android smoke test failed')
