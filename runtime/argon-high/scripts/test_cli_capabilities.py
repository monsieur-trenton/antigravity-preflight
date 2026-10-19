import sys
sys.dont_write_bytecode = True
"""Source-free process tests for update compatibility; no real CLI/provider."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location('caps', Path(__file__).with_name('cli_capabilities.py'))
caps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(caps)


PROFILE_ID=sys.argv[2] if len(sys.argv)>2 else 'flash-high'
def main(root):
    root.mkdir(exist_ok=False, parents=True)
    cases = []
    modes = {
        'current': None, 'future': None, 'old': None, 'prerelease': None,
        'missing_flag': 'MISSING_FLAGS:--effort',
        'prefix_flag': 'MISSING_FLAGS:--effort',
        'missing_model': 'PINNED_MODEL_UNAVAILABLE_OR_AMBIGUOUS',
        'wrong_label': 'PINNED_MODEL_UNAVAILABLE_OR_AMBIGUOUS',
        'duplicate_model': 'PINNED_MODEL_UNAVAILABLE_OR_AMBIGUOUS',
        'version_failed': 'METADATA_COMMAND_FAILED:VERSION',
        'help_failed': 'METADATA_COMMAND_FAILED:HELP',
        'models_failed': 'METADATA_COMMAND_FAILED:MODELS',
        'invalid_utf8': 'UnicodeDecodeError', 'empty_version': 'VERSION_SHAPE',
        'multiline_version': 'VERSION_SHAPE', 'timeout': 'METADATA_COMMAND_FAILED:HELP',
        'overflow': 'METADATA_COMMAND_FAILED:HELP', 'binary_drift': 'NATIVE_DRIFT',
        'help_stderr': None, 'help_mixed': None,
        'stderr_missing_flag': 'MISSING_FLAGS:--effort',
        'stderr_prefix_flag': 'MISSING_FLAGS:--effort',
        'stderr_invalid_utf8': 'UnicodeDecodeError',
        'split_token': 'MISSING_FLAGS:--effort',
    }
    for family, ending, text in [('ASCII_LF', '\n', 'Metadata'), ('UNICODE_CRLF', '\r\n', '条件')]:
        for mode, expected in modes.items():
            case = root / (family + '-' + mode)
            case.mkdir()
            source = case / 'fake-agy'
            version = {'future': '99.42.0', 'old': '1.3.5', 'prerelease': '2.0.0-preview.7',
                       'empty_version': '', 'multiline_version': '1.3.6\nextra'}.get(mode, '1.3.6')
            flags = list(caps.FLAGS)
            if mode in ('missing_flag', 'prefix_flag', 'stderr_missing_flag', 'stderr_prefix_flag', 'split_token'):
                flags.remove('--effort')
            if mode in ('prefix_flag', 'stderr_prefix_flag'):
                flags.append('--effort-extra')
            models = caps.runtime_profile(PROFILE_ID)['model'] + '\t' + {'flash-high': 'Gemini 3.8 Flash (High)', 'argon-high': 'Gemini 4 Argon (High)'}[PROFILE_ID] + ending
            if mode == 'missing_model':
                models = 'other-model\tOther' + ending
            if mode == 'wrong_label':
                models = caps.runtime_profile(PROFILE_ID)['model'] + '\tOther' + ending
            if mode == 'duplicate_model':
                models += models
            outputs = {'--version': (version + ending).encode(),
                       '--help': (text + ending + ' '.join(flags) + ending).encode(),
                       'models': models.encode()}
            error_outputs = {arg: (text + ending).encode() for arg in outputs}
            if mode in ('help_stderr', 'stderr_missing_flag', 'stderr_prefix_flag'):
                error_outputs['--help'] = outputs['--help']
                outputs['--help'] = b''
            if mode == 'help_mixed':
                outputs['--help'] = (text + ending + ' '.join(flags[:4]) + ending).encode()
                error_outputs['--help'] = (' '.join(flags[4:]) + ending).encode()
            if mode == 'stderr_invalid_utf8':
                error_outputs['--help'] = b'\xff'
            if mode == 'split_token':
                outputs['--help'] += b'--ef'
                error_outputs['--help'] = b'fort'
            if mode == 'invalid_utf8':
                outputs['--help'] = b'\xff'
            code = ('#!/usr/bin/python3 -I\nimport sys,time\nfrom pathlib import Path\n'
                    'outputs=' + repr(outputs) + '\nerrors=' + repr(error_outputs) + '\nmode=' + repr(mode) + '\n'
                    'arg=sys.argv[1]\n'
                    "if mode=='timeout' and arg=='--help': time.sleep(5)\n"
                    "if mode=='binary_drift' and arg=='models':\n"
                    '    Path(' + repr(str(source)) + ").write_bytes(b'changed')\n"
                    "if mode=='overflow' and arg=='--help':\n"
                    "    sys.stdout.buffer.write(b'X'*1048577)\n"
                    "else: sys.stdout.buffer.write(outputs[arg])\n"
                    'sys.stderr.buffer.write(errors[arg])\n'
                    "sys.exit(7 if (mode,arg) in [('version_failed','--version'),('help_failed','--help'),('models_failed','models')] else 0)\n")
            shebang, body = code.split('\n', 1)
            raw = (shebang + '\n' + body.replace('\n', ending)).encode()
            compile(raw, str(source), 'exec')
            source.write_bytes(raw)
            source.chmod(0o755)
            caps.save(case / 'FIXTURE-SYNTAX.json', {
                'status': 'PASS', 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                'completeFinalBytes': True, 'beforeExecution': True})
            result = caps.probe(source, case / 'capture', deadline=.4 if mode == 'timeout' else 5, runtime_profile_id=PROFILE_ID)
            assert result['failure'] == expected, (family, mode, result)
            assert result['status'] == ('STOPPED' if expected else 'PASS_METADATA_CAPABILITIES_ONLY')
            capture = case / 'capture'
            for record in capture.glob('*.json'):
                data = json.loads(record.read_bytes())
                if 'streams' in data:
                    assert data['directChildReaped'] and not data['cleanupFailures']
                    for channel, pin in data['streams'].items():
                        assert caps.identity(capture / (record.stem + '.' + channel)) == pin
            if expected is None:
                assert result['observedVersion'] == version
                assert (capture / 'HELP.stdout').read_bytes() == outputs['--help']
                assert (capture / 'MODELS.stderr').read_bytes() == (text + ending).encode()
            if (capture / 'HELP.stderr').exists() and mode not in ('timeout', 'overflow'):
                assert (capture / 'HELP.stderr').read_bytes() == error_outputs['--help']
            if mode in ('version_failed', 'help_failed', 'models_failed'):
                command = mode.split('_')[0].upper()
                assert json.loads((capture / (command + '.json')).read_bytes())['returncode'] == 7
                assert (capture / (command + '.stdout')).read_bytes() == outputs[{'VERSION':'--version','HELP':'--help','MODELS':'models'}[command]]
                if command != 'MODELS':
                    assert not (capture / 'MODELS.json').exists()
            if mode == 'overflow':
                assert (capture / 'HELP.stdout').stat().st_size == caps.CAP
            if mode == 'binary_drift':
                assert not result['binaryStable']
            cases.append({'family': family, 'case': mode, 'status': 'PASS'})
    caps.save(root / 'RESULT.json', {'status': 'PASS', 'caseCount': len(cases), 'families': 2,
                                    'cases': cases, 'realNativeCalls': 0, 'generativeCalls': 0})
    print('PASS:', len(cases), 'update-capability cases; zero real CLI/provider calls')


if __name__ == '__main__':
    main(Path(sys.argv[1]).resolve())
