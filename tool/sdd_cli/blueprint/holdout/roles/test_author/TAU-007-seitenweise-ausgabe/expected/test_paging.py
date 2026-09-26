import unittest

from listing.paging import paginate

# Prüft SPEC-0061 FR-01, FR-02, FR-03.
ITEMS = list(range(1, 46))  # 45 Einträge


class PaginateTest(unittest.TestCase):
    def test_fr01_first_and_middle_page(self):
        p = paginate(ITEMS, 1, 10)
        self.assertEqual(p.items, list(range(1, 11)))
        p = paginate(ITEMS, 2, 10)
        self.assertEqual(p.items, list(range(11, 21)))
        self.assertEqual((p.page, p.per_page, p.total_items), (2, 10, 45))

    def test_fr01_total_pages_rounds_up(self):
        self.assertEqual(paginate(ITEMS, 1, 10).total_pages, 5)
        self.assertEqual(paginate(ITEMS, 1, 15).total_pages, 3)
        self.assertEqual(paginate(ITEMS, 1, 45).total_pages, 1)

    def test_fr01_last_partial_page(self):
        self.assertEqual(paginate(ITEMS, 5, 10).items, [41, 42, 43, 44, 45])

    def test_fr01_empty_list_has_one_page(self):
        p = paginate([], 1, 20)
        self.assertEqual((p.items, p.total_items, p.total_pages, p.has_next), ([], 0, 1, False))

    def test_fr01_defaults(self):
        p = paginate(ITEMS)
        self.assertEqual((p.page, p.per_page, len(p.items)), (1, 20, 20))

    def test_fr02_has_next(self):
        self.assertTrue(paginate(ITEMS, 4, 10).has_next)
        self.assertFalse(paginate(ITEMS, 5, 10).has_next)
        self.assertFalse(paginate(ITEMS, 3, 15).has_next)

    def test_fr02_page_beyond_last(self):
        p = paginate(ITEMS, 9, 10)
        self.assertEqual((p.items, p.has_next, p.total_pages), ([], False, 5))

    def test_fr03_bounds(self):
        for page, per_page in ((0, 10), (-1, 10), (1, 0), (1, 101)):
            with self.subTest(page=page, per_page=per_page), self.assertRaises(ValueError):
                paginate(ITEMS, page, per_page)
        self.assertEqual(len(paginate(ITEMS, 1, 100).items), 45)
        self.assertEqual(paginate(ITEMS, 1, 1).items, [1])

    def test_fr03_input_unchanged(self):
        daten = [3, 1, 2]
        paginate(daten, 1, 2)
        self.assertEqual(daten, [3, 1, 2])


if __name__ == "__main__":
    unittest.main()
