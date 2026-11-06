# Review and verify the actual reference delivery

The package now includes a [three-page PDF](examples/electronics-reference-review.pdf)
with one page per named reference: Ra-02 V1.1, MPU-9250 and BMP280. Every nominal
wireframe and projection is built from edges of an actually re-imported STEP.
Tables list all nine source-bound size cases. There is no guessed PCB, mounting
feature, sensor orientation, installation position or mechanical assembly.
Views are independently fitted to the page and are **not to scale**.

## Check the delivered files, not just their old receipt

From a trusted, reviewed copy of this source snapshot:

```sh
python -m pip install -r cad_reference/requirements.txt
python cad_reference/verify_package.py --kind ra02 --package cad_reference/examples/ra02-20261106
python cad_reference/verify_package.py --kind sensors --package cad_reference/examples/sensors-20261106
```

Success is deliberately named `PASS_DELIVERED_GEOMETRY_ONLY`. The checker is
read-only and does not rewrite the package, upgrade an asset or authorize use.
It checks:

- Current reviewed source/manifest/generator digests and the explicit reference
  scope, unknowns and no-release state.
- Exact reference model and file inventory, STEP/SVG size and SHA-256, fixed
  README notices, and no duplicate JSON keys, symlinks or unexpected file paths.
- Actual STEP re-import, every root shape, a single closed solid with no loose
  edges/faces/wires, origin, source-derived dimensions and analytic box volume.
- Agreement between real geometry and recorded geometry statistics; rehashing a
  substituted STEP does not make wrong dimensions pass.
- Receipt, inventory, notices and file checksums remaining unchanged through
  verification.

The checker expects the **matching reviewed source snapshot**. An older receipt
will fail after its generator changes; use its original reviewed Git revision or
regenerate from the newer source. This is intentional, not a fit failure.

## Concrete corrections in this iteration

The previous Ra-02 validator rejected ordinary row changes, but a changed value
and recomputed input row hash could bypass the source review boundary. This was
reproduced with 17 mm changed to 170 mm. Reviewed dimensions, tolerance and full
row digests are now independently pinned; analogous sensor row-metadata guards
are included. A changed note or an added fit/release claim cannot be approved by
simply recalculating the manifest hash. Ra-02 root/binding fields are also strictly
checked, and its existing blocked ESP-01S conflict note remains pinned.

The previous topology check could accept one valid box plus a loose edge inside
its bounds. The stricter checker now rejects such extras. Multiple imported STEP
roots are checked explicitly rather than silently using only the first object.

Regression tests cover these cases, self-consistent tampered STEP hashes, wrong
dimensions/datum/statistics, missing/extra/reordered models, stale source hashes,
changed README notices, forged release claims and files changing during checking.
The existing nine example models were freshly regenerated with unchanged physical
dimensions and updated receipts. CAD_START remains blocked with 19 unmet items.

## Reproduce the visual review

```sh
python cad_reference/make_review_pdf.py \
  --ra02 cad_reference/examples/ra02-20261106 \
  --sensors cad_reference/examples/sensors-20261106 \
  --output /tmp/electronics-reference-review-new.pdf
```

The output file must not already exist. Both input packages are verified before
and after drawing. A mismatched or failed package produces no new PDF. The PDF
is a human-readable navigation aid and carries source links and receipt digest
prefixes; it is not a detailed drawing, certified part, proof of hardware identity,
or manufacturing output. The deterministic PDF layout is checked by automated
tests and rendered-page inspection.

## Trust limits

Hashes provide internal consistency, **not signatures**. This checker cannot
authenticate a checkout or manufacturer, prove that an observed item matches the
named part, or detect an attacker replacing both the trusted checking code and
all its inputs. It is not a sandbox for hostile arbitrary CAD files. SVG checks
verify delivered bytes, not an independent semantic rendering of every SVG.
PDF visuals are regenerated from STEP, not from those stored SVGs.

Box volume remains an envelope calculation, not material volume or mass. No
board dimensions, installation clearances, structural integrity, RF operation,
powered tests, hardware qualification or manufacturing decision are supplied.
