"""Checks for the deliberately partial seller-size surface, not board fit."""
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
from cad_reference import generate_board_span_reference as board
from cad_reference.generate_reference import ReferenceError, read_step_shape, sha256


class BoardSpanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = Path(self.tmp.name) / 'reference'
        self.manifest = json.loads(board.MANIFEST.read_bytes())
        self.assets = yaml.safe_load(board.ASSETS.read_bytes())

    def test_roundtrip_one_surface_and_unknown_physical_thickness(self):
        receipt = board.generate(self.out)
        self.assertIsNone(receipt['geometry']['physical_board_thickness_mm'])
        self.assertEqual(receipt['geometry']['spans_mm'], [57, 28])
        self.assertEqual(receipt['geometry']['numeric_rectangle_area_mm2'], 1596)
        shape = read_step_shape(self.out / board.STEP)
        self.assertEqual(len(shape.Solids()), 0)
        self.assertEqual(len(shape.Faces()), 1)
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        self.assertEqual(board.verify(self.out)['status'], 'PASS_DELIVERED_NUMERIC_SPANS_ONLY')
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})

    def test_manifest_cannot_invent_height_or_approve_fit(self):
        for key, value in [('scope', 'BOARD_CONTOUR'), ('physical_identity', 'VERIFIED'),
                           ('manufacturing_release', True), ('cad_start', 'PASS')]:
            m = deepcopy(self.manifest); m[key] = value
            with self.assertRaises(ReferenceError): board.validate_inputs(self.assets, m)
        for key in self.manifest['unknown_features']:
            m = deepcopy(self.manifest); m['unknown_features'][key] = 0
            with self.assertRaises(ReferenceError): board.validate_inputs(self.assets, m)

    def test_modified_spans_or_source_rejected_before_creation(self):
        for field in ('dimensions', 'source'):
            m = deepcopy(self.manifest)
            if field == 'dimensions': m[field]['long_span_mm'] = 62
            else: m[field]['filename'] = 'another-board.jpg'
            path = Path(self.tmp.name) / 'invalid.json'
            path.write_text(json.dumps(m))
            with self.assertRaises(ReferenceError): board.generate(self.out, manifest_path=path)
            self.assertFalse(self.out.exists())

    def test_wrong_asset_or_duplicate_rejected(self):
        for duplicate in (False, True):
            a = deepcopy(self.assets)
            row = next(r for r in a['assets'] if r['asset_id'] == 'AST-MCU-ESP32S3-001')
            if duplicate: a['assets'].append(deepcopy(row))
            else: row['item'] = 'another Type-C board'
            with self.assertRaises(ReferenceError): board.validate_inputs(a, self.manifest)

    def test_existing_directory_not_overwritten(self):
        board.generate(self.out)
        with self.assertRaises(FileExistsError): board.generate(self.out)
        board.verify(self.out)

    def test_invented_solid_holes_or_wrong_position_rejected(self):
        face = cq.Face.makeFromWires(cq.Workplane('XY').rect(57, 28).val())
        shapes = [cq.Workplane('XY').box(57, 28, 1.6).val(),
                  face.translate((0, 0, 1)), face.translate((1, 0, 0)),
                  cq.Face.makeFromWires(cq.Workplane('XY').rect(57, 28).val(),
                                       [cq.Workplane('XY').circle(1).val()]),
                  cq.Compound.makeCompound([face, cq.Edge.makeLine((0,0,0),(1,0,0))])]
        for shape in shapes:
            with self.assertRaises(ReferenceError): board.check_plane(shape, 57, 28)

    def test_wrong_step_fails_even_after_rehash(self):
        board.generate(self.out)
        path = self.out / board.STEP
        face = cq.Face.makeFromWires(cq.Workplane('XY').rect(58, 28).val())
        cq.exporters.export(face, str(path))
        receipt = json.loads((self.out/'validation.json').read_bytes())
        receipt['files'][0]['sha256'] = sha256(path.read_bytes())
        (self.out/'validation.json').write_text(json.dumps(receipt))
        with self.assertRaises(ReferenceError): board.verify(self.out)

    def test_false_receipt_and_svg_claim_rejected(self):
        board.generate(self.out)
        p = self.out/'validation.json'; original = p.read_bytes()
        receipt = json.loads(original); receipt['manufacturing_release'] = True
        p.write_text(json.dumps(receipt))
        with self.assertRaises(ReferenceError): board.verify(self.out)
        p.write_bytes(original)
        svg = self.out / board.SVG
        svg.write_text(svg.read_text().replace('REFERENCE ONLY.', 'FIT APPROVED.'))
        receipt = json.loads(original); receipt['files'][1]['sha256'] = sha256(svg.read_bytes())
        p.write_text(json.dumps(receipt))
        with self.assertRaises(ReferenceError): board.verify(self.out)

    def test_export_failure_retains_incomplete_receipt(self):
        with patch('cadquery.exporters.export', side_effect=RuntimeError('export failed')):
            with self.assertRaises(RuntimeError): board.generate(self.out)
        receipt = json.loads((self.out/'validation.json').read_bytes())
        self.assertEqual(receipt['status'], 'INCOMPLETE')

    def test_actual_delivered_example(self):
        result = board.verify(ROOT/'cad_reference/examples/board-spans-20261107')
        self.assertFalse(result['manufacturing_release'])


if __name__ == '__main__':
    unittest.main()
