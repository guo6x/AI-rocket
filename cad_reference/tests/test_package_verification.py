"""Delivered-artifact checks, independent of a stored PASS receipt."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import cadquery as cq

from cad_reference import generate_reference as ra02
from cad_reference import generate_sensor_reference as sensor
from cad_reference import verify_package as verifier


class DeliveredPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = tempfile.TemporaryDirectory()
        cls.ra = Path(cls.cases.name) / 'ra02'
        cls.sensors = Path(cls.cases.name) / 'sensors'
        ra02.generate(cls.ra)
        sensor.generate(cls.sensors)

    @classmethod
    def tearDownClass(cls):
        cls.cases.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.package = Path(self.temp.name) / 'package'
        shutil.copytree(self.ra, self.package)

    def read(self):
        return json.loads((self.package / 'validation.json').read_text())

    def write(self, report):
        (self.package / 'validation.json').write_text(json.dumps(report))

    def reject(self, kind='ra02'):
        with self.assertRaises((ValueError, OSError)):
            verifier.verify(self.package, kind)

    def test_verify_all_nine_actual_step_files(self):
        for path, kind, count in [(self.package, 'ra02', 3), (self.sensors, 'sensors', 6)]:
            with self.subTest(kind=kind):
                result = verifier.verify(path, kind)
                self.assertEqual(result['status'], verifier.STATUS)
                self.assertEqual(len(result['verified_models']), count)
                self.assertFalse(result['manufacturing_release'])
                self.assertEqual(result['physical_identity'], 'UNVERIFIED')

    def test_verification_is_read_only(self):
        before = {p.name: p.read_bytes() for p in self.package.iterdir()}
        verifier.verify(self.package, 'ra02')
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.package.iterdir()})

    def test_tampered_step_hash_rejected(self):
        p = next(self.package.glob('*.step'))
        p.write_bytes(p.read_bytes() + b'\n/* changed */\n')
        self.reject()

    def test_self_consistent_wrong_geometry_is_rejected(self):
        report = self.read()
        f = report['exports'][0]['files'][0]
        p = self.package / f['name']
        cq.exporters.export(cq.Workplane('XY').box(170, 16, 3.1, centered=False), str(p))
        f.update(sha256=ra02.sha256(p.read_bytes()), bytes=p.stat().st_size)
        self.write(report)
        self.reject()

    def test_rewritten_dimensions_do_not_override_source(self):
        report = self.read()
        report['exports'][0]['dimensions_mm'][0] = 170
        self.write(report)
        self.reject()

    def test_wrong_datum_with_updated_hash_rejected(self):
        report = self.read()
        f = report['exports'][0]['files'][0]
        p = self.package / f['name']
        cq.exporters.export(cq.Workplane('XY').box(17, 16, 3.1), str(p))
        f.update(sha256=ra02.sha256(p.read_bytes()), bytes=p.stat().st_size)
        self.write(report)
        self.reject()

    def test_missing_and_extra_files_rejected(self):
        extra = self.package / 'PRINT_THIS.stl'
        extra.write_text('unreviewed')
        self.reject()
        extra.unlink()
        next(self.package.glob('*.svg')).unlink()
        self.reject()

    def test_dangerous_path_and_duplicate_file_entries_rejected(self):
        for name in ['../outside.step', '/tmp/outside.step', 'RA02_V11_REFERENCE_ONLY_nominal.step']:
            with self.subTest(name=name):
                original = self.read()
                report = deepcopy(original)
                report['exports'][0]['files'][0]['name'] = name
                self.write(report)
                self.reject()
                self.write(original)

    def test_symlink_file_or_package_rejected(self):
        p = next(self.package.glob('*.step'))
        source = Path(self.temp.name) / 'outside.step'
        p.rename(source)
        p.symlink_to(source)
        self.reject()
        alias = Path(self.temp.name) / 'alias'
        alias.symlink_to(self.ra, target_is_directory=True)
        with self.assertRaises(ValueError): verifier.verify(alias, 'ra02')

    def test_incomplete_or_forged_authority_rejected(self):
        for key, value in [('status', 'INCOMPLETE'), ('manufacturing_release', True),
                           ('physical_identity', 'MEASURED'), ('cad_start', 'PASS'),
                           ('scope', 'MANUFACTURING'), ('warning', 'Fit approved')]:
            with self.subTest(key=key):
                original = self.read()
                report = deepcopy(original)
                report[key] = value
                self.write(report)
                self.reject()
                self.write(original)

    def test_modified_source_receipt_or_generator_rejected(self):
        for field in ['generator_sha256', 'inputs', 'source', 'parameter_rows']:
            with self.subTest(field=field):
                original = self.read()
                report = deepcopy(original)
                if field == 'inputs': report[field]['manifest_sha256'] = '0' * 64
                elif field == 'source': report[field]['revision'] = 'different'
                elif field == 'parameter_rows': report[field][0]['manufacturing_release'] = True
                else: report[field] = '0' * 64
                self.write(report)
                self.reject()
                self.write(original)

    def test_wrong_geometry_statistics_rejected(self):
        for field, value in [('valid_closed_solids', True), ('bbox_mm', [17, 16, 31]),
                             ('origin_mm', [0, 0, 1]), ('envelope_volume_mm3', 0)]:
            with self.subTest(field=field):
                original = self.read()
                report = deepcopy(original)
                report['exports'][0]['step_readback'][field] = value
                self.write(report)
                self.reject()
                self.write(original)

    def test_geometry_scalar_cannot_be_wrapped_in_list(self):
        report = self.read()
        geometry = report['exports'][0]['step_readback']
        geometry['envelope_volume_mm3'] = [geometry['envelope_volume_mm3']]
        self.write(report)
        self.reject()

    def test_missing_notice_and_contradictory_readme_rejected(self):
        p = self.package / 'README.txt'
        p.write_text(p.read_text() + '\nManufacturing approved\n')
        self.reject()

    def test_duplicate_json_keys_and_nonfinite_values_rejected(self):
        p = self.package / 'validation.json'
        for text in ['{"status":"INCOMPLETE","status":"PASS_GEOMETRY_ROUNDTRIP_ONLY"}',
                     '{"value":NaN}', '{"value":Infinity}']:
            with self.subTest(text=text):
                p.write_text(text)
                self.reject()

    def test_missing_duplicate_or_reordered_models_rejected(self):
        for mode in ['missing', 'duplicate', 'reordered']:
            with self.subTest(mode=mode):
                original = self.read()
                report = deepcopy(original)
                if mode == 'missing': report['exports'].pop()
                elif mode == 'duplicate': report['exports'][1] = deepcopy(report['exports'][0])
                else: report['exports'].reverse()
                self.write(report)
                self.reject()
                self.write(original)

    def test_receipt_changed_during_import_rejected(self):
        real_import = cq.importers.importStep
        def import_and_change(path):
            shape = real_import(path)
            report = self.read()
            report['status'] = 'INCOMPLETE'
            self.write(report)
            return shape
        with patch.object(cq.importers, 'importStep', side_effect=import_and_change):
            self.reject()

    def test_invalid_kind_is_not_autodetected_from_claim(self):
        self.reject('board')
        self.reject('sensors')


if __name__ == '__main__':
    unittest.main()
