"""Container smoke test using synthetic ADS-B; never enables a test mode in the app.

Run in a disposable container (no real /data mount):
  docker run --rm --platform linux/amd64 -v "$PWD/adsb_radar/tests:/tests:ro" \
    ha-adsb-radar:0.1.2 python3 /tests/smoke.py
On an ARM test host add: -e MONO_ENV_OPTIONS=--interp
"""
import base64
import json
import html
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

Path('/data').mkdir(exist_ok=True)
Path('/data/options.json').write_text(json.dumps(dict(
    device_serial='', gain=-10, ppm=0,
    vrs_username='smoke', vrs_password='smoke-test-only', latitude=52, longitude=4)))
code = '''import sys
sys.path.insert(0, '/app')
import run
run.dump1090_command = lambda options: ['/usr/local/bin/dump1090', '--net-only',
    '--net-bind-address', '127.0.0.1', '--net-ri-port', '30001',
    '--net-bi-port', '0', '--net-bo-port', '30005', '--net-ro-port', '0',
    '--net-sbs-port', '0', '--quiet']
sys.exit(run.main())
'''
process = subprocess.Popen([sys.executable, '-u', '-c', code])


def get(path, headers=None):
    return urllib.request.urlopen(urllib.request.Request(
        'http://127.0.0.1:8099' + path,
        headers={'X-Ingress-Path': '/api/hassio_ingress/test-prefix',
                 'Host': 'homeassistant.local:8123',
                 'X-Forwarded-Host': 'homeassistant.local:8123',
                 'X-Forwarded-Proto': 'http',
                 'X-Forwarded-For': '192.0.2.10, 172.30.32.1',
                 **(headers or {})}), timeout=30)


try:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError('App exited during startup')
        try:
            urllib.request.urlopen('http://127.0.0.1:8080/VirtualRadar/desktop.html', timeout=2)
            break
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    else:
        raise AssertionError('VRS did not become ready')
    try:
        get('/')
        raise AssertionError('Ingress unexpectedly accepted a non-gateway address')
    except urllib.error.HTTPError as error:
        assert error.code == 403, error.code
    print('PASS: Ingress denies non-gateway requests', flush=True)

    # Emulate gateway requests from loopback only in this disposable test container.
    nginx = Path('/etc/nginx/nginx.conf')
    nginx.write_text(nginx.read_text().replace('allow 172.30.32.2;', 'allow 127.0.0.1;'))
    subprocess.run(['nginx', '-s', 'reload'], check=True)
    time.sleep(1)
    assert b'VirtualRadar/desktop.html' in get('/').read()
    assert b'VirtualRadar/desktop.html' in get('//').read()
    for path in ('//VirtualRadar/desktop.html', '/VirtualRadar//desktop.html'):
        assert '<html' in get(path).read().decode().lower()
    assert 'acList' in json.load(get('//VirtualRadar/AircraftList.json?ldv=0'))
    print('PASS: duplicate-slash Ingress paths and query strings', flush=True)
    page = get('/VirtualRadar/desktop.html').read().decode()
    assert '<html' in page.lower()
    scripts = re.findall(r'<script[^>]*src=["\']([^"\']+)', page, re.I)
    assert scripts, 'No scripts in map page'
    for script in scripts:
        script = html.unescape(script)
        if script.startswith(('http:', 'https:', '//')):
            continue
        path = '/VirtualRadar/' + script if not script.startswith('/') else script
        with get(path) as response:
            assert response.status == 200 and response.read(), script
    print('PASS: map HTML and its scripts through proxy', flush=True)

    try:
        get('/VirtualRadar/WebAdmin/Index.html')
        raise AssertionError('Web Admin accepted anonymous access')
    except urllib.error.HTTPError as error:
        assert error.code == 401, error.code
    auth = base64.b64encode(b'smoke:smoke-test-only').decode()
    assert get('/VirtualRadar/WebAdmin/Index.html', {'Authorization': 'Basic ' + auth}).status == 200
    print('PASS: Web Admin requires and accepts configured credentials', flush=True)

    with socket.create_connection(('127.0.0.1', 30001)) as feed:
        for _ in range(10):
            feed.sendall(b'*8D40621D58C382D690C8AC2863A7;\n*8D40621D58C386435CC412692AD6;\n')
            time.sleep(0.5)
    aircraft = json.load(get('/VirtualRadar/AircraftList.json'))
    assert any(plane.get('Icao') == '40621D' for plane in aircraft['acList']), aircraft
    print('PASS: synthetic ADS-B traverses dump1090 → Beast → VRS aircraft API', flush=True)

    # Reuse the actual VRS-created database, exactly as an upgrade/restart does.
    process.terminate()
    process.wait(timeout=15)
    assert process.returncode == 0, process.returncode
    saved_options = json.loads(Path('/data/options.json').read_text())
    saved_options['vrs_username'] = 'SMOKE'  # VRS usernames are case-insensitive.
    saved_options['vrs_password'] = 'must-not-replace-existing-password'
    Path('/data/options.json').write_text(json.dumps(saved_options))
    process = subprocess.Popen([sys.executable, '-u', '-c', code])
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise AssertionError('App failed to restart with an existing user')
        try:
            with get('/VirtualRadar/WebAdmin/Index.html', {'Authorization': 'Basic ' + auth}) as response:
                assert response.status == 200
                response.read()
            break
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    else:
        raise AssertionError('Existing credentials did not work after restart')
    print('PASS: restart reuses existing user and preserves password', flush=True)
finally:
    process.terminate()
    process.wait(timeout=15)
assert process.returncode == 0, process.returncode
print('PASS: clean shutdown', flush=True)
