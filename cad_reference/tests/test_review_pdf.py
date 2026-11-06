import re
from pathlib import Path
import tempfile
import unittest

import cadquery as cq

from cad_reference.generate_reference import generate as ra02_generate, ReferenceError
from cad_reference.generate_sensor_reference import generate as sensor_generate
from cad_reference.make_review_pdf import create_review, segments


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


if __name__ == '__main__':
    unittest.main()
