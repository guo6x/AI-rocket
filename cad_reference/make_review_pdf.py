"""Three-page visual index of independently verified electronics reference STEP.

Nominal wireframes come from STEP vertices, not reused historical illustrations.
This is deliberately not a dimensioned manufacturing drawing or assembly.
"""
from __future__ import annotations

import argparse
from io import BytesIO
import json
import math
from pathlib import Path
import sys

try:
    from . import verify_package as verifier
    from . import generate_reference as ra02
    from . import generate_sensor_reference as sensor
except ImportError:
    import verify_package as verifier
    import generate_reference as ra02
    import generate_sensor_reference as sensor


def segments(shape, projection):
    """Project actual re-imported straight box edges; deduplicate coincident lines."""
    result = set()
    for edge in shape.Edges():
        vertices = edge.Vertices()
        if edge.geomType() != 'LINE' or len(vertices) != 2:
            raise ra02.ReferenceError('review sheet only supports the verified straight-edged references')
        points = [tuple(round(v, 8) for v in projection(*p.toTuple())) for p in vertices]
        if points[0] != points[1]:
            result.add(tuple(sorted(points)))
    return sorted(result)


def draw_view(canvas, shape, rectangle, projection, label):
    x, y, width, height = rectangle
    lines = segments(shape, projection)
    xs = [p[0] for line in lines for p in line]
    ys = [p[1] for line in lines for p in line]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    scale = min(width / (xmax - xmin), height / (ymax - ymin))
    dx = x + (width - scale * (xmax - xmin)) / 2 - scale * xmin
    dy = y + (height - scale * (ymax - ymin)) / 2 - scale * ymin
    canvas.setStrokeColorRGB(.15, .23, .31)
    canvas.setLineWidth(1.25)
    for a, b in lines:
        canvas.line(dx + a[0] * scale, dy + a[1] * scale, dx + b[0] * scale, dy + b[1] * scale)
    canvas.setFillColorRGB(.33, .38, .43)
    canvas.setFont('ReviewSans', 9)
    canvas.drawCentredString(x + width / 2, y - 18, label)


def render_review(ra02_dir: Path, sensor_dir: Path) -> bytes:
    """Render deterministic bytes without writing into or changing either package."""
    before = [verifier.verify(ra02_dir, 'ra02'), verifier.verify(sensor_dir, 'sensors')]
    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdfcanvas

    # Embed fonts shipped with the pinned ReportLab dependency so viewers do
    # not substitute a metric-incompatible system font. No host fonts needed.
    fonts = Path(reportlab.__file__).parent / 'fonts'
    pdfmetrics.registerFont(TTFont('ReviewSans', str(fonts / 'Vera.ttf')))
    pdfmetrics.registerFont(TTFont('ReviewSans-Bold', str(fonts / 'VeraBd.ttf')))
    stream = BytesIO()
    canvas = pdfcanvas.Canvas(stream, pagesize=A4, invariant=1, pageCompression=0)
    canvas.setTitle('AI-rocket electronics reference geometry - not for manufacture')
    canvas.setAuthor('AI-rocket reference CAD')
    width, height = A4
    records = [
        ('Ra-02 V1.1', 'Module reference box', ra02_dir, before[0]['verified_models'],
         'Ai-Thinker V1.1, 2017-12-19 | PDF page 2',
         'https://aithinker-static.oss-cn-shenzhen.aliyuncs.com/docs/Public%20Document%20Center/LoRa/lora/Specification/Ra-02_V1.1%20Specification-20171219.pdf',
         ['Length / width tolerance: unknown.', 'Connector, antenna, cable and mounting clearance: unknown.',
          'Thickness cases alone are not complete worst-case fit envelopes.'], before[0]),
        ('MPU-9250', 'Chip package reference box', sensor_dir,
         [r for r in before[1]['verified_models'] if r['name'].startswith('MPU9250')],
         'TDK PS-MPU-9250A-01 rev 1.1 | PDF page 39', sensor.REVIEWED['MPU9250']['url'],
         ['Not the GY-91 PCB or its installed height.', 'Pad seating height is not added to total package thickness.',
          'No pads, pin-1 mark, board placement or sensor axes are modeled.'], before[1]),
        ('BMP280', 'Chip package reference box', sensor_dir,
         [r for r in before[1]['verified_models'] if r['name'].startswith('BMP280')],
         'Bosch BST-BMP280-DS001-26 rev 1.26 | PDF page 38', sensor.REVIEWED['BMP280']['url'],
         ['Not the GY-91 PCB or a pressure-sensor housing.', 'Explicit XY +/-0.10 mm overrides the general +/-0.05 mm note.',
          'No vent path, lid details, solder stack or installation clearance.'], before[1]),
    ]
    for page, (title, subtitle, directory, models, source, url, caveats, receipt) in enumerate(records, 1):
        nominal = next(r for r in models if r['name'].endswith('_nominal'))
        shape = ra02.read_step_shape(directory / (nominal['name'] + '.step'))
        ra02.check_shape(shape, nominal['dimensions_mm'])
        canvas.setFillColor(colors.HexColor('#F4F6F8'))
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor('#153348'))
        canvas.setFont('ReviewSans-Bold', 11)
        canvas.drawString(38, height - 38, 'AI-ROCKET  /  REFERENCE CAD')
        canvas.setFont('ReviewSans', 10)
        canvas.drawRightString(width - 38, height - 38, f'{page:02d} / 03')
        canvas.setFont('ReviewSans-Bold', 28)
        canvas.drawString(38, height - 84, title)
        canvas.setFont('ReviewSans', 12)
        canvas.drawString(38, height - 106, subtitle)
        canvas.setFillColor(colors.HexColor('#FBE6CB'))
        canvas.roundRect(38, height - 149, width - 76, 26, 5, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor('#7E4312'))
        canvas.setFont('ReviewSans-Bold', 9)
        canvas.drawString(50, height - 139, 'REFERENCE ONLY  /  No fit, manufacturing or flight acceptance')

        draw_view(canvas, shape, (55, height - 335, 230, 150),
                  lambda x,y,z: ((x-y)*math.sqrt(3)/2, (x+y)*.5+z), 'Nominal STEP wireframe - all edges shown')
        for i, (label, proj) in enumerate([
            ('XY', lambda x,y,z: (x,y)), ('XZ', lambda x,y,z: (x,z)), ('YZ', lambda x,y,z: (y,z))]):
            draw_view(canvas, shape, (335, height - 215 - i*70, 185, 45), proj, label)
        canvas.setFillColor(colors.HexColor('#53616D'))
        canvas.setFont('ReviewSans', 9)
        canvas.drawString(38, height - 386, 'Views are independently fitted to the page, not to scale. No assembly placement is implied.')

        top = height - 405
        columns = [48, 205, 315, 425]
        canvas.setFillColor(colors.HexColor('#153348'))
        canvas.setFont('ReviewSans-Bold', 10)
        for x, text in zip(columns, ['Reference case', 'X (mm)', 'Y (mm)', 'Z (mm)']):
            canvas.drawString(x, top, text)
        canvas.setFont('ReviewSans', 11)
        for i, model in enumerate(models):
            y = top - 28 * (i+1)
            if i % 2 == 0:
                canvas.setFillColor(colors.white)
                canvas.rect(38, y - 8, width - 76, 25, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor('#153348'))
            variant = ('height low' if model['name'].endswith('height_low') else
                       'height high' if model['name'].endswith('height_high') else model['name'].split('_')[-1])
            canvas.drawString(columns[0], y, variant)
            for x, value in zip(columns[1:], model['dimensions_mm']):
                canvas.drawString(x, y, f'{value:.2f}')
        canvas.setFont('ReviewSans', 9)
        canvas.drawString(38, top - 112, 'XYZ follows the input registry. The box corner is not a sensor axis or board datum.')
        canvas.setFont('ReviewSans-Bold', 10)
        canvas.drawString(38, top - 145, 'Limits of this reference')
        canvas.setFont('ReviewSans', 10)
        for i, line in enumerate(caveats):
            canvas.drawString(38, top - 166 - i * 17, '- ' + line)

        canvas.setStrokeColor(colors.HexColor('#CED5DB'))
        canvas.line(38, 116, width - 38, 116)
        canvas.setFont('ReviewSans-Bold', 9)
        canvas.drawString(38, 96, 'Reviewed manufacturer source')
        canvas.setFont('ReviewSans', 9)
        canvas.drawString(38, 80, source)
        canvas.setFillColor(colors.HexColor('#216FA0'))
        canvas.drawString(38, 64, 'Open original manufacturer PDF')
        canvas.linkURL(url, (38, 61, 230, 76), relative=0, thickness=0)
        canvas.setFillColor(colors.HexColor('#53616D'))
        canvas.setFont('ReviewSans', 8)
        canvas.drawString(38, 42, 'Receipt SHA-256: ' + receipt['receipt_sha256'][:24] + '...  |  Geometry-only verification')
        canvas.showPage()
    canvas.save()
    after = [verifier.verify(ra02_dir, 'ra02'), verifier.verify(sensor_dir, 'sensors')]
    if before != after:
        raise ra02.ReferenceError('references changed while drawing review PDF')
    return stream.getvalue()


def create_review(output: Path, ra02_dir: Path, sensor_dir: Path) -> Path:
    # A PDF inside an exact-inventory package would invalidate that package
    # immediately after its final verification. Resolve aliases before any write.
    destination = output.resolve()
    if any(destination.is_relative_to(package.resolve()) for package in (ra02_dir, sensor_dir)):
        raise ra02.ReferenceError('PDF output must be outside both reference packages')
    if destination.exists():
        raise FileExistsError('existing PDF is not overwritten')
    data = render_review(ra02_dir, sensor_dir)
    # Use this same canonical path for writes: a lexical path containing an
    # absent directory followed by '..' could otherwise create that directory
    # inside an input package even when its final destination is outside.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as file:
        file.write(data)
    return destination


def verify_review(pdf: Path, ra02_dir: Path, sensor_dir: Path) -> dict:
    """Check delivered PDF bytes, not only a separate regenerated preview.

    This is exact reproduction with the pinned renderer, not PDF authentication
    or a claim about arbitrary viewers. The existing PDF is never overwritten.
    """
    before = verifier.read_file(pdf)
    expected = render_review(ra02_dir, sensor_dir)
    if before != expected:
        raise ra02.ReferenceError('delivered PDF differs from the verified reference render')
    if verifier.read_file(pdf) != before:
        raise ra02.ReferenceError('delivered PDF changed during verification')
    return {'status': 'PASS_REFERENCE_REVIEW_REPRODUCTION_ONLY',
            'pdf_sha256': ra02.sha256(before), 'bytes': len(before),
            'manufacturing_release': False, 'physical_identity': 'UNVERIFIED',
            'limitation': 'Exact bytes against this trusted source and pinned renderer only; not authentication, fit or hardware acceptance.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ra02', type=Path, required=True)
    p.add_argument('--sensors', type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path, help='new PDF outside both input packages')
    mode.add_argument('--check', type=Path, help='read-only exact reproduction check of an existing PDF')
    args = p.parse_args()
    try:
        if args.check is not None:
            print(json.dumps(verify_review(args.check, args.ra02, args.sensors), indent=2))
        else:
            print(create_review(args.output, args.ra02, args.sensors))
    except Exception as exc:
        print('FAIL: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
