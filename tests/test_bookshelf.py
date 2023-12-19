import sys
from unittest import mock

sys.path.append("..")
import pytest
import utils

import bookshelf as bf


class TestBookshelf:
    def setup_class(self):
        pelican_settings = {"OUTPUT_PATH": "./output/"}
        pelican_settings[bf.BOOKSHELF_KEY] = bf.DEFAULT_BOOKSHELF

        self.pelican_settings = pelican_settings

    def setup_method(self):
        mock_pelican_obj = mock.Mock()
        mock_pelican_obj.settings = self.pelican_settings
        bf.init_config(mock_pelican_obj)

    @mock.patch("bookshelf.get_page")
    def test_replace(self, mock_get_page: mock.Mock):
        book_page = "./book_page.html"
        article_page = "./article_page.html"
        with open(book_page, "r", encoding="utf-8") as f:
            html = f.read()
        mock_get_page.return_value = html

        bf.replace(article_page)
        utils.render_output(article_page)
