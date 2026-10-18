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
print('PASS: exact asset tree and four rejection controls; no provider calls')
