"""QA archives must be self-verifying and reject escaped/missing payloads."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def module(name):
    path=ROOT/'scripts'/f'{name}.py'
    spec=importlib.util.spec_from_file_location(name,path)
    loaded=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded

class BundleTest(unittest.TestCase):
    def test_archive_manifest_detects_changed_files(self):
        bundle,verifier=module('bundle'),module('verify_bundle')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source';root.mkdir()
            (root/'README.md').write_text('QA fixture\n')
            (root/'src').mkdir();(root/'src/example.cpp').write_text('int main() {}\n')
            archive=Path(tmp)/'bundle.zip'
            bundle.write_bundle(root,['README.md','src/example.cpp'],archive)
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip())
                z.extractall(Path(tmp)/'extract')
            extracted=Path(tmp)/'extract/prento'
            self.assertEqual(verifier.verify(extracted),3) # Two payloads + bundle metadata.
            metadata=json.loads((extracted/'BUNDLE.json').read_text())
            self.assertEqual(metadata['payload_files'],3)
            self.assertEqual(metadata['source_payload_files'],2)
            self.assertEqual(metadata['archive_files'],4)
            (extracted/'README.md').write_text('changed\n')
            with self.assertRaises(ValueError):verifier.verify(extracted)

    def test_bundle_rejects_escape_and_symlinks(self):
        bundle=module('bundle')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source';root.mkdir()
            outside=Path(tmp)/'outside';outside.write_text('outside')
            (root/'link').symlink_to(outside)
            for path in ('../outside','link','missing'):
                with self.assertRaises(ValueError):
                    bundle.write_bundle(root,[path],Path(tmp)/'bad.zip')

    def test_strict_verification_rejects_unlisted_files(self):
        bundle,verifier=module('bundle'),module('verify_bundle')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source';root.mkdir()
            (root/'README.md').write_text('QA fixture\n')
            archive=Path(tmp)/'bundle.zip'
            bundle.write_bundle(root,['README.md'],archive)
            with zipfile.ZipFile(archive) as z:z.extractall(Path(tmp)/'extract')
            extracted=Path(tmp)/'extract/prento'
            self.assertEqual(verifier.verify(extracted,strict=True),2)
            (extracted/'extra.py').write_text('unexpected\n')
            self.assertEqual(verifier.verify(extracted),2)
            with self.assertRaisesRegex(ValueError,'unlisted'):
                verifier.verify(extracted,strict=True)

    def test_bundle_rejects_reserved_metadata_names(self):
        bundle=module('bundle')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('BUNDLE.json','MANIFEST.sha256'):
                (root/name).write_text('reserved\n')
                with self.assertRaisesRegex(ValueError,'reserved'):
                    bundle.write_bundle(root,[name],root/'output.zip')
