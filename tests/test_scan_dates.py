import unittest
from datetime import date

from scripts.scan_weekends import add_months, is_visited, is_visa_free, weekend_pairs


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



class DestinationFilterTests(unittest.TestCase):
    def test_charleroi_is_excluded_as_brussels_alternative(self):
        self.assertTrue(is_visited({"name": "Charleroi", "country": "Belgium"}))
        self.assertTrue(is_visited({
            "name": "Brussels South",
            "destination_airport": {"code": "CRL"},
        }))

    def test_visited_names_are_normalized(self):
        self.assertTrue(is_visited({"name": "San Sebastián"}))
        self.assertTrue(is_visited({"name": "Dambach-la-Ville"}))

    def test_eu_schengen_and_visa_free_europe_are_allowed(self):
        for country in ("Belgium", "Cipro", "Switzerland", "Albania",
                        "Bosnia and Herzegovina", "Georgia", "Armenia"):
            with self.subTest(country=country):
                self.assertTrue(is_visa_free({"country": country}))

    def test_ireland_is_excluded_because_it_requires_a_visa(self):
        self.assertFalse(is_visa_free({"country": "Ireland"}))


if __name__ == '__main__':
    unittest.main()
