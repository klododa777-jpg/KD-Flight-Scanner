import unittest
from datetime import date

from scripts.scan_weekends import add_months, weekend_pairs


class RollingWeekendWindowTests(unittest.TestCase):
    def test_november_2026_matches_requested_example(self):
        pairs = weekend_pairs(date(2026, 11, 17))
        self.assertEqual(pairs[0], (date(2026, 12, 19), date(2026, 12, 20)))
        self.assertEqual(pairs[-1], (date(2027, 3, 20), date(2027, 3, 21)))
        self.assertEqual(len(pairs), 14)

    def test_window_moves_forward_one_month(self):
        pairs = weekend_pairs(date(2026, 12, 15))
        self.assertEqual(pairs[0], (date(2027, 1, 16), date(2027, 1, 17)))
        self.assertEqual(pairs[-1], (date(2027, 4, 17), date(2027, 4, 18)))

    def test_month_addition_handles_short_months_and_leap_years(self):
        self.assertEqual(add_months(date(2027, 1, 31), 1), date(2027, 2, 28))
        self.assertEqual(add_months(date(2028, 1, 31), 1), date(2028, 2, 29))

    def test_every_result_is_a_saturday_sunday_pair(self):
        pairs = weekend_pairs(date(2026, 11, 17))
        for saturday, sunday in pairs:
            self.assertEqual(saturday.weekday(), 5)
            self.assertEqual((sunday - saturday).days, 1)


if __name__ == '__main__':
    unittest.main()
