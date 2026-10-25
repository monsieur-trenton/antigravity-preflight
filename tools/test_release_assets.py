"""Check that publication rejects asset additions, missing files and symlinks."""
import importlib.util
from pathlib import Path
import tempfile
spec=importlib.util.spec_from_file_location('release_checks',Path(__file__).with_name('check_release.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);assets=root/'assets/cli-review';assets.mkdir(parents=True)
    expected=assets/'hook.py';expected.write_text('pass\n')
    pins={'assets/cli-review/hook.py':{}}
    m.validate_asset_tree(root,pins)
    cases=[('extra file',lambda:(assets/'extra').write_text('x'),lambda:(assets/'extra').unlink()),
           ('extra directory',lambda:(assets/'empty').mkdir(),lambda:(assets/'empty').rmdir()),
           ('symlink',lambda:(assets/'link').symlink_to(expected),lambda:(assets/'link').unlink()),
           ('missing',lambda:expected.unlink(),lambda:expected.write_text('pass\n'))]
    for name,make,undo in cases:
        make()
        try:m.validate_asset_tree(root,pins)
        except ValueError:pass
        else:raise AssertionError(name)
        undo()
for bad in ('ghp_'+'A'*30, 'github_pat_'+'B'*30, '-----BEGIN '+'RSA PRIVATE '+'KEY-----', '/Documents/'+'Codex/x'):
    try:m.scan_text(bad,'control')
    except AssertionError:pass
    else:raise AssertionError('scan_text accepted '+bad[:12])
m.scan_text('an ordinary evidence line','control')
print('PASS: exact asset tree, four rejection controls and four content-scan controls; no provider calls')
