"""Synthetic stage producers exercise the real publication wrapper offline."""
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class ValidationRefreshTests(unittest.TestCase):
    def setup_root(self, directory):
        root = Path(directory)
        (root/'scripts').mkdir()
        source = Path(__file__).resolve().parents[1]/'scripts/refresh_validation.sh'
        shutil.copyfile(source, root/'scripts/refresh_validation.sh')
        for name, value in [('build_shadow_checkpoint.py', {'semantic_eligibility':'ALL_REVIEW_PRICING_DISABLED', 'generated_at':'fixture'}), ('audit_resolutions.py', {'pricing_eligible':False, 'generated_at':'fixture'})]:
            (root/'scripts'/name).write_text('import json,sys\nfrom pathlib import Path\nPath(sys.argv[sys.argv.index("--output")+1]).write_text(json.dumps('+repr(value)+'))\n')
        return root

    def run_wrapper(self, root):
        return subprocess.run(['bash', str(root/'scripts/refresh_validation.sh')], capture_output=True, text=True, timeout=10)

    def test_success_publishes_complete_hashed_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.setup_root(directory)
            result=self.run_wrapper(root)
            self.assertEqual(result.returncode,0,result.stderr)
            directory=root/'data/shadow/validation'
            manifest=json.loads((directory/'latest.json').read_text())
            self.assertEqual(set(manifest['files']),{'checkpoint.json','resolutions.json'})
            for name,digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((directory/manifest['generation']/name).read_bytes()).hexdigest(),digest)
            self.assertEqual(list(directory.glob('.stage.*')),[])

    def test_failed_second_stage_preserves_previous_pointer(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.setup_root(directory)
            latest=root/'data/shadow/validation/latest.json'
            latest.parent.mkdir(parents=True)
            latest.write_text('{"generation":"previous-fixture"}\n')
            before=latest.read_bytes()
            (root/'scripts/audit_resolutions.py').write_text('raise SystemExit(9)\n')
            result=self.run_wrapper(root)
            self.assertEqual(result.returncode,9)
            self.assertEqual(latest.read_bytes(),before)
            self.assertEqual(list(latest.parent.glob('.stage.*')),[])

    def test_eligibility_promotion_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=self.setup_root(directory)
            (root/'scripts/audit_resolutions.py').write_text('import sys,json\nfrom pathlib import Path\nPath(sys.argv[-1]).write_text(json.dumps({"pricing_eligible":True,"generated_at":"fixture"}))\n')
            result=self.run_wrapper(root)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((root/'data/shadow/validation/latest.json').exists())
