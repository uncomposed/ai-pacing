## Summary

<!-- What changes and why, in a few sentences. -->

## Issue

<!-- Closes #N  -- only if EVERY Done-when box of that issue is met by this PR.
     Part of #N -- otherwise; then list which Done-when boxes are done and which are not. -->

## Kind of change

- [ ] Spec (`spec/ai-pacing.yaml`, `.idea/`)
- [ ] Model (`research_notes/.../model/`)
- [ ] Tooling (`tools/`, `test/`, `schema/`, `Makefile`, `.github/`)
- [ ] Docs / research notes
- [ ] Rendering (`renderings/`, `examples/renderings/`)

## Validation

<!-- Exact commands run and their result. Include the locale and venv used.
     State CI status, or why a check was not run. -->

```
LANG=C.UTF-8 make check
```

## Evidence status

<!-- Keep these separate. Write "none" where nothing applies; do not leave blank.
     Replicated: reproduces a published model's own outputs (source, version, tolerance).
     Numerically verified: solver agrees with closed forms / identities.
     Empirically validated: compared with observations (cutoffs, baseline, scoring).
     Assumed: taken as given, with where it is recorded. -->

- Replicated:
- Numerically verified:
- Empirically validated:
- Assumed / not yet established:

## Checklist

- [ ] `LANG=C.UTF-8 make check` passes locally
- [ ] Generated views are current (`make generate` run only if the spec or generator changed on purpose)
- [ ] No committed output was regenerated or overwritten to hide a mismatch; changed outputs are explained above
- [ ] New or changed spec nodes are `proposed` only, with IDs from the reserved-ID registry under `spec/`
- [ ] Negative results and failed checks are reported, not dropped
