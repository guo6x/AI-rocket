"""Render only the purchased ESP32 seller thumbnail's numeric XY spans.

One planar rectangle, not a PCB contour, a zero-thickness physical board or an
installed assembly. Unknown height and interface positions remain unknown.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml

try:
    from .generate_reference import ReferenceError, read_step_shape, row_hash, sha256
    from .generate_apm32_reference import close
    from .verify_package import load_receipt, read_file, same
except ImportError:
    from generate_reference import ReferenceError, read_step_shape, row_hash, sha256
    from generate_apm32_reference import close
    from verify_package import load_receipt, read_file, same

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'cad_reference/board-span-reference-inputs.json'
ASSETS = ROOT / 'engineering/assets/project-asset-registry.yaml'
REVIEWED_MANIFEST = '125ecc4df65bbf60ea8584525aaef024f8890570a3a821aadf912efb512309eb'
REVIEWED_ASSET = '3778e3137b819f942ab4ecf7bbc04653a994877e8f121bbc4b954a9c08ffdf34'
NOTICE = 'SELLER_NUMERIC_SPANS_PLANAR_REFERENCE_ONLY_NOT_BOARD_CONTOUR'
STEP = 'ESP32S3_SELLER_SPANS_PLANAR_REFERENCE_ONLY.step'
SVG = 'ESP32S3_SELLER_SPANS_PLANAR_REFERENCE_ONLY.svg'
README_TEXT = (NOTICE + '\n'
    'Seller product thumbnail labels: 57 mm long span, 28 mm short span.\n'
    'One mathematical face at Z=0, not a board with physical thickness zero.\n'
    'Rectangle corners and center are abstract drawing references, not PCB datums.\n'
    'Antenna extends beyond the marked 57 mm boundary; full envelope is unknown.\n'
    'Height, tolerances, headers, USB, holes, keepouts and cables are UNKNOWN.\n'
    'No true board contour, fit, mounting, enclosure or manufacturing approval.\n'
    'Do not substitute an official Micro-USB board or another Type-C board.\n'
    'Keep the source manifest, README and validation receipt with this reference.\n')


def validate_inputs(assets, manifest):
    if row_hash(manifest) != REVIEWED_MANIFEST:
        raise ReferenceError('seller source, spans or scope changed; source review required')
    rows = assets.get('assets', [])
    ids = [r.get('asset_id') for r in rows]
    if len(ids) != len(set(ids)):
        raise ReferenceError('duplicate purchase asset IDs')
    matches = [r for r in rows if r.get('asset_id') == manifest['asset_binding']['asset_id']]
    if (len(matches) != 1 or row_hash(matches[0]) != REVIEWED_ASSET
            or manifest['asset_binding']['sha256'] != REVIEWED_ASSET):
        raise ReferenceError('purchase model changed; source applicability review required')


def check_plane(shape, long_span, short_span):
    """Check the actual STEP surface and all its boundaries, not a stored bbox."""
    def leaves(node):
        if node.ShapeType() == 'Face':
            return [node]
        if node.ShapeType() not in ('Compound', 'Shell'):
            raise ReferenceError('expected a planar face, not solid or loose geometry')
        children = list(node)
        if not children:
            raise ReferenceError('empty reference shape')
        return [face for child in children for face in leaves(child)]

    faces = leaves(shape)
    if not shape.isValid() or len(faces) != 1:
        raise ReferenceError('expected exactly one valid planar face')
    face = faces[0]
    if (face.geomType() != 'PLANE' or len(face.Wires()) != 1
            or len(face.Edges()) != 4
            or any(e.geomType() != 'LINE' for e in face.Edges())):
        raise ReferenceError('reference must be a rectangle without holes or curves')
    bb = face.BoundingBox()
    close([bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax],
          [-long_span/2, -short_span/2, 0, long_span/2, short_span/2, 0], 'seller spans')
    corners = sorted(v.toTuple() for v in face.Vertices())
    expected = sorted((sx*long_span/2, sy*short_span/2, 0)
                      for sx in (-1, 1) for sy in (-1, 1))
    if len(corners) != 4:
        raise ReferenceError('reference must have four corners')
    for actual, wanted in zip(corners, expected):
        close(actual, wanted, 'abstract rectangle corners')
    close([face.Area()], [long_span * short_span], 'numeric span area')
    return {'planar_faces': 1, 'solids': 0,
            'spans_mm': [bb.xlen, bb.ylen], 'plane_z_mm': 0.0,
            'numeric_rectangle_area_mm2': long_span * short_span,
            'physical_board_thickness_mm': None,
            'meaning': 'seller numeric-span reference; not physical PCB area or contour'}


def render_svg(checked):
    x, y = checked['spans_mm']
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="640" viewBox="0 0 1100 640">
<rect width="1100" height="640" fill="#f4f7fb"/>
<g font-family="Arial, sans-serif" fill="#20334d">
<text x="36" y="48" font-size="25" font-weight="bold">ESP32-S3 seller dimensions: planar reference</text>
<text x="36" y="82" font-size="17" fill="#a02b30">REFERENCE ONLY. Not a PCB contour, mounting layout or 3D assembly.</text>
<rect x="70" y="170" width="{x*8:g}" height="{y*8:g}" fill="#dbeef0" stroke="#167381" stroke-width="3"/>
<path d="M 70 140 H {70+x*8:g} M 70 130 V 150 M {70+x*8:g} 130 V 150" stroke="#20334d" fill="none"/>
<text x="{70+x*4:g}" y="124" text-anchor="middle" font-size="21">{x:g} mm seller label</text>
<path d="M 550 170 V {170+y*8:g} M 540 170 H 560 M 540 {170+y*8:g} H 560" stroke="#20334d" fill="none"/>
<text x="570" y="290" font-size="18">{y:g} mm</text>
<text x="{70+x*4:g}" y="265" text-anchor="middle" font-size="19">Numeric span rectangle</text>
<text x="{70+x*4:g}" y="298" text-anchor="middle" font-size="16">No inferred holes, pins or ports</text>
<text x="{70+x*4:g}" y="330" text-anchor="middle" font-size="16">Z=0 is only a reference plane</text>
<text x="670" y="177" font-size="20" font-weight="bold">Still unknown</text>
<text x="670" y="213" font-size="17">PCB-only outline / revision</text>
<text x="670" y="246" font-size="17">Thickness / complete assembled height</text>
<text x="670" y="279" font-size="17">Headers / USB positions / overhang</text>
<text x="670" y="312" font-size="17">Holes / tolerances / antenna keepout</text>
<text x="670" y="345" font-size="17">Cable bend space / installation fit</text>
<text x="36" y="448" font-size="17">Source: original purchase image 1000013496.jpg, seller product thumbnail.</text>
<text x="36" y="480" font-size="17">Selected option: ESP32-S3 N16R8, 44-pin. Type-C is a product-image label.</text>
<text x="36" y="512" font-size="17">Dimensions were read from printed labels, not estimated from pixel scale.</text>
<text x="36" y="544" font-size="17">Rectangle corners are abstract. Antenna extends beyond the marked 57 mm boundary; full envelope is unknown.</text>
<text x="36" y="580" font-size="17" fill="#a02b30">Physical identity unverified. Do not extrude to an assumed height or release an enclosure.</text>
<text x="36" y="612" font-size="14">Source image remains private. Review illustration not to scale. No manufacturing release.</text>
</g></svg>
'''


def inputs(manifest_path, assets_path):
    mb, ab = manifest_path.read_bytes(), assets_path.read_bytes()
    manifest = load_receipt(mb)
    validate_inputs(yaml.safe_load(ab), manifest)
    return mb, manifest, ab


def generate(output, manifest_path=MANIFEST, assets_path=ASSETS):
    mb, manifest, ab = inputs(manifest_path, assets_path)
    d = manifest['dimensions']
    x, y = d['long_span_mm'], d['short_span_mm']
    import cadquery as cq
    output.mkdir(parents=True, exist_ok=False)
    receipt = {'status': 'INCOMPLETE', 'scope': NOTICE,
               'manufacturing_release': False, 'physical_identity': 'UNVERIFIED',
               'cad_start': 'UNCHANGED_BLOCKED', 'manifest_sha256': sha256(mb),
               'asset_row_sha256': REVIEWED_ASSET,
               'generator_sha256': sha256(Path(__file__).read_bytes()),
               'geometry': {}, 'files': []}
    try:
        face = cq.Face.makeFromWires(cq.Workplane('XY').rect(x, y).val())
        check_plane(face, x, y)
        cq.exporters.export(face, str(output / STEP))
        receipt['geometry'] = check_plane(read_step_shape(output / STEP), x, y)
        (output / SVG).write_text(render_svg(receipt['geometry']))
        (output / 'README.txt').write_text(README_TEXT)
        receipt['files'] = [{'name': name, 'sha256': sha256((output/name).read_bytes())}
                            for name in (STEP, SVG, 'README.txt')]
        if mb != manifest_path.read_bytes() or ab != assets_path.read_bytes():
            raise ReferenceError('source inputs changed during generation')
        receipt['status'] = 'PASS_NUMERIC_SPANS_ONLY'
    except Exception as exc:
        receipt['error'] = str(exc)
        raise
    finally:
        (output / 'validation.json').write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


def verify(package, manifest_path=MANIFEST, assets_path=ASSETS):
    mb, manifest, _ = inputs(manifest_path, assets_path)
    names = {STEP, SVG, 'README.txt', 'validation.json'}
    if package.is_symlink() or not package.is_dir() or {p.name for p in package.iterdir()} != names:
        raise ReferenceError('expected exactly the planar reference package files')
    data = {name: read_file(package/name) for name in names}
    receipt = load_receipt(data['validation.json'])
    d = manifest['dimensions']
    geometry = check_plane(read_step_shape(package/STEP), d['long_span_mm'], d['short_span_mm'])
    expected = {'status': 'PASS_NUMERIC_SPANS_ONLY', 'scope': NOTICE,
                'manufacturing_release': False, 'physical_identity': 'UNVERIFIED',
                'cad_start': 'UNCHANGED_BLOCKED', 'manifest_sha256': sha256(mb),
                'asset_row_sha256': REVIEWED_ASSET,
                'generator_sha256': sha256(Path(__file__).read_bytes()),
                'geometry': geometry,
                'files': [{'name': n, 'sha256': sha256(data[n])} for n in (STEP, SVG, 'README.txt')]}
    same(receipt, expected, 'actual planar reference receipt')
    same(data[SVG].decode(), render_svg(geometry), 'STEP-derived review SVG')
    same(data['README.txt'].decode(), README_TEXT, 'scope warning')
    if any(read_file(package/n) != b for n, b in data.items()):
        raise ReferenceError('package changed during verification')
    return {'status': 'PASS_DELIVERED_NUMERIC_SPANS_ONLY', 'step_files': 1,
            'scope': NOTICE, 'manufacturing_release': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument('--output', type=Path)
    action.add_argument('--check', type=Path)
    args = p.parse_args()
    try:
        result = generate(args.output) if args.output else verify(args.check)
        print(json.dumps({'status': result['status'], 'scope': NOTICE}))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'FAIL', 'error': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
