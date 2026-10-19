import sys
sys.dont_write_bytecode = True
#!/usr/bin/env python3
"""Local snapshot views and quotation checks; no model calls or review admission."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


class Invalid(ValueError):
    pass


def require(condition, label):
    if not condition:
        raise Invalid(label)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def load_json(path):
    def nonfinite(_):
        raise Invalid('NONFINITE_JSON')
    return json.loads(Path(path).read_bytes().decode('utf-8'),
                      object_pairs_hook=unique_object, parse_constant=nonfinite)


def source_lines(data):
    """LF is the line delimiter; CRLF loses only its line-ending CR."""
    text = data.decode('utf-8')
    if not text:
        return []
    parts = text.split('\n')
    lines = [part[:-1] if part.endswith('\r') else part for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def read_sources(inventory_path):
    inventory_path = Path(inventory_path)
    inventory = load_json(inventory_path)
    require(isinstance(inventory, dict) and isinstance(inventory.get('sources'), list),
            'INVALID_INVENTORY')
    require(bool(inventory['sources']), 'EMPTY_INVENTORY')
    root = inventory_path.resolve().parent
    sources = {}
    for row in inventory['sources']:
        require(isinstance(row, dict), 'INVALID_SOURCE_ROW')
        name = row.get('id')
        require(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_-]+', name),
                'INVALID_SOURCE_ID')
        require(name not in sources, 'DUPLICATE_SOURCE_ID')
        pin = row.get('sha256')
        require(isinstance(pin, str) and re.fullmatch(r'[0-9a-f]{64}', pin),
                'INVALID_SOURCE_HASH')
        relative = row.get('path')
        require(isinstance(relative, str) and bool(relative), 'INVALID_SOURCE_PATH')
        path = Path(relative)
        require(not path.is_absolute() and '..' not in path.parts, 'SOURCE_PATH_ESCAPE')
        source = root
        for part in path.parts:
            source = source / part
            require(not source.is_symlink(), 'SOURCE_SYMLINK')
        require(source.is_file(), 'SOURCE_NOT_REGULAR')
        data = source.read_bytes()
        require(hashlib.sha256(data).hexdigest() == pin, 'SOURCE_HASH_MISMATCH')
        sources[name] = {'sha256': pin, 'lines': source_lines(data)}
    return sources


def render(sources):
    chunks = ['NUMBERED READING VIEW — derived; original snapshots retain their hashes.\n']
    for name, source in sources.items():
        chunks.append(f"\nSOURCE {name} sha256={source['sha256']} lines={len(source['lines'])}\n")
        chunks.extend(f'[{name}:{line}] {body}\n'
                      for line, body in enumerate(source['lines'], 1))
    return ''.join(chunks)


def check(sources, ledger):
    require(isinstance(ledger, dict) and isinstance(ledger.get('citations'), list),
            'INVALID_LEDGER')
    require(bool(ledger['citations']), 'EMPTY_LEDGER')
    seen = set()
    checked = 0
    for row in ledger['citations']:
        require(isinstance(row, dict), 'INVALID_CITATION_ROW')
        identity = row.get('id')
        require(isinstance(identity, str) and bool(identity.strip()), 'INVALID_CITATION_ID')
        require(identity not in seen, 'DUPLICATE_CITATION_ID')
        seen.add(identity)
        source = row.get('source')
        require(isinstance(source, str) and source in sources, 'UNKNOWN_SOURCE')
        line = row.get('line')
        require(type(line) is int and line > 0, 'INVALID_LINE')
        quote = row.get('quote')
        require(isinstance(quote, str) and bool(quote.strip())
                and '\n' not in quote and '\r' not in quote, 'INVALID_QUOTE')
        require(line <= len(sources[source]['lines']), 'LINE_OUT_OF_RANGE')
        require(quote in sources[source]['lines'][line - 1], 'QUOTE_MISMATCH')
        checked += 1
    return checked


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    view = commands.add_parser('render')
    view.add_argument('inventory')
    view.add_argument('output', help='new file for the derived numbered reading view')
    verify = commands.add_parser('check')
    verify.add_argument('inventory')
    verify.add_argument('ledger')
    args = parser.parse_args(argv)
    try:
        sources = read_sources(args.inventory)
        if args.command == 'render':
            with Path(args.output).open('x', encoding='utf-8', newline='\n') as output:
                output.write(render(sources))
            result = {'status': 'VIEW_WRITTEN', 'sources': len(sources)}
        else:
            count = check(sources, load_json(args.ledger))
            result = {'status': 'CITATIONS_MATCHED', 'citations': count,
                      'scope': 'SUPPLIED_LEDGER_ONLY_NOT_REVIEW_ADMISSION'}
    except (Invalid, OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        # No raw source, quote or host path is echoed in a failure receipt.
        reason = str(error) if isinstance(error, Invalid) else type(error).__name__
        print(json.dumps({'status': 'STOPPED', 'reason': reason,
                          'remainingChecks': 'UNRUN'}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
