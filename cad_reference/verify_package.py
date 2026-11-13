"""Read-only verification of delivered reference files against reviewed sources.

Checks actual STEP geometry, exact inventories, hashes and source binding.
A geometry-only result does not authenticate a manufacturer, a physical unit,
or this checkout. Use a trusted reviewed checkout; this is not a signature.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import stat
import sys

import yaml

try:
    from . import generate_reference as ra02
    from . import generate_sensor_reference as sensor
except ImportError:
    import generate_reference as ra02
    import generate_sensor_reference as sensor

ROOT = Path(__file__).resolve().parents[1]
Error = ra02.ReferenceError
STATUS = 'PASS_DELIVERED_GEOMETRY_ONLY'


def same(actual, expected, label):
    """Type-sensitive JSON equality rejects bool-as-one and non-finite values."""
    if json.dumps(actual, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        raise Error('unexpected ' + label)


def read_file(path: Path) -> bytes:
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode):
        raise Error('reference files must be regular files, not links: ' + path.name)
    return path.read_bytes()


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Error('duplicate JSON key: ' + key)
        result[key] = value
    return result


def load_receipt(data: bytes):
    return json.loads(data, object_pairs_hook=reject_duplicate_keys,
                      parse_constant=lambda x: (_ for _ in ()).throw(Error('non-finite JSON: ' + x)))


def validate_numeric_report(row, actual):
    if set(row) != set(actual):
        raise Error('unexpected geometry report fields')
    for key in ('valid_closed_solids', 'meaning'):
        same(row[key], actual[key], key)
    for key in ('bbox_mm', 'origin_mm', 'envelope_volume_mm3'):
        if isinstance(row[key], list) != isinstance(actual[key], list):
            raise Error('geometry report scalar/list structure disagrees: ' + key)
        values = row[key] if isinstance(row[key], list) else [row[key]]
        expected = actual[key] if isinstance(actual[key], list) else [actual[key]]
        if len(values) != len(expected) or any(
            type(a) not in (int, float) or not math.isfinite(a)
            or not math.isclose(a, b, abs_tol=1e-6, rel_tol=1e-8)
            for a, b in zip(values, expected)
        ):
            raise Error('recorded geometry disagrees with actual STEP: ' + key)


def verify(package: Path, kind: str, root: Path = ROOT) -> dict:
    if kind not in ('ra02', 'sensors'):
        raise Error('choose ra02 or sensors explicitly')
    if package.is_symlink() or not package.is_dir():
        raise Error('package must be a real directory, not a symlink')
    registry_bytes = (root / 'engineering/parameter-registry.yaml').read_bytes()
    registry = yaml.safe_load(registry_bytes)
    generator = ra02 if kind == 'ra02' else sensor
    manifest_name = 'reference-inputs.json' if kind == 'ra02' else 'sensor-reference-inputs.json'
    generator_name = 'generate_reference.py' if kind == 'ra02' else 'generate_sensor_reference.py'
    manifest_bytes = (root / 'cad_reference' / manifest_name).read_bytes()
    manifest = load_receipt(manifest_bytes)
    receipt_bytes = read_file(package / 'validation.json')
    report = load_receipt(receipt_bytes)
    common = {'status', 'scope', 'inputs', 'generator_sha256', 'versions', 'physical_identity',
              'manufacturing_release', 'cad_start', 'unknown_features', 'exports', 'warning'}
    same(sorted(report), sorted(common | ({'source', 'parameter_rows'} if kind == 'ra02'
        else {'datum', 'geometry_validator_sha256', 'models'})), 'receipt fields')
    same(report['status'], 'PASS_GEOMETRY_ROUNDTRIP_ONLY', 'generation status')
    same(report['scope'], generator.NOTICE, 'reference scope')
    same(report['physical_identity'], 'UNVERIFIED', 'physical identity')
    same(report['manufacturing_release'], False, 'manufacturing release')
    same(report['cad_start'], 'UNCHANGED_BLOCKED', 'CAD_START')
    same(report['unknown_features'], manifest['unknown_features'], 'unknown features')
    same(report['inputs'], {'registry_sha256': ra02.sha256(registry_bytes),
                           'manifest_sha256': ra02.sha256(manifest_bytes)}, 'source input hashes')
    same(report['generator_sha256'], ra02.sha256((root / 'cad_reference' / generator_name).read_bytes()),
         'generator hash; use the matching reviewed source snapshot')
    if (set(report['versions']) != {'python', 'cadquery', 'ocp'}
            or any(type(v) is not str or not v or len(v) > 100 for v in report['versions'].values())):
        raise Error('invalid producer version metadata')

    expected = []
    if kind == 'ra02':
        dims, tol, rows = ra02.validate_inputs(registry, manifest)
        same(report['source'], manifest['source'], 'source metadata')
        same(report['parameter_rows'], rows, 'reviewed source rows')
        same(report['warning'], 'Independent reference boxes only. Thickness variants are not complete worst-case fit envelopes.', 'warning')
        for variant, z in [('height_low', dims[2] - tol), ('nominal', dims[2]), ('height_high', dims[2] + tol)]:
            expected.append(('RA02_V11_REFERENCE_ONLY_' + variant, variant, [dims[0], dims[1], z], None))
    else:
        models = sensor.validate_inputs(registry, manifest)
        same(report['models'], models, 'reviewed sensor models')
        same(report['datum'], sensor.DATUM, 'datum meaning')
        same(report['geometry_validator_sha256'], ra02.sha256((root / 'cad_reference/generate_reference.py').read_bytes()), 'geometry validator hash')
        same(report['warning'], 'Six independent numeric reference boxes, not a GY-91 board, detailed replicas, installation layout or clearance approval.', 'warning')
        for model in models:
            for variant, dims in model['dimensions_mm'].items():
                expected.append((model['model_id'] + '_PACKAGE_REFERENCE_ONLY_' + variant,
                                 variant, dims, model['model_id']))

    if type(report['exports']) is not list or len(report['exports']) != len(expected):
        raise Error('missing or extra exported models')
    file_names = {'validation.json', 'README.txt'}
    for name, _, _, _ in expected:
        file_names.update((name + '.step', name + '.svg'))
    if {p.name for p in package.iterdir()} != file_names:
        raise Error('package file inventory differs from reviewed reference set')
    readme = read_file(package / 'README.txt').decode('utf-8')
    same(readme, generator.README_TEXT, 'reference-only README')

    verified = []
    for export, (name, variant, dims, model_id) in zip(report['exports'], expected):
        same(sorted(export), sorted({'variant', 'dimensions_mm', 'in_memory', 'step_readback', 'files'}
                                   | ({'model_id'} if model_id else set())), 'export fields')
        same(export['variant'], variant, 'variant order or identity')
        same(export['dimensions_mm'], dims, 'source-derived dimensions')
        if model_id:
            same(export['model_id'], model_id, 'model identity')
        files = export['files']
        if type(files) is not list or len(files) != 2:
            raise Error('each model requires exactly STEP and SVG')
        for entry, suffix in zip(files, ('.step', '.svg')):
            same(sorted(entry), ['bytes', 'name', 'sha256'], 'file metadata fields')
            same(entry['name'], name + suffix, 'file name or path')
            data = read_file(package / (name + suffix))
            same(entry['sha256'], ra02.sha256(data), 'file checksum: ' + name + suffix)
            same(entry['bytes'], len(data), 'file size: ' + name + suffix)
        actual = ra02.check_shape(ra02.read_step_shape(package / (name + '.step')), dims)
        validate_numeric_report(export['in_memory'], actual)
        validate_numeric_report(export['step_readback'], actual)
        verified.append({'name': name, 'dimensions_mm': dims, 'geometry': actual})
    # Catch changed receipt/files during verification instead of attaching PASS
    # to a file set that no longer matches the checked bytes.
    if read_file(package / 'validation.json') != receipt_bytes:
        raise Error('receipt changed during verification')
    if ({p.name for p in package.iterdir()} != file_names
            or read_file(package / 'README.txt').decode('utf-8') != readme):
        raise Error('package inventory or README changed during verification')
    if ((root / 'engineering/parameter-registry.yaml').read_bytes() != registry_bytes
            or (root / 'cad_reference' / manifest_name).read_bytes() != manifest_bytes):
        raise Error('source inputs changed during verification')
    for export in report['exports']:
        for entry in export['files']:
            if ra02.sha256(read_file(package / entry['name'])) != entry['sha256']:
                raise Error('reference files changed during verification')
    return {'status': STATUS, 'scope': generator.NOTICE, 'manufacturing_release': False,
            'physical_identity': 'UNVERIFIED', 'cad_start': 'UNCHANGED_BLOCKED',
            'receipt_sha256': ra02.sha256(receipt_bytes), 'verified_models': verified,
            'verifier_sha256': ra02.sha256(Path(__file__).read_bytes()),
            'limitation': 'Internal consistency against this trusted source snapshot only; not a signature, received-unit identity, fit, hardware or manufacturing approval.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', required=True, type=Path)
    p.add_argument('--kind', required=True, choices=('ra02', 'sensors'))
    args = p.parse_args()
    try:
        result = verify(args.package, args.kind)
    except Exception as exc:
        print(json.dumps({'status': 'FAIL', 'error': str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
