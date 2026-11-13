import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cadquery as cq

from cad_reference.generate_reference import generate as ra02_generate, ReferenceError
from cad_reference.generate_sensor_reference import generate as sensor_generate
from cad_reference.make_review_pdf import create_review, render_review, verify_review, segments
from cad_reference import verify_package as verifier


class ReviewPdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.ra = cls.root / 'ra02'
        cls.sensors = cls.root / 'sensors'
        ra02_generate(cls.ra)
        sensor_generate(cls.sensors)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_three_page_pdf_has_labels_limits_and_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'review.pdf'
            create_review(out, self.ra, self.sensors)
            content = out.read_bytes()
            self.assertTrue(content.startswith(b'%PDF-'))
            self.assertIn(b'/FontFile2', content, 'review fonts must be embedded')
            self.assertEqual(len(re.findall(rb'/Type /Page\b', content)), 3)
            for label in (b'Ra-02 V1.1', b'MPU-9250', b'BMP280', b'REFERENCE ONLY',
                          b'Not the GY-91 PCB', b'No fit, manufacturing or flight acceptance',
                          b'PDF page 39', b'PDF page 38', b'not to scale'):
                self.assertIn(label, content)
            with self.assertRaises(FileExistsError): create_review(out, self.ra, self.sensors)
            self.assertEqual(content, out.read_bytes())

    def test_mismatched_package_does_not_produce_pdf(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'review.pdf'
            with self.assertRaises(ReferenceError): create_review(out, self.sensors, self.ra)
            self.assertFalse(out.exists())

    def test_actual_step_projection_deduplicates_coincident_box_edges(self):
        shape = cq.Workplane('XY').box(3, 3, 1, centered=False).val()
        self.assertEqual(len(segments(shape, lambda x,y,z: (x,y))), 4)
        self.assertEqual(len(segments(shape, lambda x,y,z: (x,z))), 4)

    def test_view_labels_do_not_overlap_scale_notice_or_table(self):
        from reportlab.pdfgen.canvas import Canvas
        positions = {}
        original = Canvas.drawString
        centered = Canvas.drawCentredString
        def record(canvas, x, y, text, *args, **kwargs):
            positions.setdefault(text, []).append(y)
            return original(canvas, x, y, text, *args, **kwargs)
        def record_centered(canvas, x, y, text, *args, **kwargs):
            positions.setdefault(text, []).append(y)
            return centered(canvas, x, y, text, *args, **kwargs)
        with patch.object(Canvas, 'drawString', new=record), \
                patch.object(Canvas, 'drawCentredString', new=record_centered):
            render_review(self.ra, self.sensors)
        notice = 'Views are independently fitted to the page, not to scale. No assembly placement is implied.'
        for label_y, notice_y, table_y in zip(positions['YZ'], positions[notice], positions['Reference case']):
            self.assertGreaterEqual(label_y - notice_y, 12)
            self.assertGreaterEqual(notice_y - table_y, 12)
        self.assertEqual(len(positions[notice]), 3)

    def test_output_inside_either_package_is_rejected_without_mutation(self):
        before = {folder: {p.name: p.read_bytes() for p in folder.iterdir()}
                  for folder in (self.ra, self.sensors)}
        for folder in (self.ra, self.sensors):
            for relative in ('review.pdf', 'nested/review.pdf'):
                with self.subTest(folder=folder.name, relative=relative):
                    with self.assertRaisesRegex(ReferenceError, 'outside both'):
                        create_review(folder / relative, self.ra, self.sensors)
                    self.assertEqual(before[folder], {p.name: p.read_bytes() for p in folder.iterdir()})
        for folder, kind in ((self.ra, 'ra02'), (self.sensors, 'sensors')):
            self.assertEqual(verifier.verify(folder, kind)['status'], verifier.STATUS)

    def test_symlink_alias_and_dotdot_cannot_hide_inside_package_output(self):
        with tempfile.TemporaryDirectory() as temp:
            alias = Path(temp) / 'alias'
            alias.symlink_to(self.ra, target_is_directory=True)
            for out in (alias / 'review.pdf', alias / 'nested/review.pdf',
                        self.ra / 'absent/../review.pdf', self.ra):
                with self.subTest(output=str(out)):
                    with self.assertRaisesRegex(ReferenceError, 'outside both'):
                        create_review(out, self.ra, self.sensors)
            self.assertFalse((self.ra / 'review.pdf').exists())
            self.assertFalse((self.ra / 'nested').exists())
            self.assertFalse((self.ra / 'absent').exists())

    def test_readonly_verification_matches_exact_repeat_render(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'review.pdf'
            create_review(out, self.ra, self.sensors)
            before = out.read_bytes()
            self.assertEqual(before, render_review(self.ra, self.sensors))
            result = verify_review(out, self.ra, self.sensors)
            self.assertEqual(result['status'], 'PASS_REFERENCE_REVIEW_REPRODUCTION_ONLY')
            self.assertFalse(result['manufacturing_release'])
            self.assertEqual(before, out.read_bytes())

    def test_outbound_dotdot_does_not_create_intermediate_package_directory(self):
        out = self.ra / 'absent/../../outbound-review.pdf'
        destination = out.resolve()
        self.addCleanup(lambda: destination.unlink(missing_ok=True))
        result = create_review(out, self.ra, self.sensors)
        self.assertEqual(result, destination)
        self.assertTrue(result.is_file())
        self.assertFalse((self.ra / 'absent').exists())
        self.assertEqual(verifier.verify(self.ra, 'ra02')['status'], verifier.STATUS)

    def test_stale_or_modified_pdf_is_rejected_and_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'review.pdf'
            create_review(out, self.ra, self.sensors)
            modified = out.read_bytes().replace(b'REFERENCE ONLY', b'MANUFACTURE OK')
            out.write_bytes(modified)
            with self.assertRaisesRegex(ReferenceError, 'differs'):
                verify_review(out, self.ra, self.sensors)
            self.assertEqual(modified, out.read_bytes())

    def test_missing_or_symlink_pdf_does_not_create_or_modify_target(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / 'absent.pdf'
            with self.assertRaises(FileNotFoundError):
                verify_review(missing, self.ra, self.sensors)
            self.assertFalse(missing.exists())
            target = Path(temp) / 'target.pdf'
            create_review(target, self.ra, self.sensors)
            before = target.read_bytes()
            alias = Path(temp) / 'alias.pdf'
            alias.symlink_to(target)
            with self.assertRaisesRegex(ReferenceError, 'regular files'):
                verify_review(alias, self.ra, self.sensors)
            self.assertEqual(before, target.read_bytes())

    def test_pdf_changed_during_render_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'review.pdf'
            create_review(out, self.ra, self.sensors)
            expected = out.read_bytes()
            def render_and_change(*_):
                out.write_bytes(b'changed during rendering')
                return expected
            with patch('cad_reference.make_review_pdf.render_review', side_effect=render_and_change):
                with self.assertRaisesRegex(ReferenceError, 'changed during'):
                    verify_review(out, self.ra, self.sensors)

    def test_committed_pdf_matches_committed_step_packages(self):
        examples = Path(__file__).resolve().parents[1] / 'examples'
        result = verify_review(examples / 'electronics-reference-review.pdf',
                               examples / 'ra02-20261106', examples / 'sensors-20261106')
        self.assertEqual(result['status'], 'PASS_REFERENCE_REVIEW_REPRODUCTION_ONLY')


if __name__ == '__main__':
    unittest.main()
