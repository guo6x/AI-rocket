"""Source-bound LQFP48 chip body, envelope and 48 planar recommended lands.

No core-board geometry, electrical mapping, PCB fabrication or fit approval.
The land STEP deliberately contains surfaces, not invented copper thickness.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

import yaml

try:
    from .generate_reference import ReferenceError, check_shape, read_step_shape, row_hash, sha256
    from .verify_package import load_receipt, read_file, same
except ImportError:
    from generate_reference import ReferenceError, check_shape, read_step_shape, row_hash, sha256
    from verify_package import load_receipt, read_file, same

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'cad_reference/apm32-reference-inputs.json'
ASSETS = ROOT / 'engineering/assets/project-asset-registry.yaml'
REVIEWED_MANIFEST = 'd1558be80a29b537c7c522918f9c74e3b5d485220c97ae70c3545b5c540b63c5'
REVIEWED_ASSET = '73efb4fe024bc4527e2ee934ce9eab360f30aeb17b99926cd2778c074e49a656'
NOTICE = 'APM32_CHIP_AND_RECOMMENDED_LAND_REFERENCE_ONLY_NOT_CORE_BOARD'
PREFIX = 'APM32F103C8T6_'
FILES = {
    'body': PREFIX + 'BODY_NOMINAL_REFERENCE_ONLY.step',
    'envelope': PREFIX + 'MAX_DIMENSIONS_REFERENCE_ONLY.step',
    'lands': PREFIX + 'RECOMMENDED_LANDS_REFERENCE_ONLY.step',
    'coordinates': 'land-coordinates-reference-only.json',
    'review': PREFIX + 'REFERENCE_ONLY.svg',
}
README_TEXT = (NOTICE + '\n'
    'Three independent references, not a core-board or an assembly.\n'
    'BODY: nominal 7 x 7 x 1.4 mm box, bottom Z=0.1 mm. No bent leads or mold details.\n'
    'MAX_DIMENSIONS: separate 9.2 x 9.2 x 1.6 mm numeric box, NOT material or fit clearance.\n'
    'LANDS: 48 planar faces at Z=0. No physical copper, mask, paste or solder thickness.\n'
    'Origin: package center at seating plane; XY orientation follows source Figure 19.\n'
    'Pin numbers are source drawing labels, not a verified board or electrical pin map.\n'
    'Keep validation.json and land-coordinates-reference-only.json with the STEP files.\n'
    'No fit, manufacture, PCB release, hardware operation or flight approval.\n')


def validate_inputs(assets: dict, manifest: dict) -> None:
    # Pin every reviewed field, including scope and unknowns. Updating a hash alone
    # is not evidence review; changes require inspecting the primary drawing again.
    if row_hash(manifest) != REVIEWED_MANIFEST:
        raise ReferenceError('APM32 source, dimensions or claims changed; source review required')
    rows = assets.get('assets', [])
    identifiers = [a.get('asset_id') for a in rows]
    if len(identifiers) != len(set(identifiers)):
        raise ReferenceError('duplicate purchase asset IDs')
    matches = [a for a in rows if a.get('asset_id') == manifest['asset_binding']['asset_id']]
    if (len(matches) != 1 or row_hash(matches[0]) != manifest['asset_binding']['sha256']
            or row_hash(matches[0]) != REVIEWED_ASSET):
        raise ReferenceError('purchase model or evidence changed; applicability review required')


def lands(manifest: dict) -> list[dict]:
    p = manifest['dimensions']['lands']
    half_row = (p['per_side'] - 1) * p['pitch'] / 2
    radial = (p['opposing_inner_span'] + p['opposing_outer_span']) / 4
    result = []
    for side in range(4):
        for i in range(p['per_side']):
            tangent = -half_row + i * p['pitch']
            x, y = ((tangent, -radial), (radial, tangent),
                    (-tangent, radial), (-radial, -tangent))[side]
            dx, dy = ((p['width'], p['radial_length']) if side % 2 == 0
                      else (p['radial_length'], p['width']))
            result.append({'pin': side * p['per_side'] + i + 1,
                           'center_mm': [x, y, 0.0], 'size_xy_mm': [dx, dy]})
    return result


def close(actual, expected, label):
    if len(actual) != len(expected) or any(
            type(a) not in (int, float) or not math.isfinite(a)
            or not math.isclose(a, b, abs_tol=1e-6, rel_tol=1e-8)
            for a, b in zip(actual, expected)):
        raise ReferenceError('geometry differs from reviewed ' + label)


def check_box(shape, dims, origin):
    result = check_shape(shape.translate(tuple(-x for x in origin)), dims)
    result['origin_mm'] = origin
    result['meaning'] = 'independent numeric reference box, not material volume or fit clearance'
    return result


def check_lands(shape, expected):
    """Verify every actual planar rectangle, not only aggregate bounding box/area."""
    def leaves(node):
        if node.ShapeType() == 'Face':
            return [node]
        if node.ShapeType() not in ('Compound', 'Shell'):
            raise ReferenceError('land pattern must contain only planar faces')
        children = list(node)
        if not children:
            raise ReferenceError('empty land topology')
        return [f for child in children for f in leaves(child)]

    faces = leaves(shape)
    if not shape.isValid() or len(faces) != 48 or len(expected) != 48:
        raise ReferenceError('expected 48 valid land faces')
    unmatched = list(expected)
    verified = []
    for face in faces:
        if face.geomType() != 'PLANE' or len(face.Wires()) != 1 or len(face.Edges()) != 4:
            raise ReferenceError('expected one planar rectangular wire for each land')
        if any(e.geomType() != 'LINE' for e in face.Edges()):
            raise ReferenceError('land boundary must use four straight edges')
        center = face.Center().toTuple()
        matches = [p for p in unmatched if all(abs(a-b) < 1e-6 for a, b in zip(center, p['center_mm']))]
        if len(matches) != 1:
            raise ReferenceError('missing, duplicate or displaced land')
        pad = matches[0]
        unmatched.remove(pad)
        x, y, z = pad['center_mm']
        dx, dy = pad['size_xy_mm']
        bb = face.BoundingBox()
        close([bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax],
              [x-dx/2, y-dy/2, z, x+dx/2, y+dy/2, z], 'land edges')
        vertices = sorted(v.toTuple() for v in face.Vertices())
        corners = sorted((x+sx*dx/2, y+sy*dy/2, z) for sx in (-1, 1) for sy in (-1, 1))
        if len(vertices) != 4:
            raise ReferenceError('land must have four corners')
        for vertex, corner in zip(vertices, corners):
            close(vertex, corner, 'land corners')
        close([face.Area()], [dx*dy], 'land area')
        verified.append(pad)
    if unmatched:
        raise ReferenceError('missing lands')
    return {'valid_planar_faces': 48, 'solids': 0, 'plane_z_mm': 0.0,
            'total_area_mm2': 17.28, 'lands': sorted(verified, key=lambda p: p['pin']),
            'meaning': 'recommended 2D land surfaces, no physical copper or solder thickness'}


def box_specs(manifest):
    d = manifest['dimensions']
    body = d['body_xy_nominal'] + [d['body_thickness_nominal']]
    outer = [v + d['lead_span_tolerance'] for v in d['lead_span_nominal']]
    return {'body': (body, [-body[0]/2, -body[1]/2, d['stand_off_nominal']]),
            'envelope': (outer + [d['overall_height_maximum']], [-outer[0]/2, -outer[1]/2, 0.0])}


def coordinate_data(manifest, pads):
    return {'scope': NOTICE, 'units': 'mm', 'datum': manifest['datum'],
            'manufacturing_release': False, 'source': manifest['source'], 'lands': pads}


def render_svg(pads):
    """Human-readable source-dimension review; positions use verified STEP faces."""
    s = 44
    ox, oy = 338, 372
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="780" viewBox="0 0 960 780">',
        '<rect width="960" height="780" fill="#f6f8fb"/>',
        '<g font-family="sans-serif" fill="#162337">',
        '<text x="36" y="42" font-size="24" font-weight="bold">APM32F103C8T6 / LQFP48</text>',
        '<text x="36" y="70" font-size="17">48-pad manufacturer-recommended land reference</text>',
        '<text x="36" y="98" font-size="15" fill="#a02b30">REFERENCE ONLY. NOT THE PURCHASED CORE BOARD. NO PCB / FIT RELEASE.</text>',
        f'<rect x="{ox-4.6*s}" y="{oy-4.6*s}" width="{9.2*s}" height="{9.2*s}" fill="none" stroke="#ab651b" stroke-dasharray="7 5"/>',
        f'<rect x="{ox-3.5*s}" y="{oy-3.5*s}" width="{7*s}" height="{7*s}" fill="#e4ebf3" stroke="#586b83"/>']
    for pad in pads:
        x, y, _ = pad['center_mm']
        dx, dy = pad['size_xy_mm']
        parts.append(f'<rect x="{ox+(x-dx/2)*s:.3f}" y="{oy-(y+dy/2)*s:.3f}" width="{dx*s:.3f}" height="{dy*s:.3f}" fill="#248a97" stroke="#11505a" stroke-width="0.7"/>')
        tx, ty = ox+x*s, oy-y*s
        if abs(x) > 4: tx += 38 if x > 0 else -38
        else: ty += 42 if y < 0 else -36
        parts.append(f'<text x="{tx:.3f}" y="{ty+4:.3f}" text-anchor="middle" font-size="10">{pad["pin"]}</text>')
    parts.extend([
        f'<path d="M {ox-12} {oy} h 24 M {ox} {oy-12} v 24" stroke="#586b83"/>',
        f'<text x="{ox}" y="{oy+34}" text-anchor="middle" font-size="15">Body outline: 7.00 x 7.00</text>',
        f'<text x="{ox}" y="{oy+58}" text-anchor="middle" font-size="13">Center datum / +X right / +Y up</text>',
        '<text x="612" y="177" font-size="18" font-weight="bold">Drawing dimensions (mm)</text>',
        '<text x="612" y="210" font-size="16">48 lands, 12 per side</text>',
        '<text x="612" y="239" font-size="16">Each land: 0.30 x 1.20</text>',
        '<text x="612" y="268" font-size="16">Pitch: 0.50 / gap: 0.20</text>',
        '<text x="612" y="297" font-size="16">Inner / outer span: 7.30 / 9.70</text>',
        '<text x="612" y="326" font-size="16">Land-row span: 5.80</text>',
        '<text x="612" y="372" font-size="18" font-weight="bold">Separate 3D STEP references</text>',
        '<text x="612" y="405" font-size="16">Body: 7 x 7 x 1.4 at Z=0.1</text>',
        '<text x="612" y="434" font-size="16">Body top: Z=1.5 (derived)</text>',
        '<text x="612" y="463" font-size="16">Max dimensions: 9.2 x 9.2 x 1.6</text>',
        '<text x="612" y="492" font-size="14" fill="#ab651b">Dashed outline = max-dimension box</text>',
        '<text x="612" y="535" font-size="14">Lands are planar surfaces at Z=0.</text>',
        '<text x="612" y="558" font-size="14">No invented copper / solder thickness.</text>',
        '<text x="36" y="652" font-size="15">Reference axes and pin numbers follow Figure 19, not the unverified purchased board.</text>',
        '<text x="36" y="680" font-size="15">Source: Geehy APM32F103x4x6x8 datasheet V1.5, printed pp45-47 / PDF46-48.</text>',
        '<text x="36" y="708" font-size="15">Exact order-code mapping: printed p54 / PDF55. Dimensions in mm; review image not to scale.</text>',
        '<text x="36" y="742" font-size="14" fill="#a02b30">Physical identity unverified. Mounting, USB, headers, board shape and installation clearance unknown.</text>',
        '</g></svg>'])
    return '\n'.join(parts) + '\n'


def generate(output: Path, manifest_path: Path = MANIFEST, assets_path: Path = ASSETS):
    mb, ab = manifest_path.read_bytes(), assets_path.read_bytes()
    manifest = load_receipt(mb)
    validate_inputs(yaml.safe_load(ab), manifest)
    import cadquery as cq
    import OCP
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'INCOMPLETE', 'scope': NOTICE, 'physical_identity': 'UNVERIFIED',
        'manufacturing_release': False, 'cad_start': 'UNCHANGED_BLOCKED',
        'inputs': {'manifest_sha256': sha256(mb), 'assets_sha256': sha256(ab)},
        'generator_sha256': sha256(Path(__file__).read_bytes()),
        'versions': {'python': sys.version.split()[0], 'cadquery': cq.__version__, 'ocp': OCP.__version__},
        'exports': {}, 'files': []}
    try:
        for kind, (dims, origin) in box_specs(manifest).items():
            shape = cq.Workplane('XY').box(*dims, centered=False).translate(tuple(origin)).val()
            check_box(shape, dims, origin)
            path = output / FILES[kind]
            cq.exporters.export(shape, str(path))
            report['exports'][kind] = check_box(read_step_shape(path), dims, origin)
        pads = lands(manifest)
        faces = [cq.Face.makeFromWires(cq.Workplane('XY').center(*p['center_mm'][:2])
                 .rect(*p['size_xy_mm']).val()) for p in pads]
        shape = cq.Compound.makeCompound(faces)
        check_lands(shape, pads)
        cq.exporters.export(shape, str(output / FILES['lands']))
        checked = check_lands(read_step_shape(output / FILES['lands']), pads)
        report['exports']['lands'] = checked
        (output / FILES['coordinates']).write_text(json.dumps(coordinate_data(manifest, checked['lands']), indent=2) + '\n')
        (output / FILES['review']).write_text(render_svg(checked['lands']))
        (output / 'README.txt').write_text(README_TEXT)
        report['files'] = [{'name': name, 'sha256': sha256((output/name).read_bytes()), 'bytes': (output/name).stat().st_size}
                           for name in [*FILES.values(), 'README.txt']]
        if mb != manifest_path.read_bytes() or ab != assets_path.read_bytes():
            raise ReferenceError('inputs changed during generation')
        report['status'] = 'PASS_GEOMETRY_ROUNDTRIP_ONLY'
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        (output / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def verify(package: Path, manifest_path: Path = MANIFEST, assets_path: Path = ASSETS):
    if package.is_symlink() or not package.is_dir():
        raise ReferenceError('expected a real package directory')
    mb, ab = manifest_path.read_bytes(), assets_path.read_bytes()
    manifest = load_receipt(mb)
    validate_inputs(yaml.safe_load(ab), manifest)
    names = {*FILES.values(), 'README.txt', 'validation.json'}
    if {p.name for p in package.iterdir()} != names:
        raise ReferenceError('unexpected or missing APM32 package files')
    data = {name: read_file(package / name) for name in names}
    report = load_receipt(data['validation.json'])
    same(sorted(report), sorted(['status', 'scope', 'physical_identity', 'manufacturing_release',
         'cad_start', 'inputs', 'generator_sha256', 'versions', 'exports', 'files']), 'receipt fields')
    same(report['status'], 'PASS_GEOMETRY_ROUNDTRIP_ONLY', 'generation status')
    same(report['scope'], NOTICE, 'reference-only scope')
    same(report['physical_identity'], 'UNVERIFIED', 'physical identity')
    same(report['manufacturing_release'], False, 'release')
    same(report['cad_start'], 'UNCHANGED_BLOCKED', 'CAD_START')
    same(report['inputs'], {'manifest_sha256': sha256(mb), 'assets_sha256': sha256(ab)}, 'input hashes')
    same(report['generator_sha256'], sha256(Path(__file__).read_bytes()), 'generator source')
    if (set(report['versions']) != {'python', 'cadquery', 'ocp'}
            or any(type(v) is not str or not v or len(v) > 100 for v in report['versions'].values())):
        raise ReferenceError('invalid producer versions')
    same(data['README.txt'].decode(), README_TEXT, 'reference disclaimer')
    same(report['files'], [{'name': n, 'sha256': sha256(data[n]), 'bytes': len(data[n])}
         for n in [*FILES.values(), 'README.txt']], 'delivered file digests')
    expected = {}
    for kind, (dims, origin) in box_specs(manifest).items():
        expected[kind] = check_box(read_step_shape(package/FILES[kind]), dims, origin)
    expected['lands'] = check_lands(read_step_shape(package/FILES['lands']), lands(manifest))
    # Numeric reports tolerate only insignificant kernel roundoff; all structural
    # fields/claims and pin coordinates must still match independently reimported STEP.
    same(sorted(report['exports']), sorted(expected), 'export set')
    for kind in ('body', 'envelope'):
        actual = report['exports'][kind]
        same(sorted(actual), sorted(expected[kind]), 'box report fields')
        for key in expected[kind]:
            if key in ('bbox_mm', 'origin_mm'):
                close(actual[key], expected[kind][key], key)
            elif key == 'envelope_volume_mm3':
                close([actual[key]], [expected[kind][key]], key)
            else:
                same(actual[key], expected[kind][key], key)
    same(report['exports']['lands'], expected['lands'], 'actual land geometry')
    same(load_receipt(data[FILES['coordinates']]), coordinate_data(manifest, expected['lands']['lands']), 'pin coordinates')
    same(data[FILES['review']].decode(), render_svg(expected['lands']['lands']), 'STEP-derived review SVG')
    if any(read_file(package/name) != content for name, content in data.items()):
        raise ReferenceError('package changed during read-only verification')
    return {'status': 'PASS_DELIVERED_GEOMETRY_ONLY', 'scope': NOTICE, 'step_files': 3,
            'planar_lands': 48, 'manufacturing_release': False, 'cad_start': 'UNCHANGED_BLOCKED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--output', type=Path, help='new output directory only')
    action.add_argument('--check', type=Path, help='read-only delivered-package verification')
    args = parser.parse_args()
    try:
        result = generate(args.output) if args.output else verify(args.check)
        print(json.dumps({'status': result['status'], 'scope': NOTICE}))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'FAIL', 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
