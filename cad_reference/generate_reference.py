"""Source-bound unpowered electronics reference boxes, never current article CAD.

No hardware access, placement, fit, mounting features or manufacturing release.
Only the reviewed Ra-02 dimensional source is enabled in this initial package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'cad_reference/reference-inputs.json'
REGISTRY = ROOT / 'engineering/parameter-registry.yaml'
PARAMETERS = ('MN-RA02-LENGTH', 'MN-RA02-WIDTH', 'MN-RA02-HEIGHT')
NOTICE = 'REFERENCE_ONLY_NOT_FOR_FIT_MANUFACTURE_OR_FLIGHT'
UNKNOWN_FEATURES = ('placement', 'mounting_holes', 'mating_connector', 'wire_envelope',
                    'antenna_clearance', 'length_tolerance', 'width_tolerance')


class ReferenceError(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def row_hash(row: dict) -> str:
    return sha256(json.dumps(row, sort_keys=True, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode())


def validate_inputs(registry: dict, manifest: dict) -> tuple[list[float], float, list[dict]]:
    """Reject changed provenance, units, conflicts, unknowns and invented fit claims."""
    if manifest.get('schema_version') != 1 or manifest.get('scope') != NOTICE:
        raise ReferenceError('wrong schema or reference-only scope')
    if manifest.get('manufacturing_release') is not False:
        raise ReferenceError('manufacturing_release must remain false')
    if manifest.get('physical_identity') != 'UNVERIFIED':
        raise ReferenceError('physical identity must remain unverified')
    if manifest.get('unknown_features') != dict.fromkeys(UNKNOWN_FEATURES):
        raise ReferenceError('unknown features must remain explicit nulls')
    if manifest.get('enabled_model') != 'ra02_v11_nominal_reference_box':
        raise ReferenceError('only the reviewed Ra-02 reference is enabled')
    layer = registry.get('manufacturer_nominal', {})
    if layer.get('evidence_level') != 'MANUFACTURER_NOMINAL_REFERENCE':
        raise ReferenceError('wrong evidence layer')
    parameters = layer.get('parameters', [])
    ids = [row.get('id') for row in parameters]
    if len(ids) != len(set(ids)):
        raise ReferenceError('duplicate parameter IDs')
    sources = {row['id']: row for row in parameters}
    bindings = manifest.get('parameter_bindings', [])
    if [b.get('id') for b in bindings] != list(PARAMETERS):
        raise ReferenceError('unreviewed dimension bindings')
    rows = []
    for binding, property_name in zip(bindings, ('module_length', 'module_width', 'module_height')):
        row = sources.get(binding['id'])
        if not row or row_hash(row) != binding.get('sha256'):
            raise ReferenceError('source changed or missing; review required: ' + binding['id'])
        expected = {
            'asset_id': 'AST-RF-RA02-001', 'property': property_name, 'unit': 'mm',
            'evidence_level': 'MANUFACTURER_NOMINAL_REFERENCE', 'conflict': False,
            'conflict_group': None, 'model_status': 'UNRESOLVED_VARIANT',
            'design_use': 'OFFLINE_CONCEPT_REFERENCE',
            'design_scope': 'module_reference_envelope_only',
        }
        if any(row.get(key) != val for key, val in expected.items()):
            raise ReferenceError('invalid evidence, asset, scope, conflict or units: ' + binding['id'])
        value = row.get('value')
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ReferenceError('dimension must be positive finite numeric mm')
        if row.get('source_url') != manifest.get('source', {}).get('url'):
            raise ReferenceError('source URL mismatch')
        rows.append(row)
    tolerance = rows[2].get('tolerance')
    if type(tolerance) not in (float, int) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ReferenceError('height tolerance must be explicit, finite and positive')
    if rows[2].get('tolerance_unit') != 'mm' or tolerance >= rows[2]['value']:
        raise ReferenceError('invalid height tolerance')
    if rows[0].get('tolerance') is not None or rows[1].get('tolerance') is not None:
        raise ReferenceError('length/width tolerance requires separate review')
    source = manifest.get('source', {})
    if source.get('review_status') != 'PDF_TEXT_AND_PIXELS_REVIEWED' or source.get('page') != 2:
        raise ReferenceError('reviewed source is required')
    if (source.get('pdf_sha256') != 'b4d1fa7502007b18a06620681eece42985f8eb8bf62279fdaea4f00cd977b59d'
            or source.get('revision') != 'Ra-02 V1.1, 2017-12-19'):
        raise ReferenceError('source PDF digest or revision changed; independent review required')
    return [float(row['value']) for row in rows], float(tolerance), rows


def check_shape(shape, dimensions: list[float]) -> dict:
    """Check OCC topology, unit-sensitive dimensions and independent analytic volume."""
    solids = shape.Solids()
    if (not shape.isValid() or len(solids) != 1 or not solids[0].Shells()
            or not all(shell.Closed() for shell in solids[0].Shells())):
        raise ReferenceError('expected exactly one valid closed solid')
    bb = shape.BoundingBox()
    lengths = [bb.xlen, bb.ylen, bb.zlen]
    minima = [bb.xmin, bb.ymin, bb.zmin]
    if not all(math.isclose(a, b, abs_tol=1e-6, rel_tol=1e-8)
               for a, b in zip(lengths, dimensions)):
        raise ReferenceError('read-back dimensions differ from source inputs')
    if not all(abs(v) <= 1e-6 for v in minima):
        raise ReferenceError('unexpected datum: reference corner must be origin')
    volume = shape.Volume()
    if not math.isclose(volume, math.prod(dimensions), rel_tol=1e-8, abs_tol=1e-6):
        raise ReferenceError('read-back volume differs from analytic box volume')
    return {'valid_closed_solids': 1, 'bbox_mm': lengths, 'origin_mm': minima,
            'envelope_volume_mm3': volume, 'meaning': 'box volume, not material volume or mass'}


def generate(output: Path, registry_path: Path = REGISTRY, manifest_path: Path = MANIFEST) -> dict:
    registry_bytes, manifest_bytes = registry_path.read_bytes(), manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    dims, height_tolerance, rows = validate_inputs(yaml.safe_load(registry_bytes), manifest)
    # Import optional CAD kernel only after rejecting invalid or blocked inputs.
    import cadquery as cq
    import OCP
    # Exclusive directory creation protects prior receipts from accidental overwrite.
    output.mkdir(parents=True, exist_ok=False)
    report = {
        'status': 'INCOMPLETE', 'scope': NOTICE,
        'inputs': {'registry_sha256': sha256(registry_bytes), 'manifest_sha256': sha256(manifest_bytes)},
        'generator_sha256': sha256(Path(__file__).read_bytes()),
        'versions': {'python': sys.version.split()[0], 'cadquery': cq.__version__,
                     'ocp': getattr(OCP, '__version__', 'unknown')},
        'physical_identity': 'UNVERIFIED', 'manufacturing_release': False,
        'cad_start': 'UNCHANGED_BLOCKED', 'unknown_features': manifest['unknown_features'],
        'source': manifest['source'], 'parameter_rows': rows, 'exports': [],
        'warning': 'Independent reference boxes only. Thickness variants are not complete worst-case fit envelopes.',
    }
    report_path = output / 'validation.json'
    try:
        for suffix, z in [('height_low', dims[2] - height_tolerance),
                          ('nominal', dims[2]), ('height_high', dims[2] + height_tolerance)]:
            size = [dims[0], dims[1], z]
            name = 'RA02_V11_REFERENCE_ONLY_' + suffix
            model = cq.Workplane('XY').box(*size, centered=(False, False, False))
            original = check_shape(model.val(), size)
            step, svg = output / (name + '.step'), output / (name + '.svg')
            assembly = cq.Assembly(model, name=name)
            cq.exporters.export(assembly.toCompound(), str(step))
            # STEP product fields do not reliably retain labels through all importers;
            # the filename, adjacent receipt and README remain required context.
            imported = cq.importers.importStep(str(step))
            recovered = check_shape(imported.val(), size)
            cq.exporters.export(model, str(svg), opt={'width': 700, 'height': 400,
                                'showAxes': False, 'projectionDir': (1, -1, 1), 'strokeWidth': 0.1})
            report['exports'].append({'variant': suffix, 'dimensions_mm': size,
                'in_memory': original, 'step_readback': recovered,
                'files': [{'name': p.name, 'sha256': sha256(p.read_bytes()), 'bytes': p.stat().st_size}
                          for p in (step, svg)]})
        if registry_path.read_bytes() != registry_bytes or manifest_path.read_bytes() != manifest_bytes:
            raise ReferenceError('inputs changed during export')
        report['status'] = 'PASS_GEOMETRY_ROUNDTRIP_ONLY'
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        (output / 'README.txt').write_text(NOTICE + '\n'
            'Ra-02 V1.1 source-bound rectangular references, NOT replicas or an assembly.\n'
            'No mating, antenna/cable clearance, material, mass, tolerances in X/Y or physical identity established.\n'
            'Height low/nominal/high are 3.1/3.2/3.3 mm, not full worst-case fit bounds.\n'
            'Do not manufacture or infer hardware safety from these files. Read validation.json.\n')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path, help='new directory; existing directories rejected')
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
