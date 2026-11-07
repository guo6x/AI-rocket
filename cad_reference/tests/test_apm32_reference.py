"""Real-kernel APM32 48-land verification and source/geometry negative tests."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import cadquery as cq
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cad_reference import generate_apm32_reference as apm
from cad_reference.generate_reference import ReferenceError, read_step_shape, sha256


class APM32ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.source = Path(cls.temp.name)/'source'
        cls.report = apm.generate(cls.source)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.manifest = json.loads(apm.MANIFEST.read_bytes())
        self.assets = yaml.safe_load(apm.ASSETS.read_bytes())
        self.temp_case = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_case.cleanup)
        self.out = Path(self.temp_case.name)/'copy'
        shutil.copytree(self.source, self.out)

    def rehash(self, filename):
        """A replaced file with forged matching digest must still fail geometry checks."""
        p = self.out/'validation.json'
        receipt = json.loads(p.read_bytes())
        item = next(i for i in receipt['files'] if i['name'] == filename)
        content = (self.out/filename).read_bytes()
        item.update(sha256=sha256(content), bytes=len(content))
        p.write_text(json.dumps(receipt))

    def reject(self):
        with self.assertRaises((ReferenceError, ValueError, TypeError)):
            apm.verify(self.out)

    def test_real_three_step_roundtrips_and_read_only_verifier(self):
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        verified = apm.verify(self.out)
        self.assertEqual(verified['status'], 'PASS_DELIVERED_GEOMETRY_ONLY')
        self.assertEqual(verified['step_files'], 3)
        self.assertEqual(verified['planar_lands'], 48)
        self.assertFalse(verified['manufacturing_release'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})

    def test_nominal_height_is_not_maximum_height(self):
        body = read_step_shape(self.out/apm.FILES['body']).BoundingBox()
        maximum = read_step_shape(self.out/apm.FILES['envelope']).BoundingBox()
        apm.close([body.xlen, body.ylen, body.zlen, body.zmin, body.zmax], [7, 7, 1.4, .1, 1.5], 'body')
        apm.close([maximum.xlen, maximum.ylen, maximum.zlen, maximum.zmin], [9.2, 9.2, 1.6, 0], 'maximum')

    def test_land_geometry_has_no_copper_thickness_or_solids(self):
        shape = read_step_shape(self.out/apm.FILES['lands'])
        self.assertEqual(len(shape.Solids()), 0)
        self.assertEqual(len(shape.Faces()), 48)
        apm.close([shape.BoundingBox().zlen, shape.Area()], [0, 17.28], 'planar area')

    def test_source_figure19_pin_order_and_independent_dimensions(self):
        pads = apm.lands(self.manifest)
        # Independent hand-transcribed drawing anchors, not produced by the generator.
        for pin, expected in {1:[-2.75,-4.25,0],12:[2.75,-4.25,0],
             13:[4.25,-2.75,0],24:[4.25,2.75,0],25:[2.75,4.25,0],
             36:[-2.75,4.25,0],37:[-4.25,2.75,0],48:[-4.25,-2.75,0]}.items():
            self.assertEqual(pads[pin-1]['center_mm'], expected)
        self.assertEqual(pads[0]['size_xy_mm'], [.3,1.2])
        self.assertEqual(pads[12]['size_xy_mm'], [1.2,.3])
        self.assertAlmostEqual(4.25-.6, 7.3/2)
        self.assertAlmostEqual(4.25+.6, 9.7/2)
        self.assertAlmostEqual(11*.5+.3, 5.8)

    def test_source_dimensions_revision_and_page_tampering_rejected(self):
        for change in ('height', 'pitch', 'units', 'source', 'source_page', 'model'):
            with self.subTest(change=change):
                m = deepcopy(self.manifest)
                if change == 'height': m['dimensions']['body_thickness_nominal']=1.6
                elif change == 'pitch': m['dimensions']['lands']['pitch']=.65
                elif change == 'units': m['units']='inch'
                elif change == 'source': m['source']['pdf_sha256']='0'*64
                elif change == 'source_page': m['source']['land_pattern_pdf_page']=47
                else: m['model']='APM32F103R8T6'
                with self.assertRaises(ReferenceError): apm.validate_inputs(self.assets, m)

    def test_reference_identity_and_unknowns_cannot_be_promoted(self):
        for field, value in [('manufacturing_release',True),('physical_identity','VERIFIED'),
                             ('cad_start','PASS'),('scope','CORE_BOARD'),('schema_version',True)]:
            with self.subTest(field=field):
                m=deepcopy(self.manifest); m[field]=value
                with self.assertRaises(ReferenceError): apm.validate_inputs(self.assets,m)
        for feature in self.manifest['unknown_features']:
            with self.subTest(feature=feature):
                m=deepcopy(self.manifest); m['unknown_features'][feature]=0
                with self.assertRaises(ReferenceError): apm.validate_inputs(self.assets,m)

    def test_changed_purchase_model_or_duplicate_asset_rejected(self):
        for duplicate in (False, True):
            a=deepcopy(self.assets)
            row=next(r for r in a['assets'] if r['asset_id']=='AST-MCU-APM32-001')
            if duplicate: a['assets'].append(deepcopy(row))
            else: row['item']='some other board'
            with self.assertRaises(ReferenceError): apm.validate_inputs(a,self.manifest)

    def test_invalid_manifest_leaves_no_output(self):
        path=Path(self.temp_case.name)/'bad.json'
        m=deepcopy(self.manifest); m['dimensions']['body_thickness_nominal']=float('nan')
        path.write_text(json.dumps(m)); out=Path(self.temp_case.name)/'new'
        with self.assertRaises(ValueError): apm.generate(out,manifest_path=path)
        self.assertFalse(out.exists())

    def test_existing_output_cannot_be_overwritten(self):
        with self.assertRaises(FileExistsError): apm.generate(self.out)
        apm.verify(self.out)

    def test_import_and_export_failures_leave_incomplete_receipt(self):
        for function in ('cadquery.importers.importStep','cadquery.exporters.export'):
            out=Path(self.temp_case.name)/function.rsplit('.',1)[-1]
            with patch(function,side_effect=RuntimeError('kernel failed')):
                with self.assertRaisesRegex(RuntimeError,'kernel failed'): apm.generate(out)
            self.assertEqual(json.loads((out/'validation.json').read_text())['status'],'INCOMPLETE')

    def test_shifted_body_with_forged_hash_is_rejected(self):
        path=self.out/apm.FILES['body']
        shape=read_step_shape(path).translate((.1,0,0))
        cq.exporters.export(shape,str(path)); self.rehash(path.name); self.reject()

    def test_wrong_max_envelope_with_forged_hash_is_rejected(self):
        path=self.out/apm.FILES['envelope']
        shape=cq.Workplane('XY').box(9,9,1.6,centered=False).translate((-4.5,-4.5,0)).val()
        cq.exporters.export(shape,str(path)); self.rehash(path.name); self.reject()

    def test_missing_duplicate_shifted_rotated_or_solid_pad_rejected(self):
        original=read_step_shape(self.source/apm.FILES['lands'])
        for action in ('missing','duplicate','shifted','rotation','thickened','loose_edge'):
            with self.subTest(action=action):
                faces=original.Faces()
                if action=='missing': faces.pop()
                elif action=='duplicate': faces[0]=faces[1]
                elif action=='shifted': faces[0]=faces[0].translate((.01,0,0))
                elif action=='rotation': faces[0]=faces[0].rotate(faces[0].Center(),faces[0].Center()+cq.Vector(0,0,1),15)
                elif action=='thickened': faces[0]=cq.Solid.extrudeLinear(faces[0].outerWire(),[],cq.Vector(0,0,.035))
                else: faces.append(cq.Edge.makeLine((0,0,0),(1,0,0)))
                shape=cq.Compound.makeCompound(faces)
                with self.assertRaises(ReferenceError): apm.check_lands(shape,apm.lands(self.manifest))

    def test_rotated_land_array_is_not_equivalent_pin_frame(self):
        # A square's 90-degree symmetry cannot prove pin numbering. The independent
        # coordinate/label artifact is validated against Figure 19 separately.
        data=json.loads((self.out/apm.FILES['coordinates']).read_bytes())
        data['lands'][0]['pin']=48
        (self.out/apm.FILES['coordinates']).write_text(json.dumps(data))
        self.rehash(apm.FILES['coordinates']); self.reject()

    def test_forged_svg_labels_rejected_even_when_receipt_rehashed(self):
        p=self.out/apm.FILES['review']
        p.write_text(p.read_text().replace('REFERENCE ONLY.','FIT APPROVED.'))
        self.rehash(p.name); self.reject()

    def test_receipt_cannot_promote_release_or_lie_about_geometry(self):
        path=self.out/'validation.json'; original=path.read_bytes()
        for mode in ('release','scope','status','area','origin_bool'):
            with self.subTest(mode=mode):
                receipt=json.loads(original)
                if mode=='release': receipt['manufacturing_release']=True
                elif mode=='scope': receipt['scope']='CORE_BOARD'
                elif mode=='status': receipt['status']='INCOMPLETE'
                elif mode=='area': receipt['exports']['lands']['total_area_mm2']=0
                else: receipt['exports']['envelope']['origin_mm'][2]=False
                path.write_text(json.dumps(receipt)); self.reject()
        path.write_bytes(original)

    def test_duplicate_json_keys_rejected(self):
        path=self.out/'validation.json'
        path.write_text(path.read_text().replace('"status":','"status":"PASS_GEOMETRY_ROUNDTRIP_ONLY", "status":',1))
        self.reject()

    def test_extra_inventory_and_symlink_rejected(self):
        p=self.out/'extra.step'; p.write_text('unexpected'); self.reject(); p.unlink()
        p=self.out/apm.FILES['body']; p.unlink(); p.symlink_to(self.source/apm.FILES['body']); self.reject()


if __name__=='__main__':
    unittest.main()
