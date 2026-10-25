"""Fast offline tests for the units bridge (#11): Metzger re-digitization, the coupling toy and its limiting cases."""
import importlib.util
import json
import math
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('coupling_toy', HERE / 'coupling_toy.py')
toy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(toy)
FIG2 = json.loads((HERE / 'metzger/fig2_digitized.json').read_text())
BY_EYE_MAX = [6.9, 41, 219, 434, 1440, 6600, 23500]       # model/docking/metzger.py MAX_T
BY_EYE_RED = [6.9, 20, 71, 83, 60, 192, 154]              # model/docking/metzger.py RED_T


def fit(t, y):
    lt = [math.log(v) for v in y]
    mt, ml = sum(t) / len(t), sum(lt) / len(lt)
    return sum((a - mt) * (b - ml) for a, b in zip(t, lt)) / sum((a - mt) ** 2 for a in t)


class MetzgerRecheck(unittest.TestCase):
    def test_axis_calibration_reproduces_values(self):
        ax = FIG2['axis']
        bottom = ax['gridline_rows'][-1]
        for case in ('max', 'reduced'):
            for row, m in zip(FIG2[case]['centre_rows'], FIG2[case]['mass_t']):
                self.assertAlmostEqual(math.log10(m), (bottom - row) / ax['px_per_decade'], places=9)

    def test_gridlines_evenly_spaced(self):
        rows = FIG2['axis']['gridline_rows']
        gaps = [b - a for a, b in zip(rows, rows[1:])]
        self.assertLessEqual(max(gaps) - min(gaps), 1)

    def test_reduced_end_point_matches_abstract_within_two_pixels(self):
        tol = 10 ** (2 / FIG2['axis']['px_per_decade']) - 1
        self.assertLess(abs(FIG2['reduced']['mass_t'][-1] / 156 - 1), tol)

    def test_by_eye_values_agree_within_five_percent(self):
        for new, old in zip(FIG2['max']['mass_t'] + FIG2['reduced']['mass_t'], BY_EYE_MAX + BY_EYE_RED):
            self.assertLess(abs(new / old - 1), 0.055)

    def test_rates_unchanged_by_redigitization(self):
        t = FIG2['years']
        new, old = fit(t, FIG2['max']['mass_t']), fit(t, BY_EYE_MAX)
        self.assertAlmostEqual(new, 0.6474, places=3)
        self.assertLess(abs(new - old), 0.01)
        # g = 0.35 is about half of the source's max-rate fit, not equal to it; 2-year spacing is not the doubling time
        self.assertTrue(0.45 < 0.35 / new < 0.6)
        self.assertNotAlmostEqual(math.log(2) / new, 2.0, places=0)


class CouplingToy(unittest.TestCase):
    def test_reduces_to_unchanged_solver_law(self):
        T = 40
        r = toy.run(T=T)
        base = toy.baseline_path(0.35, 1e-3, T, Kmax=math.inf)
        self.assertLess(max(abs(a / b - 1) for a, b in zip(r['Y'], base)), 1e-9)
        self.assertIn(toy.GROWTH_LAW, toy.SOLVER.read_text())

    def test_baseline_matches_docking_iteration(self):
        path = toy.baseline_path(0.35, 1e-3, 20, Kmax=1e9, A_close=0.1, chi_pre=0.15)
        a = 1e-3
        for _ in range(20):
            a *= math.exp(0.35 * (1.0 if a >= 0.1 else 0.15) * (1 - a / 1e9))
        self.assertAlmostEqual(path[-1], a, places=15)

    def test_faster_coding_does_not_raise_growth_when_energy_binds(self):
        paths = [toy.run(lam=lam, r_E=0.10)['Y'] for lam in (2, 8, 64, 1e6)]
        for p in paths[1:]:
            self.assertEqual(p, paths[0])
        self.assertAlmostEqual(math.log(paths[0][-1] / paths[0][-2]), math.log(1.10), places=9)

    def test_faster_coding_does_not_raise_growth_when_chips_bind(self):
        paths = [toy.run(lam=lam, Q_imp=1e-4)['Y'] for lam in (8, 64, 1e6)]
        for p in paths[1:]:
            self.assertEqual(p, paths[0])

    def test_faster_coding_does_not_raise_output_beyond_a_resource_cap(self):
        for lam in (8, 1e6):
            r = toy.run(lam=lam, E_max=0.02)
            self.assertLessEqual(max(r['Y']), 0.02 * (1 + 1e-9))

    def test_coding_matters_only_while_design_binds(self):
        rates = [toy.run(lam=lam, T=20)['rates'][-1] for lam in (0.5, 1, 2, 4, 8, 16)]
        self.assertTrue(all(a < b for a, b in zip(rates[:4], rates[1:5])))
        self.assertAlmostEqual(rates[-1], 0.35, places=9)
        self.assertAlmostEqual(rates[-2], 0.35, places=9)

    def test_chip_quota_is_not_a_constant_multiplier(self):
        r = toy.run(lam=64, Q_imp=1e-4)['rates']
        self.assertGreater(r[0], 2 * r[-1])
        crude = toy.run(lam=64, Q_imp=1e-4, eta_crude=0.1, K_crude=1.6e-6)['rates']
        self.assertGreater(crude[-1], r[-1])

    def test_committed_results_reproduce(self):
        old = json.loads(toy.OUT_JSON.read_text())
        new = json.loads(json.dumps(toy.compute(), sort_keys=True))
        self.assertEqual(toy._drift(old, new), [])
        self.assertEqual(toy.OUT_MD.read_text(), toy.markdown(toy.compute()))


if __name__ == '__main__':
    unittest.main()
