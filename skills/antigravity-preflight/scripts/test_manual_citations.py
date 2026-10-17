"""Exercise the saved local utility through its real CLI, with no provider access."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).with_name('manual_citations.py')


class CitationTests(unittest.TestCase):
    def test_both_fixture_families(self):
        scenarios = []
        for family, newline, word in [('ASCII_LF', '\n', 'required'),
                                      ('UNICODE_CRLF', '\r\n', '必須 café')]:
            for case in ['valid', 'wrong_line', 'reversed_quote', 'zero', 'negative',
                         'bool', 'float', 'too_large', 'unknown_source', 'empty_quote',
                         'multiline_quote', 'duplicate_id', 'changed_hash',
                         'duplicate_source', 'escape', 'symlink', 'empty_ledger',
                         'duplicate_json', 'invalid_utf8', 'unicode_separator',
                         'no_terminal_newline', 'empty_source', 'failure_precedence',
                         'render', 'render_no_overwrite']:
                with self.subTest(family=family, case=case), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    body = newline.join(['fixed equality', word, 'last']) + newline
                    expected = None
                    if case == 'unicode_separator':
                        body = 'first\u2028still first' + newline + word
                    if case == 'no_terminal_newline':
                        body = 'first' + newline + word
                    if case == 'empty_source':
                        body = ''
                    data = body.encode('utf-8')
                    if case == 'invalid_utf8':
                        data = b'\xff\n'
                    (root / 'source.txt').write_bytes(data)
                    row = {'id': 'S01', 'path': 'source.txt',
                           'sha256': hashlib.sha256(data).hexdigest()}
                    citation = {'id': 'F01-P1', 'source': 'S01', 'line': 2, 'quote': word}
                    citations = [citation]
                    rows = [row]
                    if case == 'wrong_line':
                        citation['line'] = 1
                        expected = 'QUOTE_MISMATCH'
                    elif case == 'reversed_quote':
                        citation['quote'] = word[::-1]
                        expected = 'QUOTE_MISMATCH'
                    elif case in ['zero', 'negative', 'bool', 'float']:
                        citation['line'] = {'zero': 0, 'negative': -1, 'bool': True, 'float': 2.0}[case]
                        expected = 'INVALID_LINE'
                    elif case == 'too_large':
                        citation['line'] = 4
                        expected = 'LINE_OUT_OF_RANGE'
                    elif case == 'unknown_source':
                        citation['source'] = 'S02'
                        expected = 'UNKNOWN_SOURCE'
                    elif case in ['empty_quote', 'multiline_quote']:
                        citation['quote'] = ' ' if case == 'empty_quote' else 'fixed\nequality'
                        expected = 'INVALID_QUOTE'
                    elif case == 'duplicate_id':
                        citations.append(dict(citation))
                        expected = 'DUPLICATE_CITATION_ID'
                    elif case == 'changed_hash':
                        row['sha256'] = '0' * 64
                        expected = 'SOURCE_HASH_MISMATCH'
                    elif case == 'duplicate_source':
                        rows.append(dict(row))
                        expected = 'DUPLICATE_SOURCE_ID'
                    elif case == 'escape':
                        row['path'] = '../source.txt'
                        expected = 'SOURCE_PATH_ESCAPE'
                    elif case == 'symlink':
                        (root / 'alias.txt').symlink_to(root / 'source.txt')
                        row['path'] = 'alias.txt'
                        expected = 'SOURCE_SYMLINK'
                    elif case == 'empty_ledger':
                        citations = []
                        expected = 'EMPTY_LEDGER'
                    elif case == 'duplicate_json':
                        expected = 'DUPLICATE_JSON_KEY'
                    elif case == 'invalid_utf8':
                        expected = 'UnicodeDecodeError'
                    elif case == 'empty_source':
                        expected = 'LINE_OUT_OF_RANGE'
                    elif case == 'failure_precedence':
                        citation['line'] = 1
                        citations.append({'id': 'later', 'source': 'S99', 'line': 1, 'quote': 'secret'})
                        expected = 'QUOTE_MISMATCH'
                    inventory = root / 'inventory.json'
                    inventory.write_text(json.dumps({'sources': rows}), encoding='utf-8')
                    ledger = root / 'ledger.json'
                    ledger.write_text(json.dumps({'citations': citations}), encoding='utf-8')
                    if case == 'duplicate_json':
                        ledger.write_text('{"citations": [], "citations": []}', encoding='utf-8')
                    args = ['check', str(inventory), str(ledger)]
                    if case.startswith('render'):
                        output = root / 'view.txt'
                        args = ['render', str(inventory), str(output)]
                        if case == 'render_no_overwrite':
                            output.write_text('preserve', encoding='utf-8')
                            expected = 'FileExistsError'
                    process = subprocess.run([sys.executable, '-I', str(SCRIPT), *args],
                                             capture_output=True, text=True, timeout=10)
                    self.assertEqual(process.stderr, '')
                    result = json.loads(process.stdout)
                    self.assertEqual(process.returncode, 1 if expected else 0)
                    if expected:
                        self.assertEqual(result, {'status': 'STOPPED', 'reason': expected,
                                                  'remainingChecks': 'UNRUN'})
                        self.assertNotIn(word, process.stdout)
                        self.assertNotIn(str(root), process.stdout)
                    elif case == 'render':
                        self.assertEqual(result['status'], 'VIEW_WRITTEN')
                        self.assertIn('[S01:2] ' + word + '\n', output.read_text(encoding='utf-8'))
                        self.assertNotIn('[S01:4]', output.read_text(encoding='utf-8'))
                    else:
                        self.assertEqual(result['status'], 'CITATIONS_MATCHED')
                        self.assertEqual(result['citations'], 1)
                        self.assertEqual(result['scope'], 'SUPPLIED_LEDGER_ONLY_NOT_REVIEW_ADMISSION')
                    if case == 'render_no_overwrite':
                        self.assertEqual(output.read_text(), 'preserve')
                    scenarios.append(f'{family}/{case}')
        self.assertEqual(len(scenarios), 50)
        print(json.dumps({'scenarios': 50, 'families': 2, 'savedCliExecutions': 50,
                          'providerCalls': 0, 'cases': scenarios}))


if __name__ == '__main__':
    unittest.main()
