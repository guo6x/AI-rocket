"""Synthetic-only tests. Values below describe NO purchased or real board."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import cadquery as cq
from cad_reference import board_measurement_envelope as board
from cad_reference.generate_reference import ReferenceError


class BoardMeasurementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.input = self.root / 'private-input' / 'record.json'
        self.input.parent.mkdir()
        self.evidence = self.input.parent / 'synthetic-evidence.txt'
        self.evidence.write_text('SYNTHETIC TEST FIXTURE, NOT A PHYSICAL MEASUREMENT.\n')
        self.output = self.root / 'output'
        self.record = board.template('RA02_U1')
        self.record.update(coverage=board.COVERAGE)
        self.record['identity'] = {
            'pcb_markings_or_revision': 'SYNTHETIC TEST, no actual PCB',
            'recorded_assembly_state': 'synthetic downward pins and top feature',
            'orientation_and_extreme_features': 'synthetic full XY, worksheet datum',
            'evidence_ids': ['EV-synthetic'],
        }
        self.record['method'] = {
            'date': '2026-11-10', 'instrument': 'SYNTHETIC instrument',
            'resolution_mm': .01, 'uncertainty_basis': 'SYNTHETIC test bounds only',
            'unpowered': True,
        }
        self.record['review'] = {'reviewed_for_this_unit': True,
                                'reviewer_ref': 'SYNTHETIC TEST', 'transcription_checked': True}
        self.record['evidence'] = [{'id': 'EV-synthetic', 'path': self.evidence.name,
                                  'sha256': board.digest(self.evidence.read_bytes()), 'unit_id': 'RA02_U1'}]
        values = dict(PCB_L=20, PCB_W=10, PCB_T=1.6, H_plus=3, H_minus=5,
                      X_min=-2, X_max=12, Y_min=-1, Y_max=24)
        self.record['measurements'] = {
            key: {'readings_mm': [value] * 3, 'uncertainty_mm': .1,
                  'evidence_ids': ['EV-synthetic']} for key, value in values.items()}
        self.save()

    def save(self):
        self.input.write_bytes(board.canonical(self.record))

    def validated(self):
        return board.validate(self.record, self.input.parent)

    def refused(self):
        with self.assertRaises(ReferenceError):
            self.validated()

    def test_all_five_templates_are_blank_and_refused_without_output(self):
        for unit in board.UNITS:
            self.record = board.template(unit)
            self.save()
            self.assertTrue(all(r['readings_mm'] is None for r in self.record['measurements'].values()))
            with self.assertRaises(ReferenceError):
                board.generate(self.input, self.output)
            self.assertFalse(self.output.exists())

    def test_shipped_templates_exactly_match_empty_generator_and_never_export(self):
        folder = Path(board.__file__).parent / 'measurement-record-templates'
        self.assertEqual({p.name for p in folder.iterdir()}, {unit+'.json' for unit in board.UNITS})
        for unit in board.UNITS:
            path = folder / (unit+'.json')
            self.assertEqual(board.load_record(path), board.template(unit))
            with self.assertRaises(ReferenceError): board.generate(path, self.output)
            self.assertFalse(self.output.exists())

    def test_asymmetric_heights_and_negative_protrusions_follow_worksheet(self):
        value = self.validated()
        self.assertEqual(value['boxes_mm']['OBSERVED_SPAN'], [-2, -1, -5, 12, 24, 4.6])
        for actual, expected in zip(value['boxes_mm']['UNCERTAINTY_EXPANDED'], [-2.1,-1.1,-5.1,12.1,24.1,4.8]):
            self.assertAlmostEqual(actual, expected)
        self.assertFalse(value['physical_measurements_verified_by_software'])

    def test_reading_spread_is_not_averaged_out_of_expanded_box(self):
        self.record['measurements']['X_min']['readings_mm'] = [-2, -2.3, -2.1]
        self.record['measurements']['H_minus']['readings_mm'] = [5, 5.3, 5.1]
        value = self.validated()
        self.assertAlmostEqual(value['boxes_mm']['UNCERTAINTY_EXPANDED'][0], -2.4)
        self.assertAlmostEqual(value['boxes_mm']['UNCERTAINTY_EXPANDED'][2], -5.4)

    def test_no_underboard_features_can_be_explicit_zero_but_not_unknown(self):
        row = self.record['measurements']['H_minus']
        row['readings_mm'] = [0,0,0]
        self.assertEqual(self.validated()['boxes_mm']['OBSERVED_SPAN'][2], 0)
        self.assertEqual(self.validated()['boxes_mm']['UNCERTAINTY_EXPANDED'][2], -.1)
        row['readings_mm'] = None
        self.refused()

    def test_bad_numeric_values_rejected(self):
        original = deepcopy(self.record)
        for value in (None, True, '1.6', float('nan'), float('inf'), 0, -1):
            with self.subTest(value=value):
                self.record = deepcopy(original)
                self.record['measurements']['PCB_T']['readings_mm'] = [value] * 3
                self.refused()

    def test_oversized_integers_refused_without_output_or_traceback(self):
        original = deepcopy(self.record)
        for value in (10**400, -(10**400)):
            for location in ('reading', 'uncertainty', 'resolution'):
                with self.subTest(location=location, sign=value > 0):
                    self.record = deepcopy(original)
                    if location == 'reading':
                        self.record['measurements']['PCB_T']['readings_mm'] = [value] * 3
                    elif location == 'uncertainty':
                        self.record['measurements']['PCB_T']['uncertainty_mm'] = value
                    else:
                        self.record['method']['resolution_mm'] = value
                    self.save()
                    self.refused()
                    result = subprocess.run(
                        [sys.executable, '-m', 'cad_reference.board_measurement_envelope',
                         'generate', '--input', str(self.input), '--output', str(self.output)],
                        capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1)
                    self.assertIn('REFUSED:', result.stderr)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertFalse(self.output.exists())

    def test_uncertainty_cannot_be_blank_zero_or_negative(self):
        for value in (None, 0, -1, True, '0.1', float('inf')):
            self.record['measurements']['PCB_L']['uncertainty_mm'] = value
            self.refused()

    def test_repeat_readings_and_source_refs_required_for_every_value(self):
        original = deepcopy(self.record)
        for key, value in [('readings_mm', [1, 1]), ('evidence_ids', []),
                           ('evidence_ids', ['EV-missing']), ('evidence_ids', ['EV-synthetic']*2)]:
            self.record = deepcopy(original)
            self.record['measurements']['PCB_T'][key] = value
            self.refused()

    def test_units_datum_coverage_and_asset_cannot_be_swapped(self):
        original = deepcopy(self.record)
        for key, value in [('units','inch'), ('datum','sensor_axes'), ('coverage','BARE_MODULE'),
                           ('asset_id','AST-MCU-APM32-001'), ('unit_id','RA02_U2'),
                           ('unit_id',None), ('schema_version',True)]:
            self.record = deepcopy(original)
            self.record[key] = value
            self.refused()

    def test_no_blank_identity_method_or_review_claim(self):
        original = deepcopy(self.record)
        for group, key, value in [('identity','pcb_markings_or_revision',None),
                                 ('method','date','2026-02-30'), ('method','resolution_mm',0),
                                 ('method','unpowered',False), ('method','uncertainty_basis',''),
                                 ('review','reviewed_for_this_unit',False),
                                 ('review','transcription_checked',None), ('review','reviewer_ref','')]:
            self.record = deepcopy(original)
            self.record[group][key] = value
            self.refused()

    def test_no_unknown_fields_or_acceptance_promotion(self):
        original = deepcopy(self.record)
        for mutation in ('release','fit','unknown','new','new_measurement'):
            self.record = deepcopy(original)
            if mutation == 'release': self.record['manufacturing_release'] = True
            elif mutation == 'fit': self.record['fit_accepted'] = True
            elif mutation == 'unknown': self.record['unknown_features']['mounting_holes'] = []
            elif mutation == 'new': self.record['flight_qualified'] = True
            else: self.record['measurements']['PCB_T']['guessed'] = True
            self.refused()

    def test_missing_changed_empty_or_mismatched_evidence_refused(self):
        original = deepcopy(self.record)
        for mutation in ('missing','changed','empty','unit','duplicate'):
            self.record = deepcopy(original)
            if mutation == 'missing': self.record['evidence'][0]['path'] = 'missing.txt'
            elif mutation == 'changed': self.record['evidence'][0]['sha256'] = '0'*64
            elif mutation == 'empty': self.record['evidence'] = []
            elif mutation == 'unit': self.record['evidence'][0]['unit_id'] = 'RA02_U2'
            else: self.record['evidence'].append(deepcopy(self.record['evidence'][0]))
            self.refused()

    def test_evidence_paths_cannot_escape_or_use_symlinks(self):
        for path in ('../synthetic-evidence.txt', '/tmp/anything', 'folder\\file'):
            self.record['evidence'][0]['path'] = path
            self.refused()
        alias = self.input.parent / 'alias'
        alias.symlink_to(self.evidence)
        self.record['evidence'][0]['path'] = 'alias'
        self.refused()

    def test_windows_drive_and_stream_paths_rejected_before_filesystem_access(self):
        # POSIX syntax alone is insufficient: a drive component can reset a
        # Windows join, and colon names may address NTFS alternate streams.
        for path in ('D:/outside.txt', 'D:outside.txt', 'sub/D:/outside.txt',
                     'synthetic-evidence.txt:stream'):
            with self.subTest(path=path):
                self.record['evidence'][0]['path'] = path
                with patch.object(Path, 'is_file', side_effect=AssertionError('unsafe path reached filesystem')):
                    self.refused()

    def test_envelope_must_include_pcb_and_correct_nonnegative_heights(self):
        original = deepcopy(self.record)
        for key, value in [('X_min',1), ('Y_min',1), ('X_max',9), ('Y_max',19), ('H_minus',-5)]:
            self.record = deepcopy(original)
            self.record['measurements'][key]['readings_mm'] = [value]*3
            self.refused()

    def test_expanded_envelope_must_also_contain_pcb_bounds(self):
        self.record['measurements']['PCB_W']['uncertainty_mm'] = 4
        self.refused()

    def test_json_duplicates_and_nan_are_refused(self):
        for content in ('{"scope":1,"scope":2}', '{"value":NaN}'):
            self.input.write_text(content)
            with self.assertRaises(ReferenceError): board.load_record(self.input)

    def test_actual_kernel_roundtrips_two_boxes_without_touching_sources(self):
        before = self.input.read_bytes(), self.evidence.read_bytes()
        report = board.generate(self.input, self.output)
        self.assertEqual(report['status'], board.STATUS)
        self.assertEqual(len(list(self.output.glob('*.step'))), 2)
        self.assertEqual(board.verify(self.input, self.output)['status'], board.STATUS)
        shape = board.read_step_shape(self.output / board.filenames('RA02_U1')['OBSERVED_SPAN'])
        self.assertAlmostEqual(shape.BoundingBox().zmin, -5)
        self.assertAlmostEqual(shape.BoundingBox().zmax, 4.6)
        self.assertEqual(before, (self.input.read_bytes(), self.evidence.read_bytes()))
        self.assertNotIn('synthetic-evidence.txt', (self.output / 'validation.json').read_text())
        self.assertNotIn('SYNTHETIC instrument', (self.output / 'validation.json').read_text())

    def test_existing_output_is_preserved(self):
        self.output.mkdir()
        marker = self.output / 'keep.txt'
        marker.write_text('keep')
        with self.assertRaises(FileExistsError): board.generate(self.input, self.output)
        self.assertEqual(marker.read_text(), 'keep')
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_step_import_failure_and_final_verification_failure_never_leave_pass(self):
        for where in ('read_step_shape', 'verify'):
            with tempfile.TemporaryDirectory() as temp:
                output = Path(temp) / 'output'
                with patch.object(board, where, side_effect=ReferenceError('injected')):
                    with self.assertRaisesRegex(ReferenceError, 'injected'):
                        board.generate(self.input, output)
                self.assertEqual(json.loads((output/'validation.json').read_text())['status'], 'INCOMPLETE')

    def test_input_change_during_export_is_caught(self):
        original = cq.exporters.export
        def change(*args, **kwargs):
            result = original(*args, **kwargs)
            self.evidence.write_text('changed')
            return result
        with patch.object(cq.exporters, 'export', side_effect=change):
            with self.assertRaises(ReferenceError): board.generate(self.input, self.output)
        self.assertEqual(json.loads((self.output/'validation.json').read_text())['status'], 'INCOMPLETE')

    def test_source_change_during_verification_is_refused(self):
        board.generate(self.input, self.output)
        original = board.read_step_shape
        def change(path):
            shape = original(path)
            self.evidence.write_text('CHANGED DURING VERIFICATION')
            return shape
        with patch.object(board, 'read_step_shape', side_effect=change):
            with self.assertRaises(ReferenceError): board.verify(self.input, self.output)

    def test_step_change_after_import_during_verification_is_refused(self):
        board.generate(self.input, self.output)
        original = board.read_step_shape
        def change(path):
            shape = original(path)
            path.write_bytes(path.read_bytes()+b'CHANGED AFTER IMPORT')
            return shape
        with patch.object(board, 'read_step_shape', side_effect=change):
            with self.assertRaisesRegex(ReferenceError, 'package changed'):
                board.verify(self.input, self.output)

    def test_receipt_change_during_verification_is_refused(self):
        board.generate(self.input, self.output)
        original = board.read_step_shape
        def change(path):
            shape = original(path)
            receipt = self.output/'validation.json'
            receipt.write_bytes(receipt.read_bytes()+b' ')
            return shape
        with patch.object(board, 'read_step_shape', side_effect=change):
            with self.assertRaisesRegex(ReferenceError, 'package changed'):
                board.verify(self.input, self.output)

    def test_independent_reimport_catches_shift_even_if_digest_recomputed(self):
        board.generate(self.input, self.output)
        step = self.output / board.filenames('RA02_U1')['OBSERVED_SPAN']
        shifted = board.read_step_shape(step).translate((0,0,1))
        cq.exporters.export(shifted, str(step))
        receipt = json.loads((self.output/'validation.json').read_text())
        receipt['exports'][step.name] = board.digest(step.read_bytes())
        (self.output/'validation.json').write_bytes(board.canonical(receipt))
        with self.assertRaises(ReferenceError): board.verify(self.input, self.output)

    def test_surface_and_multiple_solids_are_not_valid_boxes(self):
        shape = cq.Workplane('XY').box(14,25,9.6,centered=False).val().translate((-2,-1,-5))
        for bad in (shape.Faces()[0], cq.Compound.makeCompound([shape, shape.translate((30,0,0))])):
            with self.assertRaises(ReferenceError): board.check_box(bad, [-2,-1,-5,12,24,4.6])

    def test_changed_record_and_extra_file_fail_readonly_verification(self):
        board.generate(self.input, self.output)
        before = {p.name: p.read_bytes() for p in self.output.iterdir()}
        self.record['method']['instrument'] = 'CHANGED'
        self.save()
        with self.assertRaises(ReferenceError): board.verify(self.input, self.output)
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.output.iterdir()})

    def test_extra_package_file_and_modified_warning_refused(self):
        board.generate(self.input, self.output)
        extra = self.output / 'unexpected.txt'
        extra.write_text('unexpected')
        with self.assertRaises(ReferenceError): board.verify(self.input, self.output)
        extra.unlink()
        (self.output/'README.txt').write_text('fit approved')
        with self.assertRaises(ReferenceError): board.verify(self.input, self.output)

    def test_cli_blank_template_cannot_generate_step_or_report_success(self):
        script = str(Path(board.__file__))
        empty = self.root / 'empty.json'
        result = subprocess.run([sys.executable, script, 'template', '--unit','APM32','--output',str(empty)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([sys.executable, script, 'generate','--input',str(empty),'--output',str(self.output)], capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'REFUSED', result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()


