"""Turn one reviewed board measurement record into two REFERENCE-ONLY boxes.

No actual board data is bundled. No fitting, mounting, manufacturing or flight
acceptance. Evidence hashes detect changed bytes, not authenticity or accuracy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cad_reference.generate_reference import ReferenceError, check_shape, read_step_shape

SCOPE = 'BOARD_MEASUREMENT_ENVELOPE_REFERENCE_ONLY'
STATUS = 'PASS_INPUT_AND_GEOMETRY_CHECKS_ONLY'
DATUM = 'TOP_X_RIGHT_Y_UP_Z_ZERO_PCB_UNDERSIDE_L_ALONG_Y_W_ALONG_X'
COVERAGE = 'ALL_FIXED_RIGID_FEATURES_IN_CURRENT_RECORDED_STATE'
UNITS = {
    'APM32': 'AST-MCU-APM32-001',
    'ESP32S3': 'AST-MCU-ESP32S3-001',
    'RA02_U1': 'AST-RF-RA02-001',
    'RA02_U2': 'AST-RF-RA02-001',
    'GY91': 'AST-SENSOR-GY91-001',
}
DIMENSIONS = ('PCB_L', 'PCB_W', 'PCB_T', 'H_plus', 'H_minus',
              'X_min', 'X_max', 'Y_min', 'Y_max')
UNKNOWN = ('actual_pcb_contour', 'mounting_holes', 'header_coordinates',
           'mated_connectors', 'flexible_cables', 'antenna_rf_clearance',
           'thermal_clearance', 'service_space', 'placement', 'design_margin')
README = '''REFERENCE ONLY: arithmetic boxes from one reviewed measurement record.
Not the PCB contour, a detailed replica, a bracket, or an assembly.
OBSERVED_SPAN uses means of the recorded repeated readings.
UNCERTAINTY_EXPANDED uses reading extremes plus supplied uncertainty bounds.
Those bounds are estimates supplied by the record, not guaranteed physical limits.
No design clearance is silently added. Box volume is not material volume or mass.
No fit, mounting, manufacturing, flight, electrical or RF qualification.
Source files remain private. Keep the input record and evidence for re-verification.
A valid hash proves byte consistency, not who made a measurement or its accuracy.
No CAD authority or as-built registry is changed. Read validation.json.
'''


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2,
                      allow_nan=False).encode() + b'\n'


def exact(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ReferenceError(f'{label}: missing or unexpected fields')


def text_value(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ReferenceError(f'{label}: explicit reviewed description required')


def number(value, label):
    if type(value) not in (int, float):
        raise ReferenceError(f'{label}: finite numeric mm required (not blank/string/bool)')
    try:
        converted = float(value)
    except OverflowError:
        raise ReferenceError(f'{label}: numeric mm exceeds finite float range') from None
    if not math.isfinite(converted):
        raise ReferenceError(f'{label}: finite numeric mm required (not blank/string/bool)')
    return converted


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReferenceError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def load_record(path: Path):
    if path.is_symlink() or not path.is_file():
        raise ReferenceError('input must be a regular non-symlink file')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=no_duplicates,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ReferenceError(f'nonfinite JSON constant: {value}')))


def template(unit: str) -> dict:
    return {
        'schema_version': 1, 'scope': SCOPE, 'unit_id': unit, 'asset_id': UNITS[unit],
        'units': 'mm', 'datum': DATUM, 'coverage': None,
        'identity': {'pcb_markings_or_revision': None, 'recorded_assembly_state': None,
                     'orientation_and_extreme_features': None, 'evidence_ids': []},
        'method': {'date': None, 'instrument': None, 'resolution_mm': None,
                   'uncertainty_basis': None, 'unpowered': None},
        'review': {'reviewed_for_this_unit': None, 'reviewer_ref': None,
                   'transcription_checked': None},
        'evidence': [],
        'measurements': {key: {'readings_mm': None, 'uncertainty_mm': None,
                               'evidence_ids': []} for key in DIMENSIONS},
        'unknown_features': dict.fromkeys(UNKNOWN),
        'manufacturing_release': False, 'fit_accepted': False,
    }


def evidence_files(record: dict, base: Path) -> list[dict]:
    rows = record['evidence']
    if not isinstance(rows, list) or not rows:
        raise ReferenceError('local evidence files required; no invented sources')
    result, seen = [], set()
    base = base.resolve()
    for row in rows:
        exact(row, ('id', 'path', 'sha256', 'unit_id'), 'evidence')
        ident, relative = row['id'], row['path']
        if not isinstance(ident, str) or not re.fullmatch(r'EV-[A-Za-z0-9_-]+', ident) or ident in seen:
            raise ReferenceError('evidence IDs must be unique EV- identifiers')
        seen.add(ident)
        if row['unit_id'] != record['unit_id']:
            raise ReferenceError('evidence unit mismatch; U1/U2 cannot substitute for each other')
        if (not isinstance(relative, str) or not relative or '\\' in relative
                or ':' in relative or '\x00' in relative):
            raise ReferenceError('evidence path must be a local relative POSIX path')
        path = PurePosixPath(relative)
        if path.is_absolute() or '..' in path.parts or not path.parts:
            raise ReferenceError('evidence path must stay inside the private input directory')
        target = base.joinpath(*path.parts)
        if any(base.joinpath(*path.parts[:n]).is_symlink() for n in range(1, len(path.parts) + 1)):
            raise ReferenceError('evidence symlinks are not accepted')
        if not target.is_file():
            raise ReferenceError(f'evidence file missing: {ident}')
        data = target.read_bytes()
        if not data or digest(data) != row['sha256']:
            raise ReferenceError(f'evidence digest mismatch or empty file: {ident}')
        result.append({'id': ident, 'sha256': row['sha256'], 'unit_id': row['unit_id']})
    return result


def validate(record: dict, base: Path) -> dict:
    exact(record, template('APM32'), 'record')
    if type(record['schema_version']) is not int or record['schema_version'] != 1:
        raise ReferenceError('unsupported schema')
    unit = record['unit_id']
    if not isinstance(unit, str) or unit not in UNITS or record['asset_id'] != UNITS[unit]:
        raise ReferenceError('unknown unit or mismatched asset')
    if (record['scope'] != SCOPE or record['units'] != 'mm' or record['datum'] != DATUM
            or record['coverage'] != COVERAGE):
        raise ReferenceError('explicit mm, worksheet datum and complete rigid coverage required')
    if record['manufacturing_release'] is not False or record['fit_accepted'] is not False:
        raise ReferenceError('cannot promote a reference to accepted fit or manufacturing')
    if record['unknown_features'] != dict.fromkeys(UNKNOWN):
        raise ReferenceError('unknown mounting/cable/contour/design fields must remain null')
    identity, method, review = record['identity'], record['method'], record['review']
    exact(identity, ('pcb_markings_or_revision', 'recorded_assembly_state',
                     'orientation_and_extreme_features', 'evidence_ids'), 'identity')
    exact(method, ('date', 'instrument', 'resolution_mm', 'uncertainty_basis', 'unpowered'), 'method')
    exact(review, ('reviewed_for_this_unit', 'reviewer_ref', 'transcription_checked'), 'review')
    for key in ('pcb_markings_or_revision', 'recorded_assembly_state', 'orientation_and_extreme_features'):
        text_value(identity[key], key)
    for key in ('date', 'instrument', 'uncertainty_basis'):
        text_value(method[key], key)
    from datetime import date
    try:
        date.fromisoformat(method['date'])
    except (ValueError, TypeError):
        raise ReferenceError('method date must be a real ISO date') from None
    resolution = number(method['resolution_mm'], 'resolution')
    if resolution <= 0 or method['unpowered'] is not True:
        raise ReferenceError('positive instrument resolution and unpowered record required')
    if review['reviewed_for_this_unit'] is not True or review['transcription_checked'] is not True:
        raise ReferenceError('explicit per-unit review and transcription check required')
    text_value(review['reviewer_ref'], 'reviewer_ref')
    sources = evidence_files(record, base)
    ids = {row['id'] for row in sources}

    def refs(value):
        if (not isinstance(value, list) or not value or
                any(not isinstance(v, str) for v in value) or
                len(set(value)) != len(value) or not set(value) <= ids):
            raise ReferenceError('each identity/measurement requires unique known evidence IDs')
    refs(identity['evidence_ids'])
    exact(record['measurements'], DIMENSIONS, 'measurements')
    stats = {}
    for key, row in record['measurements'].items():
        exact(row, ('readings_mm', 'uncertainty_mm', 'evidence_ids'), key)
        values = row['readings_mm']
        if not isinstance(values, list) or len(values) < 3:
            raise ReferenceError(f'{key}: at least three retained readings required')
        values = [number(value, key) for value in values]
        uncertainty = number(row['uncertainty_mm'], key + ' uncertainty')
        if uncertainty <= 0:
            raise ReferenceError(f'{key}: positive uncertainty required; unknown is not zero')
        refs(row['evidence_ids'])
        mean = sum(value / len(values) for value in values)
        low, high = min(values) - uncertainty, max(values) + uncertainty
        if not all(math.isfinite(v) for v in (mean, low, high)):
            raise ReferenceError('nonfinite calculated interval')
        if key.startswith('PCB_') and low <= 0:
            raise ReferenceError(f'{key}: board dimensions must remain positive with uncertainty')
        if key in ('H_plus', 'H_minus'):
            if min(values) < 0:
                raise ReferenceError('H+ and H- are nonnegative distances, not signed Z coordinates')
            low = max(0, low)
        stats[key] = {'mean': mean, 'low': low, 'high': high}
    m = {key: value['mean'] for key, value in stats.items()}
    if (m['X_min'] > 0 or m['Y_min'] > 0 or m['X_max'] < m['PCB_W']
            or m['Y_max'] < m['PCB_L']):
        raise ReferenceError('rigid envelope must contain PCB spans in the worksheet datum')
    observed = [m['X_min'], m['Y_min'], -m['H_minus'],
                m['X_max'], m['Y_max'], m['PCB_T'] + m['H_plus']]
    expanded = [stats['X_min']['low'], stats['Y_min']['low'], -stats['H_minus']['high'],
                stats['X_max']['high'], stats['Y_max']['high'],
                stats['PCB_T']['high'] + stats['H_plus']['high']]
    if (expanded[3] < stats['PCB_W']['high'] or expanded[4] < stats['PCB_L']['high']):
        raise ReferenceError('expanded complete envelope contradicts PCB span bounds')
    for box in (observed, expanded):
        sizes = [box[i + 3] - box[i] for i in range(3)]
        if any(not math.isfinite(v) or v <= 0 for v in sizes) or not math.isfinite(math.prod(sizes)):
            raise ReferenceError('invalid or nonfinite calculated box')
    return {
        'unit_id': unit, 'asset_id': record['asset_id'], 'scope': SCOPE,
        'input_sha256': digest(canonical(record)), 'sources': sources,
        'coordinate_order': ['xmin', 'ymin', 'zmin', 'xmax', 'ymax', 'zmax'],
        'boxes_mm': {'OBSERVED_SPAN': observed, 'UNCERTAINTY_EXPANDED': expanded},
        'measurement_intervals_mm': stats,
        'unknown_features': dict.fromkeys(UNKNOWN),
        'fit_accepted': False, 'manufacturing_release': False,
        'physical_measurements_verified_by_software': False,
        'meaning': 'Input arithmetic and geometry only. Human evidence assertions are not authenticated.',
    }


def check_box(shape, bounds):
    sizes = [bounds[i + 3] - bounds[i] for i in range(3)]
    # Reuse strict topology, loose geometry, box volume and dimension checks.
    return check_shape(shape.translate(tuple(-v for v in bounds[:3])), sizes)


def filenames(unit):
    return {kind: f'{unit}_{kind}_BOX_REFERENCE_ONLY.step'
            for kind in ('OBSERVED_SPAN', 'UNCERTAINTY_EXPANDED')}


def generate(input_path: Path, output: Path) -> dict:
    record = load_record(input_path)
    validated = validate(record, input_path.parent)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError('choose a new output directory; existing output is never overwritten')
    # Avoid a receipt overwriting the input or an input-directory alias via '..'.
    output = output.resolve()
    if output == input_path.parent.resolve() or output in input_path.resolve().parents:
        raise ReferenceError('output must be separate from the private input directory')
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'INCOMPLETE', 'validated_input': validated, 'exports': {}}
    receipt = output / 'validation.json'
    try:
        import cadquery as cq
        for kind, name in filenames(record['unit_id']).items():
            bounds = validated['boxes_mm'][kind]
            sizes = [bounds[i + 3] - bounds[i] for i in range(3)]
            shape = cq.Workplane('XY').box(*sizes, centered=False).val().translate(tuple(bounds[:3]))
            check_box(shape, bounds)
            path = output / name
            cq.exporters.export(shape, str(path))
            check_box(read_step_shape(path), bounds)
            report['exports'][name] = digest(path.read_bytes())
        # Re-read input and evidence to reject source mutations during CAD generation.
        if validate(load_record(input_path), input_path.parent) != validated:
            raise ReferenceError('input or evidence changed during generation')
        (output / 'README.txt').write_text(README, encoding='utf-8')
        report['status'] = STATUS
        receipt.write_bytes(canonical(report))
        verify(input_path, output)
    except Exception as error:
        report['status'] = 'INCOMPLETE'
        report['error'] = str(error)
        receipt.write_bytes(canonical(report))
        raise
    return report


def verify(input_path: Path, package: Path) -> dict:
    expected = validate(load_record(input_path), input_path.parent)
    names = filenames(expected['unit_id'])
    inventory = set(names.values()) | {'validation.json', 'README.txt'}
    if package.is_symlink() or not package.is_dir() or {p.name for p in package.iterdir()} != inventory:
        raise ReferenceError('package inventory differs or is not a regular directory')
    if any(p.is_symlink() or not p.is_file() for p in package.iterdir()):
        raise ReferenceError('package must contain regular non-symlink files')
    before = {p.name: p.read_bytes() for p in package.iterdir()}
    receipt = load_record(package / 'validation.json')
    exact(receipt, ('status', 'validated_input', 'exports'), 'receipt')
    if receipt['status'] != STATUS or receipt['validated_input'] != expected:
        raise ReferenceError('receipt does not match the current input/evidence')
    exact(receipt['exports'], names.values(), 'export inventory')
    if (package / 'README.txt').read_text(encoding='utf-8') != README:
        raise ReferenceError('reference warnings changed')
    for kind, name in names.items():
        path = package / name
        if digest(path.read_bytes()) != receipt['exports'][name]:
            raise ReferenceError('export digest mismatch')
        check_box(read_step_shape(path), expected['boxes_mm'][kind])
    if validate(load_record(input_path), input_path.parent) != expected:
        raise ReferenceError('input or evidence changed during verification')
    if (package.is_symlink() or {p.name for p in package.iterdir()} != inventory or
            any(p.is_symlink() or not p.is_file() for p in package.iterdir()) or
            {p.name: p.read_bytes() for p in package.iterdir()} != before):
        raise ReferenceError('package changed during verification')
    return {'status': STATUS, 'unit_id': expected['unit_id'], 'fit_accepted': False,
            'manufacturing_release': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('template')
    p.add_argument('--unit', choices=UNITS, required=True)
    p.add_argument('--output', type=Path, required=True)
    for command in ('generate', 'verify'):
        p = sub.add_parser(command)
        p.add_argument('--input', type=Path, required=True)
        p.add_argument('--output' if command == 'generate' else '--package', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'template':
            with args.output.open('xb') as target:
                target.write(canonical(template(args.unit)))
            print('Blank template only; no measurements or CAD generated.')
        else:
            result = generate(args.input, args.output) if args.command == 'generate' else verify(args.input, args.package)
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except (ReferenceError, OSError, ValueError, TypeError, KeyError) as error:
        print(f'REFUSED: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


