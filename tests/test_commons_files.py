import unittest

from src.commons_files import commons_file_page, commons_file_title, is_commons_file_page


class CommonsFileTitleTests(unittest.TestCase):
    def test_accepts_a_file_title(self):
        self.assertEqual('File:Chiyoda.jpg', commons_file_title('File:Chiyoda.jpg'))
        self.assertEqual('File:Chiyoda.jpg', commons_file_title('file:Chiyoda.jpg'))
        self.assertEqual('File:Chiyoda.jpg', commons_file_title('Chiyoda.jpg'))

    def test_accepts_a_commons_file_page_url(self):
        self.assertEqual('File:Chiyoda 写真.jpg', commons_file_title(
            'https://commons.wikimedia.org/wiki/File:Chiyoda_%E5%86%99%E7%9C%9F.jpg'))

    def test_strips_query_and_fragment_from_a_page_url(self):
        self.assertEqual('File:Chiyoda.jpg', commons_file_title(
            'https://commons.wikimedia.org/wiki/File:Chiyoda.jpg?uselang=ja#top'))

    def test_normalizes_whitespace_and_underscores(self):
        self.assertEqual('File:Chiyoda photo.jpg', commons_file_title('File:Chiyoda__photo.jpg'))
        self.assertEqual('File:Chiyoda photo.jpg', commons_file_title('File:  Chiyoda   photo.jpg  '))

    def test_rejects_empty_values(self):
        for value in ('', '   ', 'File:', 'File:   '):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    commons_file_title(value)

    def test_rejects_category_and_other_namespaces(self):
        for value in ('Category:千代田区', 'Special:Upload', 'User:Someone'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    commons_file_title(value)

    def test_rejects_non_commons_hosts(self):
        for value in (
            'https://example.com/wiki/File:Chiyoda.jpg',
            'https://upload.wikimedia.org/wikipedia/commons/a/Chiyoda.jpg',
            'http://commons.wikimedia.org/wiki/File:Chiyoda.jpg',
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    commons_file_title(value)

    def test_rejects_unsupported_title_characters(self):
        for value in ('File:Foo#bar.jpg', 'File:Foo?bar.jpg', 'File:Foo[bar].jpg', 'File:Foo|bar.jpg'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    commons_file_title(value)


class CommonsFilePageTests(unittest.TestCase):
    def test_builds_the_canonical_page_url(self):
        self.assertEqual(
            'https://commons.wikimedia.org/wiki/File:Chiyoda_%E5%86%99%E7%9C%9F.jpg',
            commons_file_page('File:Chiyoda 写真.jpg'))
        self.assertEqual(
            'https://commons.wikimedia.org/wiki/File:Chiyoda.jpg',
            commons_file_page('Chiyoda.jpg'))

    def test_normalizes_a_page_url(self):
        self.assertEqual(
            'https://commons.wikimedia.org/wiki/File:Chiyoda_%E5%86%99%E7%9C%9F.jpg',
            commons_file_page('https://commons.wikimedia.org/wiki/File:Chiyoda_%E5%86%99%E7%9C%9F.jpg?uselang=ja'))

    def test_round_trips_a_title_through_its_page_url(self):
        for title in ('File:Chiyoda 写真.jpg', 'File:Example (1).jpg', 'File:100%.jpg'):
            with self.subTest(title=title):
                self.assertEqual(title, commons_file_title(commons_file_page(title)))


class IsCommonsFilePageTests(unittest.TestCase):
    def test_accepts_a_commons_file_page(self):
        self.assertTrue(is_commons_file_page('https://commons.wikimedia.org/wiki/File:Chiyoda.jpg'))
        self.assertTrue(is_commons_file_page('https://commons.wikimedia.org/wiki/File:Chiyoda_%E5%86%99%E7%9C%9F.jpg'))

    def test_rejects_a_bare_title(self):
        self.assertFalse(is_commons_file_page('File:Chiyoda.jpg'))
        self.assertFalse(is_commons_file_page('Chiyoda.jpg'))

    def test_rejects_query_or_fragment(self):
        self.assertFalse(is_commons_file_page('https://commons.wikimedia.org/wiki/File:Chiyoda.jpg?uselang=ja'))
        self.assertFalse(is_commons_file_page('https://commons.wikimedia.org/wiki/File:Chiyoda.jpg#top'))

    def test_rejects_whitespace_in_the_url(self):
        self.assertFalse(is_commons_file_page('https://commons.wikimedia.org/wiki/File:Chiyoda Ward.jpg'))

    def test_rejects_non_file_pages_and_hosts(self):
        for value in (
            'https://commons.wikimedia.org/wiki/Category:千代田区',
            'https://commons.wikimedia.org/wiki/Special:Upload',
            'https://example.com/wiki/File:Chiyoda.jpg',
            'https://upload.wikimedia.org/wikipedia/commons/a/Chiyoda.jpg',
            'http://commons.wikimedia.org/wiki/File:Chiyoda.jpg',
        ):
            with self.subTest(value=value):
                self.assertFalse(is_commons_file_page(value))


if __name__ == '__main__':
    unittest.main()
