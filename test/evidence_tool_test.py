import copy
import datetime as dt
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('evidence_tool', ROOT / 'tools/evidence_tool.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

RECORDS = tool.load_records()
PROTOCOL = tool.load_yaml(tool.PROTOCOL)


def forecast(**kw):
    f = dict(id='FC-TEST', model='toy', target='METR 50% time horizon of the next frontier model (hours)',
             information_cutoff='2026-08-01', issued='2026-08-02', label='retrospective', inputs=['EV-METZGER-2013'],
             horizon='6 months', baselines=['B-FLAT', 'B-LOGLINEAR'], scoring=['S-ABSLOGERR'], resolution=None)
    f.update(kw)
    return f


class EvidenceRecordsTest(unittest.TestCase):
    def setUp(self):
        self.doc = copy.deepcopy(RECORDS)
        self.recs = {r['id']: r for r in self.doc['records']}

    def rejects(self, message, errors):
        self.assertTrue(any(message in e for e in errors), errors)

    def test_committed_records_and_protocol_are_consistent(self):
        self.assertEqual([], tool.validate_records(self.doc))
        self.assertEqual([], tool.validate_protocol(PROTOCOL, self.recs))

    def test_missing_availability_date_is_rejected(self):
        del self.recs['EV-METR-HF-2026']['availability_date']
        self.rejects("'availability_date' is a required property", tool.validate_records(self.doc))

    def test_observation_after_availability_is_rejected(self):
        self.recs['EV-METR-HF-2026']['observation_date'] = {'start': '2026-07', 'end': '2026-09'}
        self.rejects('observed after it became available', tool.validate_records(self.doc))

    def test_observation_needs_an_observation_date(self):
        self.recs['EV-METR-HF-2026']['observation_date'] = 'not_applicable'
        self.rejects('an observation needs an observation_date', tool.validate_records(self.doc))

    def test_secondary_reading_must_say_how_it_was_extracted(self):
        self.recs['EV-METR-HF-2026']['extraction']['method'] = 'quoted'
        self.rejects('reading is read_secondary_only but extraction method is quoted', tool.validate_records(self.doc))

    def test_unknown_dependency_is_rejected(self):
        self.recs['EV-TURNER-2019']['depends_on'] = ['EV-GHOST']
        self.rejects('depends_on unknown record EV-GHOST', tool.validate_records(self.doc))

    def test_partial_dates_are_compared_conservatively(self):
        self.assertEqual((dt.date(2013, 1, 1), dt.date(2013, 12, 31)), tool.date_bounds('2013'))
        self.assertFalse(tool.available_by({'availability_date': '2013'}, '2013-06-01'))
        self.assertTrue(tool.available_by({'availability_date': '2013'}, '2014-01-01'))

    def test_models_fitted_to_the_same_data_are_not_independent(self):
        a, b = copy.deepcopy(self.recs['EV-METZGER-2013']), copy.deepcopy(self.recs['EV-TURNER-2019'])
        recs = {'A': dict(a, id='A', fitted_to=['metr-2025']), 'B': dict(b, id='B', fitted_to=['metr-2025']),
                'C': dict(b, id='C', fitted_to=[], depends_on=['A']), 'D': dict(b, id='D', fitted_to=[])}
        self.assertFalse(tool.independent(recs, 'A', 'B'))
        self.assertFalse(tool.independent(recs, 'A', 'C'))
        self.assertFalse(tool.independent(recs, 'B', 'C'))      # C inherits A's fitting data
        self.assertTrue(tool.independent(recs, 'A', 'D'))


class ProtocolTest(unittest.TestCase):
    def setUp(self):
        self.p = copy.deepcopy(PROTOCOL)
        self.recs = {r['id']: r for r in RECORDS['records']}

    def errors(self, *fs):
        self.p['forecasts'] = list(fs)
        return tool.validate_protocol(self.p, self.recs)

    def test_clean_retrospective_forecast_passes(self):
        self.assertEqual([], self.errors(forecast()))

    def test_input_after_cutoff_is_contamination(self):
        errs = self.errors(forecast(inputs=['EV-METR-HF-2026']))
        self.assertTrue(any('postdates the cutoff 2026-08-01 (contamination)' in e for e in errs), errs)

    def test_locked_forecast_needs_a_commit(self):
        errs = self.errors(forecast(label='locked'))
        self.assertTrue(any('a locked forecast needs lock_commit' in e for e in errs), errs)

    def test_locked_forecast_of_an_observed_outcome_is_retrospective(self):
        f = forecast(label='locked', lock_commit='abc1234', information_cutoff='2026-06-01', issued='2026-06-02',
                     inputs=[], resolution={'record': 'EV-METR-HF-2026', 'vintage': 'blog 2026-08-26'})
        self.assertEqual([], self.errors(f))
        f['issued'] = '2026-07-15'
        errs = self.errors(f)
        self.assertTrue(any('label it retrospective' in e for e in errs), errs)

    def test_unknown_baseline_or_score_is_rejected(self):
        errs = self.errors(forecast(baselines=['B-ORACLE'], scoring=['S-VIBES']))
        self.assertTrue(any('unknown baseline B-ORACLE' in e for e in errs) and any('unknown scoring rule S-VIBES' in e for e in errs))


class ScoringHelpersTest(unittest.TestCase):
    def test_wilson(self):
        lo, hi = tool.wilson(15, 192)
        self.assertAlmostEqual(lo, 0.0479, places=4)
        self.assertAlmostEqual(hi, 0.1249, places=4)

    def test_interval_score(self):
        self.assertEqual(2.0, tool.interval_score(1, 3, 2, 0.2))
        self.assertAlmostEqual(2.0 + 10.0, tool.interval_score(1, 3, 4, 0.2))

    def test_rolling_origins_never_train_on_the_future(self):
        times = [2019, 2020, 2021, 2022, 2023, 2024]
        for c, train, test in tool.rolling_origins(times, [2020, 2022], horizon=1):
            self.assertTrue(all(times[i] <= c for i in train))
            self.assertTrue(all(c < times[i] <= c + 1 for i in test))

    def test_baselines(self):
        times, values = [0, 1, 2], [1.0, 2.0, 4.0]
        self.assertEqual(4.0, tool.flat_forecast(times, values, [0, 1, 2], 3))
        self.assertAlmostEqual(8.0, tool.loglinear_forecast(times, values, [0, 1, 2], 3))
        self.assertAlmostEqual(0.0, tool.abs_log_error(8.0, 8.0))


if __name__ == '__main__':
    unittest.main()
