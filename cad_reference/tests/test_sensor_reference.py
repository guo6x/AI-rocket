"""Real CAD-kernel round trips and negative provenance/identity cases."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import cadquery as cq
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cad_reference import generate_sensor_reference as sensor
from cad_reference.generate_reference import ReferenceError, check_shape, row_hash, sha256


class SensorReferenceTests(unittest.TestCase):
    def setUp(self):
        self.registry = yaml.safe_load(sensor.REGISTRY.read_bytes())
        self.manifest = json.loads(sensor.MANIFEST.read_bytes())

    def row(self, key='MN-BMP280-PACKAGE-LENGTH'):
        return next(r for r in self.registry['manufacturer_nominal']['parameters'] if r['id'] == key)

    def rebind(self):
        for model in self.manifest['models']:
            for binding in model['parameter_bindings']:
                binding['sha256'] = row_hash(self.row(binding['id']))

    def assertRejected(self):
        with self.assertRaises((ReferenceError, ValueError)):
            sensor.validate_inputs(self.registry, self.manifest)

    def test_reviewed_limits_match_independent_expected_values(self):
        models = sensor.validate_inputs(self.registry, self.manifest)
        self.assertEqual(models[0]['dimensions_mm'], {
            'minimum': [2.9, 2.9, 0.95], 'nominal': [3., 3., 1.], 'maximum': [3.1, 3.1, 1.05]})
        self.assertEqual(models[1]['dimensions_mm'], {
            'minimum': [1.9, 2.4, 0.9], 'nominal': [2., 2.5, 0.95], 'maximum': [2.1, 2.6, 1.]})

    def test_six_actual_step_roundtrips_and_file_hashes(self):
        expected = {
            ('MPU9250', 'minimum'): [2.9, 2.9, .95],
            ('MPU9250', 'nominal'): [3., 3., 1.],
            ('MPU9250', 'maximum'): [3.1, 3.1, 1.05],
            ('BMP280', 'minimum'): [1.9, 2.4, .9],
            ('BMP280', 'nominal'): [2., 2.5, .95],
            ('BMP280', 'maximum'): [2.1, 2.6, 1.],
        }
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'new'
            report = sensor.generate(out)
            self.assertEqual(report['status'], 'PASS_GEOMETRY_ROUNDTRIP_ONLY')
            self.assertEqual(len(report['exports']), 6)
            self.assertFalse(report['manufacturing_release'])
            self.assertEqual(report['physical_identity'], 'UNVERIFIED')
            self.assertEqual(report['cad_start'], 'UNCHANGED_BLOCKED')
            self.assertEqual(report['datum'], sensor.DATUM)
            for export in report['exports']:
                dims = expected.pop((export['model_id'], export['variant']))
                self.assertEqual(export['dimensions_mm'], dims)
                for file in export['files']:
                    p = out / file['name']
                    self.assertEqual(file['sha256'], sha256(p.read_bytes()))
                    if p.suffix == '.step':
                        check_shape(cq.importers.importStep(str(p)).val(), dims)
            self.assertFalse(expected)
            self.assertIn('NOT the GY-91 board', (out / 'README.txt').read_text())

    def test_explicit_bmp_tolerances_not_general_tolerance(self):
        # The drawing has explicit XY +/-0.10; its general +/-0.05 does not replace it.
        self.manifest['models'][1]['dimensions_mm']['minimum'] = [1.95, 2.45, .9]
        self.assertRejected()

    def test_do_not_add_substrate_or_seating_height(self):
        for index, height in [(0, 1.02), (1, 1.08)]:
            with self.subTest(index=index):
                old = deepcopy(self.manifest)
                self.manifest['models'][index]['dimensions_mm']['nominal'][2] = height
                self.assertRejected()
                self.manifest = old

    def test_source_digest_revision_url_page_required(self):
        for field, value in [('pdf_sha256', '0' * 64), ('revision', 'new'),
                             ('url', 'https://example.com/unreviewed.pdf'), ('page', 37),
                             ('review_status', 'TEXT_ONLY')]:
            with self.subTest(field=field):
                old = deepcopy(self.manifest)
                self.manifest['models'][1]['source'][field] = value
                self.assertRejected()
                self.manifest = old

    def test_unknowns_and_identity_remain_unknown(self):
        for feature in sensor.UNKNOWN:
            with self.subTest(feature=feature):
                self.manifest['unknown_features'][feature] = 0
                self.assertRejected()
                self.manifest['unknown_features'][feature] = None
        for field, value in [('manufacturing_release', True), ('physical_identity', 'VERIFIED'),
                             ('datum', 'SENSOR_AXES'), ('scope', 'GY91_BOARD'), ('schema_version', True)]:
            with self.subTest(field=field):
                old = deepcopy(self.manifest)
                self.manifest[field] = value
                self.assertRejected()
                self.manifest = old

    def test_row_change_rejected_even_if_value_unchanged(self):
        self.row()['source_revision'] = 'new unknown revision'
        self.assertRejected()

    def test_unreviewed_receipt_claims_and_nested_fields_rejected(self):
        for field, value in [('model_claim', 'GY-91 measured fit-approved board'),
                             ('dimension_basis', 'sensor axes verified'),
                             ('manufacturing_release', True), ('scope', 'FLIGHT_RELEASE')]:
            with self.subTest(field=field):
                old = deepcopy(self.manifest)
                self.manifest['models'][0][field] = value
                self.assertRejected()
                self.manifest = old
        for path in ('root', 'source', 'binding'):
            with self.subTest(path=path):
                old = deepcopy(self.manifest)
                target = {'root': self.manifest, 'source': self.manifest['models'][0]['source'],
                          'binding': self.manifest['models'][0]['parameter_bindings'][0]}[path]
                target['manufacturing_release'] = True
                self.assertRejected()
                self.manifest = old

    def test_rehash_does_not_bypass_critical_row_checks(self):
        for field, value in [('unit', 'cm'), ('value', True), ('asset_id', 'A-DIFFERENT-BOARD'),
                             ('conflict', True), ('model_status', 'MEASURED'),
                             ('design_scope', 'board_fit'), ('tolerance', .1),
                             ('source_url', 'https://example.com/fake.pdf'),
                             ('source_revision', 'new'), ('model_claim', 'GY-91 board')]:
            with self.subTest(field=field):
                old = deepcopy(self.registry)
                self.row()[field] = value
                self.rebind()
                self.assertRejected()
                self.registry = old
                self.rebind()

    def test_missing_duplicate_and_reordered_bindings(self):
        for mode in ('missing', 'duplicate', 'reordered', 'extra_model'):
            with self.subTest(mode=mode):
                old = deepcopy(self.manifest)
                bindings = self.manifest['models'][0]['parameter_bindings']
                if mode == 'missing': bindings.pop()
                elif mode == 'duplicate': bindings[1] = deepcopy(bindings[0])
                elif mode == 'reordered': bindings.reverse()
                else: self.manifest['models'].append(deepcopy(self.manifest['models'][0]))
                self.assertRejected()
                self.manifest = old

    def test_duplicate_registry_id_rejected(self):
        self.registry['manufacturer_nominal']['parameters'].append(deepcopy(self.row()))
        self.assertRejected()

    def test_invalid_inputs_leave_no_output_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest_path, out = Path(temp) / 'invalid.json', Path(temp) / 'new'
            self.manifest['models'][1]['dimensions_mm']['nominal'][0] = float('nan')
            manifest_path.write_text(json.dumps(self.manifest))
            with self.assertRaises(ValueError):
                sensor.generate(out, manifest_path=manifest_path)
            self.assertFalse(out.exists())

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            marker = out / 'validation.json'
            marker.write_text('previous evidence')
            with self.assertRaises(FileExistsError): sensor.generate(out)
            self.assertEqual(marker.read_text(), 'previous evidence')

    def test_import_failure_leaves_incomplete_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'new'
            with patch('cadquery.importers.importStep', side_effect=RuntimeError('readback failed')):
                with self.assertRaisesRegex(RuntimeError, 'readback failed'): sensor.generate(out)
            receipt = json.loads((out / 'validation.json').read_text())
            self.assertEqual(receipt['status'], 'INCOMPLETE')
            self.assertEqual(receipt['exports'], [])

    def test_export_failure_leaves_incomplete_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'new'
            with patch('cadquery.exporters.export', side_effect=RuntimeError('export failed')):
                with self.assertRaisesRegex(RuntimeError, 'export failed'): sensor.generate(out)
            receipt = json.loads((out / 'validation.json').read_text())
            self.assertEqual(receipt['status'], 'INCOMPLETE')

    def test_wrong_geometry_datum_or_unit_fails(self):
        size = [2., 2.5, .95]
        for model in [cq.Workplane('XY').box(20, 25, 9.5, centered=False),
                      cq.Workplane('XY').box(*size),
                      cq.Workplane('XY').box(*size, centered=False).translate((1, 0, 0))]:
            with self.subTest(model=model):
                with self.assertRaises(ReferenceError): check_shape(model.val(), size)


if __name__ == '__main__':
    unittest.main()
