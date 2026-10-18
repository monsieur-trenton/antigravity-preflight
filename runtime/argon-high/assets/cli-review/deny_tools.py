"""Default-deny native hook. No invocation arguments or tool payload are retained."""
import json
import sys
from pathlib import Path
import os
import re

decision = 'deny'
try:
    event = json.loads(sys.stdin.read(65537))
    name = event.get('toolCall', {}).get('name')
    if name == 'finish':
        decision = 'allow'
    destination = os.environ.get('AGY_PREFLIGHT_AUDIT')
    if destination and isinstance(name, str) and re.fullmatch(r'[a-z_]{1,64}', name):
        with Path(destination).open('a') as audit:
            audit.write(json.dumps({'tool': name, 'decision': decision}) + '\n')
except Exception:
    pass
print(json.dumps({"decision": decision, "reason": "Only internal report completion is allowed; operational tools are denied."}))
