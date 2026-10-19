import sys
sys.dont_write_bytecode = True
"""Capture metadata and freeze one CLI candidate; never launches a review.

Version strings are observations, not admission pins. A PASS checks only the
listed interface. Fresh stream controls and init binding remain necessary.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import time

MODEL = 'gemini-3.8-flash-high'
LABEL = 'Gemini 3.8 Flash (High)'
FLAGS = ('--input-format', '--output-format', '--agent', '--model', '--effort',
         '--disable-slash-commands', '--print-timeout', '--new-project')
CAP = 1048576


def identity(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            digest.update(chunk)
    return {'sha256': digest.hexdigest(), 'bytes': path.stat().st_size}


def save(path, data):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def capture(binary, args, out, name, deadline=60):
    """Retain bounded exact bytes and outcome before interpreting any content."""
    data = {'stdout': bytearray(), 'stderr': bytearray()}
    process = None
    failure = None
    cleanup = []
    selector = selectors.DefaultSelector()
    start = time.monotonic()
    try:
        env = dict(os.environ, AGY_CLI_DISABLE_AUTO_UPDATE='true')
        process = subprocess.Popen([str(binary), *args], cwd=out, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
        for name_, pipe in [('stdout', process.stdout), ('stderr', process.stderr)]:
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, name_)
        while selector.get_map():
            if time.monotonic() - start >= deadline:
                raise ValueError('METADATA_TIMEOUT')
            for key, _ in selector.select(.05):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                target = data[key.data]
                remaining = CAP - len(target)
                target.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    raise ValueError('METADATA_OVERFLOW')
        process.wait(timeout=max(.01, deadline - (time.monotonic() - start)))
    except Exception as error:
        failure = str(error) if type(error) is ValueError else type(error).__name__
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except Exception as error:
                cleanup.append(type(error).__name__)
            try:
                process.wait(timeout=5)
            except Exception as error:
                cleanup.append(type(error).__name__)
            for pipe in (process.stdout, process.stderr):
                if pipe is not None:
                    pipe.close()
        selector.close()
        for channel, raw in data.items():
            (out / (name + '.' + channel)).write_bytes(raw)
        row = {'args': args, 'returncode': process.returncode if process else None,
               'failure': failure, 'cleanupFailures': cleanup,
               'directChildReaped': process is not None and process.poll() is not None,
               'elapsedSeconds': round(time.monotonic() - start, 3),
               'streams': {c: identity(out / (name + '.' + c)) for c in data}}
        save(out / (name + '.json'), row)
    return row


def runtime_profile(profile_id):
    # Reject duplicate keys and any schema/content beyond the two commissioned profiles.
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result: raise ValueError('PROFILE_DUPLICATE_KEY')
            result[key] = value
        return result
    path = Path(__file__).resolve().parent.parent / 'RUNTIME-PROFILES.json'
    raw = path.read_bytes()
    registry = json.loads(raw, object_pairs_hook=pairs)
    expected = {'schemaVersion': 1, 'profiles': {'flash-high': {'model': 'gemini-3.8-flash-high', 'label': 'Gemini 3.8 Flash (High)', 'effort': 'high', 'useG1Credits': False}, 'argon-high': {'model': 'gemini-4-argon-high', 'label': 'Gemini 4 Argon (High)', 'effort': 'high', 'useG1Credits': True}}}
    if registry != expected or type(registry.get('schemaVersion')) is not int or any(type(value['useG1Credits']) is not bool for value in registry['profiles'].values()):
        raise ValueError('PROFILE_REGISTRY')
    if type(profile_id) is not str or profile_id not in registry['profiles']:
        raise ValueError('RUNTIME_PROFILE_REQUIRED')
    item = registry['profiles'][profile_id]
    return dict(id=profile_id, model=item['model'], effort=item['effort'], useG1Credits=item['useG1Credits'], registry=identity(path))


def interpret(out, runtime_profile_id='flash-high'):
    selected = runtime_profile(runtime_profile_id)
    model = selected['model']
    label = {'flash-high': 'Gemini 3.8 Flash (High)', 'argon-high': 'Gemini 4 Argon (High)'}[runtime_profile_id]
    # Capture records must already be durable. Do not constrain to one release.
    version = (out / 'VERSION.stdout').read_bytes().decode('utf-8').strip()
    if not version or len(version) > 128 or '\n' in version or '\r' in version:
        raise ValueError('VERSION_SHAPE')
    help_text = '\n'.join((out / ('HELP.' + channel)).read_bytes().decode('utf-8')
                          for channel in ('stdout', 'stderr'))
    tokens = set(re.findall(r'(?<![\w-])--[a-z][a-z0-9-]*', help_text))
    missing = sorted(set(FLAGS) - tokens)
    if missing:
        raise ValueError('MISSING_FLAGS:' + ','.join(missing))
    rows = (out / 'MODELS.stdout').read_bytes().decode('utf-8').splitlines()
    matches = [line.split('\t') for line in rows if line.split('\t')[0] == model]
    if matches != [[model, label]]:
        raise ValueError('PINNED_MODEL_UNAVAILABLE_OR_AMBIGUOUS')
    return {'observedVersion': version, 'model': model, 'effort': 'high', 'runtimeProfile': selected,
            'requiredFlags': list(FLAGS)}


def probe(source, out, deadline=60, runtime_profile_id='flash-high'):
    runtime_profile(runtime_profile_id)
    source = source.resolve(strict=True)
    out.mkdir(exist_ok=False, parents=True)
    before = identity(source)
    save(out / 'NATIVE-BEFORE.json', dict(path=str(source), **before))
    frozen = out / 'runtime' / 'agy'
    frozen.parent.mkdir()
    shutil.copyfile(source, frozen)
    frozen.chmod(0o555)
    failure = None
    details = {}
    try:
        if identity(frozen) != before:
            raise ValueError('FREEZE_MISMATCH')
        for name, args in [('VERSION', ['--version']), ('HELP', ['--help']), ('MODELS', ['models'])]:
            row = capture(frozen, args, out, name, deadline)
            if row['failure'] or row['returncode'] != 0 or row['cleanupFailures']:
                raise ValueError('METADATA_COMMAND_FAILED:' + name)
        details = interpret(out, runtime_profile_id)
    except Exception as error:
        failure = str(error) if type(error) is ValueError else type(error).__name__
    finally:
        try:
            after = identity(source)
            save(out / 'NATIVE-AFTER.json', dict(path=str(source), **after))
            stable = before == after == identity(frozen)
        except Exception:
            stable = False
        if not stable and failure is None:
            failure = 'NATIVE_DRIFT'
        result = {'status': 'STOPPED' if failure else 'PASS_METADATA_CAPABILITIES_ONLY',
                  'failure': failure, 'binaryStable': stable, 'frozenBinary': before,
                  **details, 'generativeCalls': 0, 'qualificationCredit': 0,
                  'scope': 'Metadata only; stream semantics and containment not qualified',
                  'nextRequired': 'Fresh offline stream controls and exact runtime init binding'}
        save(out / 'RESULT.json', result)
    return result


if __name__ == '__main__':
    result = probe(Path(sys.argv[1]), Path(sys.argv[2]), runtime_profile_id=sys.argv[3])
    print(json.dumps(result))
    sys.exit(0 if result['status'] == 'PASS_METADATA_CAPABILITIES_ONLY' else 1)
