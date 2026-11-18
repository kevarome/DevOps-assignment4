"""Validate the extracted artifact that will be deployed to S3."""

import argparse
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from posixpath import normpath
import unittest
from urllib.parse import unquote, urlsplit

from build import PUBLIC_FILES, ROOT


class ResumePage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.links = []
        self.stylesheets = []
        self.viewport = ""
        self.headings = 0
        self.title_text = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        for attribute in ("href", "src"):
            if attribute in attrs:
                self.links.append(attrs[attribute])
        if tag == "link" and "stylesheet" in attrs.get("rel", "").split():
            self.stylesheets.append(attrs.get("href", ""))
        if tag == "meta" and attrs.get("name") == "viewport":
            self.viewport = attrs.get("content", "")
        if tag == "title":
            self.in_title = True
        if tag == "h1":
            self.headings += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title_text.append(data)


class ArtifactTests(unittest.TestCase):
    artifact = ROOT / "dist"

    @classmethod
    def setUpClass(cls):
        cls.page = ResumePage()
        cls.page.feed((cls.artifact / "index.html").read_text(encoding="utf-8"))
        cls.page.close()

    def test_only_public_files_are_packaged(self):
        actual = {
            path.relative_to(self.artifact).as_posix()
            for path in self.artifact.rglob("*")
            if path.is_file()
        }
        self.assertEqual(actual, set(PUBLIC_FILES))

    def test_page_has_title_heading_and_mobile_viewport(self):
        self.assertTrue("".join(self.page.title_text).strip(), "Missing page title")
        self.assertEqual(self.page.headings, 1, "Expected one main heading")
        self.assertIn("width=device-width", self.page.viewport.replace(" ", ""))

    def test_stylesheet_is_linked_and_nonempty(self):
        paths = [normpath(urlsplit(link).path).lstrip("/") for link in self.page.stylesheets]
        self.assertIn("styles.css", paths)
        self.assertTrue((self.artifact / "styles.css").read_text(encoding="utf-8").strip())

    def test_internal_links_and_anchors_resolve(self):
        duplicates = [target for target, count in Counter(self.page.ids).items() if count > 1]
        self.assertEqual(duplicates, [], "Duplicate page IDs")
        for link in self.page.links:
            with self.subTest(link=link):
                self.assertTrue(link, "Empty link or asset URL")
                url = urlsplit(link)
                if url.scheme or url.netloc:
                    continue
                path = normpath(unquote(url.path).lstrip("/") or "index.html")
                self.assertIn(path, PUBLIC_FILES, "Local URL is missing from the artifact")
                if path == "index.html" and url.fragment:
                    self.assertIn(unquote(url.fragment), self.page.ids, "Missing anchor target")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="directory containing the packaged site")
    ArtifactTests.artifact = parser.parse_args().artifact
    unittest.main(argv=["test_site"], verbosity=2)
