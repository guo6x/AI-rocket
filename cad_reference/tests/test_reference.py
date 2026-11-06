from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import yaml
from cad_reference.generate_reference import (
    MANIFEST, REGISTRY, ReferenceError, check_shape, generate, row_hash, validate_inputs,
)


class ReferenceInputTests(unittest.TestCase):
    def setUp(self):
        self.registry = yaml.safe_load(REGISTRY.read_text())
        self.manifest = json.loads(MANIFEST.read_text())

    def row(self, index=0):
        ident = self.manifest['parameter_bindings'][index]['id']
        return next(r for r in self.registry['manufacturer_nominal']['parameters'] if r['id'] == ident)

    def rebind(self, index=0):
        self.manifest['parameter_bindings'][index]['sha256'] = row_hash(self.row(index))

    def test_known_inputs(self):
        dims, tol, _ = validate_inputs(self.registry, self.manifest)
        self.assertEqual(dims, [17, 16, 3.2])
        self.assertEqual(tol, 0.1)

    def test_changed_source_is_not_silently_used(self):
        self.row()['value'] = 18
        with self.assertRaisesRegex(ReferenceError, 'source changed'):
            validate_inputs(self.registry, self.manifest)

    def test_missing_and_duplicate_parameters(self):
        for operation in ('missing', 'duplicate'):
            with self.subTest(operation=operation):
                r = deepcopy(self.registry)
                rows = r['manufacturer_nominal']['parameters']
                if operation == 'missing':
                    rows.remove(next(x for x in rows if x['id'] == self.row()['id']))
                else:
                    rows.append(deepcopy(self.row()))
                with self.assertRaises(ReferenceError):
                    validate_inputs(r, self.manifest)

    def test_forged_metadata_rejected_even_with_updated_digest(self):
        mutations = {'unit': 'cm', 'evidence_level': 'MEASURED', 'asset_id': 'AST-SENSOR-GY91-001',
                     'design_scope': 'chip_package_reference_only', 'conflict': True,
                     'model_status': 'CONFIRMED_PRESENT', 'design_use': 'MANUFACTURING',
                     'property': 'package_length', 'source_url': 'https://example.com/guess'}
        for key, value in mutations.items():
            with self.subTest(field=key):
                self.setUp()
                self.row()[key] = value
                self.rebind()
                with self.assertRaises(ReferenceError):
                    validate_inputs(self.registry, self.manifest)

    def test_invalid_dimensions(self):
        for value in (None, 0, -1, True, '17', float('inf'), float('nan')):
            with self.subTest(value=value):
                self.setUp()
                self.row()['value'] = value
                with self.assertRaises(ValueError):
                    self.rebind()
                    validate_inputs(self.registry, self.manifest)

    def test_height_tolerance_required(self):
        for value in (None, 0, -0.1, 3.2, True):
            with self.subTest(value=value):
                self.setUp()
                self.row(2)['tolerance'] = value
                self.rebind(2)
                with self.assertRaises(ReferenceError):
                    validate_inputs(self.registry, self.manifest)

    def test_unknown_geometry_cannot_be_backfilled(self):
        for key in self.manifest['unknown_features']:
            with self.subTest(feature=key):
                m = deepcopy(self.manifest)
                m['unknown_features'][key] = 0
                with self.assertRaises(ReferenceError):
                    validate_inputs(self.registry, m)

    def test_no_other_model_enabled(self):
        self.manifest['enabled_model'] = 'esp01s'
        with self.assertRaisesRegex(ReferenceError, 'only the reviewed'):
            validate_inputs(self.registry, self.manifest)

    def test_cannot_promote_to_approved_hardware(self):
        for key, value in [('manufacturing_release', True), ('physical_identity', 'MEASURED'),
                           ('scope', 'ASSEMBLY'), ('schema_version', 2)]:
            with self.subTest(field=key):
                m = deepcopy(self.manifest)
                m[key] = value
                with self.assertRaises(ReferenceError):
                    validate_inputs(self.registry, m)

    def test_unreviewed_pdf_rejected(self):
        self.manifest['source']['review_status'] = 'SEARCH_SNIPPET_ONLY'
        with self.assertRaises(ReferenceError):
            validate_inputs(self.registry, self.manifest)

    def test_unreviewed_pdf_digest_or_revision_rejected(self):
        for key, value in [('pdf_sha256', 'x' * 64), ('revision', 'unreviewed revision')]:
            with self.subTest(field=key):
                m = deepcopy(self.manifest)
                m['source'][key] = value
                with self.assertRaisesRegex(ReferenceError, 'independent review'):
                    validate_inputs(self.registry, m)

    def test_length_tolerance_requires_review(self):
        self.row()['tolerance'] = 0.1
        self.rebind()
        with self.assertRaisesRegex(ReferenceError, 'separate review'):
            validate_inputs(self.registry, self.manifest)


class ActualKernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Missing CadQuery is an error, NOT a silently skipped success.
        import cadquery as cq
        cls.cq = cq

    def test_real_roundtrip_all_three_thicknesses(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / 'output'
            report = generate(dest)
            self.assertEqual(report['status'], 'PASS_GEOMETRY_ROUNDTRIP_ONLY')
            for row, expected in zip(report['exports'], [3.1, 3.2, 3.3]):
                self.assertAlmostEqual(row['dimensions_mm'][2], expected, places=9)
            self.assertEqual(len(list(dest.glob('*.step'))), 3)
            self.assertEqual(len(list(dest.glob('*.svg'))), 3)
            for r in report['exports']:
                self.assertAlmostEqual(r['step_readback']['envelope_volume_mm3'],
                                       17 * 16 * r['dimensions_mm'][2], places=7)
            with self.assertRaises(FileExistsError):
                generate(dest)

    def test_dimension_error_detected(self):
        shape = self.cq.Workplane('XY').box(170, 16, 3.2, centered=(False, False, False)).val()
        with self.assertRaisesRegex(ReferenceError, 'dimensions'):
            check_shape(shape, [17, 16, 3.2])

    def test_datum_error_detected(self):
        shape = self.cq.Workplane('XY').box(17, 16, 3.2).val()
        with self.assertRaisesRegex(ReferenceError, 'datum'):
            check_shape(shape, [17, 16, 3.2])

    def test_compound_is_not_a_single_component(self):
        a = self.cq.Workplane('XY').box(17,16,3.2).val()
        b = a.translate((40,0,0))
        with self.assertRaisesRegex(ReferenceError, 'one valid closed solid'):
            check_shape(self.cq.Compound.makeCompound([a,b]), [17,16,3.2])

    def test_surface_is_not_a_solid(self):
        face = self.cq.Workplane('XY').box(17,16,3.2).val().Faces()[0]
        with self.assertRaisesRegex(ReferenceError, 'one valid closed solid'):
            check_shape(face, [17,16,3.2])

    def test_export_failure_never_writes_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / 'output'
            with mock.patch.object(self.cq.importers, 'importStep', side_effect=RuntimeError('broken STEP')):
                with self.assertRaisesRegex(RuntimeError, 'broken STEP'):
                    generate(dest)
            report = json.loads((dest / 'validation.json').read_text())
            self.assertEqual(report['status'], 'INCOMPLETE')
            self.assertIn('broken STEP', report['error'])


if __name__ == '__main__':
    unittest.main()
