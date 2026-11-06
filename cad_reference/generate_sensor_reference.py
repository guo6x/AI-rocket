"""Independent MPU-9250/BMP280 package boxes, never a GY-91 board or fit model.

Manufacturer package dimensions only. No PCB, holes, sensor axes, solder, pads,
vent passage, installation clearance, physical measurements or release implied.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml

try:
    from .generate_reference import ReferenceError, check_shape, row_hash, sha256
except ImportError:  # direct CLI execution
    from generate_reference import ReferenceError, check_shape, row_hash, sha256

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'cad_reference/sensor-reference-inputs.json'
REGISTRY = ROOT / 'engineering/parameter-registry.yaml'
NOTICE = 'CHIP_PACKAGE_REFERENCE_ONLY_NOT_GY91_BOARD_FIT_MANUFACTURE_OR_FLIGHT'
DATUM = 'ARBITRARY_PACKAGE_BOX_CORNER_NOT_SENSOR_OR_BOARD_AXES'
BASIS = ('Explicit whole-package dimensions only; all-min/all-max are numeric reference '
         'corners, not an installation clearance or joint manufacturing distribution.')
UNKNOWN = ('gy91_board_dimensions', 'populated_chip_identity', 'placement_on_board',
           'board_axes', 'mounting_holes', 'solder_height', 'connector_clearance',
           'vent_path', 'material_volume', 'mass')
# These are independently reviewed drawing values, not a user input allowlist.
# Changes require a fresh source review; merely rehashing a manifest is insufficient.
REVIEWED = {
    'MPU9250': {
        'registry_source_url': 'https://www.invensense.tdk.com/en-us/news-media/press/invensense-sets-new-industry-standard-worlds-smallest-lowest-power-integrated-9-axis',
        'registry_source_revision': 'TDK InvenSense MPU-9250 product announcement; revision not published; retrieved 2026-10-27',
        'registry_model_claim': 'MPU-9250 chip/package on ordered GY-91 variant',
        'url': 'https://product.tdk.com/system/files/dam/doc/product/sensor/mortion-inertial/imu/data_sheet/ps-mpu-9250a-01-v1.1.pdf',
        'revision': 'PS-MPU-9250A-01 revision 1.1, 2016-06-20', 'page': 39,
        'pdf_sha256': 'fb38e76cd5f3b223d5c93046d690bd843c34a9c77f70c04f0052c12436855db9',
        'dimensions_mm': {'minimum': [2.9, 2.9, 0.95], 'nominal': [3., 3., 1.],
                          'maximum': [3.1, 3.1, 1.05]},
    },
    'BMP280': {
        'registry_source_url': 'https://www.bosch-sensortec.com/products/environmental-sensors/pressure-sensors/bmp280/',
        'registry_source_revision': 'Bosch BMP280 product page; revision not published; retrieved 2026-10-27',
        'registry_model_claim': 'BMP280 chip/package on ordered GY-91 variant',
        'url': 'https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf',
        'revision': 'BST-BMP280-DS001-26 revision 1.26, 2021-10', 'page': 38,
        'pdf_sha256': '473ff27d9df698b4757e36b36209f83b9f637b592c999d5fabe2a9453a488da6',
        'dimensions_mm': {'minimum': [1.9, 2.4, 0.9], 'nominal': [2., 2.5, 0.95],
                          'maximum': [2.1, 2.6, 1.]},
    },
}


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def validate_inputs(registry: dict, manifest: dict) -> list[dict]:
    if set(manifest) != {'schema_version', 'scope', 'manufacturing_release', 'physical_identity',
                         'datum', 'unknown_features', 'models'}:
        raise ReferenceError('unreviewed top-level fields')
    if (type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 1
            or manifest.get('scope') != NOTICE or manifest.get('datum') != DATUM):
        raise ReferenceError('wrong schema, scope or datum')
    if (manifest.get('physical_identity') != 'UNVERIFIED'
            or manifest.get('manufacturing_release') is not False
            or manifest.get('unknown_features') != dict.fromkeys(UNKNOWN)):
        raise ReferenceError('physical identity, release or unknown features changed')
    layer = registry.get('manufacturer_nominal', {})
    if layer.get('evidence_level') != 'MANUFACTURER_NOMINAL_REFERENCE':
        raise ReferenceError('wrong evidence layer')
    parameters = layer.get('parameters', [])
    ids = [row.get('id') for row in parameters]
    if len(ids) != len(set(ids)):
        raise ReferenceError('duplicate parameter IDs')
    rows = {row['id']: row for row in parameters}
    models = manifest.get('models', [])
    if [m.get('model_id') for m in models] != list(REVIEWED):
        raise ReferenceError('only the two independently reviewed chip packages are enabled')
    checked = []
    for model in models:
        if set(model) != {'model_id', 'model_claim', 'asset_id', 'physical_identity',
                          'parameter_bindings', 'source', 'dimensions_mm', 'dimension_basis'}:
            raise ReferenceError('unreviewed model fields')
        key = model['model_id']
        reviewed = REVIEWED[key]
        title = 'MPU-9250' if key == 'MPU9250' else 'BMP280'
        if (model.get('model_claim') != title + ' chip-package rectangular reference'
                or model.get('dimension_basis') != BASIS):
            raise ReferenceError('reference claim or dimension basis changed')
        if (model.get('asset_id') != 'AST-SENSOR-GY91-001'
                or model.get('physical_identity') != 'UNVERIFIED'):
            raise ReferenceError('asset or physical identity changed')
        source = model.get('source', {})
        if (set(source) != {'url', 'revision', 'page', 'pdf_sha256', 'retrieved_on', 'review_status'}
                or source.get('retrieved_on') != '2026-11-06'):
            raise ReferenceError('unreviewed source fields or review date')
        if (source.get('review_status') != 'PDF_TEXT_AND_PIXELS_REVIEWED'
                or any(source.get(k) != reviewed[k] for k in ('url', 'revision', 'page', 'pdf_sha256'))):
            raise ReferenceError('source changed; independent review required')
        if canonical(model.get('dimensions_mm')) != canonical(reviewed['dimensions_mm']):
            raise ReferenceError('dimensions or tolerance bounds changed; review the original drawing')
        bindings = model.get('parameter_bindings', [])
        expected_ids = [f'MN-{key}-PACKAGE-{axis}' for axis in ('LENGTH', 'WIDTH', 'HEIGHT')]
        if [b.get('id') for b in bindings] != expected_ids:
            raise ReferenceError('wrong or reordered package dimension bindings')
        source_rows = []
        for index, binding in enumerate(bindings):
            if set(binding) != {'id', 'sha256'}:
                raise ReferenceError('unreviewed binding fields')
            row = rows.get(binding['id'])
            if not row or row_hash(row) != binding.get('sha256'):
                raise ReferenceError('registry row changed; review required: ' + binding['id'])
            expected = {
                'asset_id': 'AST-SENSOR-GY91-001', 'unit': 'mm',
                'property': ('package_length', 'package_width', 'package_height')[index],
                'evidence_level': 'MANUFACTURER_NOMINAL_REFERENCE',
                'model_status': 'UNRESOLVED_VARIANT', 'conflict': False, 'conflict_group': None,
                'design_use': 'OFFLINE_CONCEPT_REFERENCE', 'design_scope': 'chip_package_reference_only',
                'source_url': reviewed['registry_source_url'],
                'source_revision': reviewed['registry_source_revision'],
                'model_claim': reviewed['registry_model_claim'],
            }
            if any(row.get(k) != v for k, v in expected.items()):
                raise ReferenceError('wrong evidence, asset, scope, conflict or units')
            value = row.get('value')
            if type(value) not in (int, float) or value != reviewed['dimensions_mm']['nominal'][index]:
                raise ReferenceError('nominal registry value disagrees with reviewed drawing')
            # These legacy rows have no tolerances; new limits come from the PDF,
            # not a silent reinterpretation of the product-page registry.
            if row.get('tolerance') is not None or row.get('tolerance_unit') is not None:
                raise ReferenceError('registry tolerance changed; source reconciliation required')
            source_rows.append(row)
        checked.append(dict(model, parameter_rows=source_rows))
    return checked


def generate(output: Path, registry_path: Path = REGISTRY, manifest_path: Path = MANIFEST) -> dict:
    registry_bytes, manifest_bytes = registry_path.read_bytes(), manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    models = validate_inputs(yaml.safe_load(registry_bytes), manifest)
    import cadquery as cq
    import OCP
    output.mkdir(parents=True, exist_ok=False)
    report = {
        'status': 'INCOMPLETE', 'scope': NOTICE, 'datum': DATUM,
        'manufacturing_release': False, 'physical_identity': 'UNVERIFIED',
        'cad_start': 'UNCHANGED_BLOCKED', 'unknown_features': manifest['unknown_features'],
        'inputs': {'registry_sha256': sha256(registry_bytes), 'manifest_sha256': sha256(manifest_bytes)},
        'generator_sha256': sha256(Path(__file__).read_bytes()),
        'geometry_validator_sha256': sha256((ROOT / 'cad_reference/generate_reference.py').read_bytes()),
        'versions': {'python': sys.version.split()[0], 'cadquery': cq.__version__,
                     'ocp': getattr(OCP, '__version__', 'unknown')},
        'models': models, 'exports': [],
        'warning': 'Six independent numeric reference boxes, not a GY-91 board, detailed replicas, installation layout or clearance approval.',
    }
    try:
        for item in models:
            for variant, dims in item['dimensions_mm'].items():
                name = item['model_id'] + '_PACKAGE_REFERENCE_ONLY_' + variant
                model = cq.Workplane('XY').box(*dims, centered=(False, False, False))
                original = check_shape(model.val(), dims)
                step, svg = output / (name + '.step'), output / (name + '.svg')
                cq.exporters.export(model, str(step))
                readback = check_shape(cq.importers.importStep(str(step)).val(), dims)
                cq.exporters.export(model, str(svg), opt={'width': 700, 'height': 400,
                    'showAxes': False, 'projectionDir': (1, -1, 1), 'strokeWidth': 0.1})
                report['exports'].append({'model_id': item['model_id'], 'variant': variant,
                    'dimensions_mm': dims, 'in_memory': original, 'step_readback': readback,
                    'files': [{'name': p.name, 'sha256': sha256(p.read_bytes()), 'bytes': p.stat().st_size}
                              for p in (step, svg)]})
        if registry_path.read_bytes() != registry_bytes or manifest_path.read_bytes() != manifest_bytes:
            raise ReferenceError('inputs changed during export')
        report['status'] = 'PASS_GEOMETRY_ROUNDTRIP_ONLY'
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        (output / 'validation.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        (output / 'README.txt').write_text(NOTICE + '\n'
            'MPU-9250 and BMP280 CHIP PACKAGE reference boxes; NOT the GY-91 board.\n'
            'Minimum, nominal and maximum are independent dimensional cases, not an assembly.\n'
            'The datum is an arbitrary box corner, NOT sensor/board axes or mounting coordinates.\n'
            'No pads, vent hole, solder, connectors, material volume or mass modeled.\n'
            'Retain validation.json with these files. No fit, manufacture or flight acceptance.\n')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='new output directory only')
    args = parser.parse_args()
    try:
        result = generate(args.output)
    except Exception as exc:
        print(json.dumps({'status': 'FAIL', 'error': str(exc)}))
        return 1
    print(json.dumps({'status': result['status'], 'exports': len(result['exports']), 'scope': NOTICE}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
