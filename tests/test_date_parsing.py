from unittest import TestCase
from popthings import compute_date


class TestDateParsing(TestCase):
    def test_iso_date(self):
        """ ISO formatted dates: YYYY-MM-DD."""
        date = "2018-12-31"
        self.assertEqual(date, compute_date(date))

    def test_iso_date_with_space(self):
        date = " 2018-12-31 "
        self.assertEqual("2018-12-31", compute_date(date))

    def test_invalid_date(self):
        self.assertEqual("31/12/2018", compute_date("31/12/2018"))

    def test_iso_date_with_positive_offset(self):
        date = "2018-12-30 + 1"
        self.assertEqual("2018-12-31", compute_date(date))

    def test_iso_date_with_negative_offset(self):
        date = "2018-12-30 - 1"
        self.assertEqual("2018-12-29", compute_date(date))

    def test_iso_date_with_negative_large_offset(self):
        date = "2018-12-30 - 10"
        self.assertEqual("2018-12-20", compute_date(date))

    def test_other_values(self):
        for word in ('today', 'tomorrow', 'evening', 'anytime', 'someday', 'next month'):
            with self.subTest(word=word):
                self.assertEqual(word, compute_date(word))
