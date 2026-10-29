import unittest
from app import account_map, validate_draft

class ValidationTests(unittest.TestCase):
    def test_account_map(self):
        self.assertEqual(account_map("instagram=acc1;twitter=acc2"),
                         {"instagram":"acc1","twitter":"acc2"})
    def test_rejects_unknown_platform(self):
        with self.assertRaises(ValueError): account_map("myspace=acc1")
    def test_requires_caption(self):
        with self.assertRaises(ValueError): validate_draft({"content":" ","platforms":["instagram"]})
    def test_requires_platform(self):
        with self.assertRaises(ValueError): validate_draft({"content":"Hello","platforms":[]})
    def test_requires_https_media(self):
        with self.assertRaises(ValueError):
            validate_draft({"content":"Hello","platforms":["instagram"],"media_url":"http://example.org/a.jpg"})
    def test_valid_text_draft(self):
        result = validate_draft({"content":"Hello","platforms":["instagram","twitter"]})
        self.assertEqual(result,("Hello",["instagram","twitter"],None,None))

if __name__ == "__main__":
    unittest.main()
