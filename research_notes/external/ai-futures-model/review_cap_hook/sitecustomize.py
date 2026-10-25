"""Start-up hook for the #49 review/integration cap EXTENSION in Monte Carlo runs.

The upstream batch runner executes every rollout in a freshly *spawned* subprocess, so a
patch made in the parent does not reach the rollouts. aifm_review_ablation.py puts this
directory on PYTHONPATH and sets AIFM_REVIEW_CAP_KAPPA, AIFM_REVIEW_CAP_SRC (the upstream
checkout) and AIFM_REVIEW_CAP_HERE (this replication folder). Python imports
`sitecustomize` at start-up in every process, including the spawned ones, and this file
then applies review_cap at run time. With the variables unset it does nothing.

It fails loudly rather than silently running the unpatched upstream.
"""

import os

_kappa = os.environ.get("AIFM_REVIEW_CAP_KAPPA")
if _kappa:
    import sys

    for _p in (os.environ["AIFM_REVIEW_CAP_SRC"], os.environ["AIFM_REVIEW_CAP_HERE"]):
        if _p not in sys.path:
            sys.path.insert(0, _p)
    import review_cap as _rc

    _rc.install(float(_kappa))  # for the life of the process
    assert _rc.active_kappa() == float(_kappa)
