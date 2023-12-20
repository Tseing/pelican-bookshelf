import os
import sys
from unittest import mock

sys.path.append("..")
import pytest
import yaml

import bookshelf as bs
import utils


@pytest.mark.skip
class TestInitCfg:
    def setup_class(self):
        self.pelican_settings = {"OUTPUT_PATH": "output/"}
        self.mock_pelican_obj = mock.Mock()
        self.mock_pelican_obj.settings = self.pelican_settings

    def teardown_method(self):
        # Delete global variables
        del bs.BOOKSHELF_SETTING
        del bs.bookshelf

    def test_default_config(self):
        bs.init_config(self.mock_pelican_obj)
        assert bs.DEFAULT_BOOKSHELF == bs.BOOKSHELF_SETTING

    def test_custom_config(self):
        custom_config = {
            "FIELDS": ["year", "ISBN"],
            "WAIT_TIME": 5,
            "UPDATE": True,
        }
        self.pelican_settings.update({bs.BOOKSHELF_KEY: custom_config})
        self.mock_pelican_obj.settings = self.pelican_settings
        bs.init_config(self.mock_pelican_obj)

        assert "output/bookshelf.yaml" == bs.BOOKSHELF_SETTING["BOOKSHELF_PATH"]
        assert custom_config == bs.BOOKSHELF_SETTING

        self.pelican_settings[bs.BOOKSHELF_KEY].update({"FIELDS": ["year", "ISBN", "foo"],})
        self.mock_pelican_obj.settings = self.pelican_settings
        with pytest.raises(RuntimeError):
            bs.init_config(self.mock_pelican_obj)

    def test_custom_path(self):
        custom_config = {
            "FIELDS": ["year", "ISBN"],
            "WAIT_TIME": 5,
            "UPDATE": True,
            "BOOKSHELF_PATH": "custom_path/bookshelf.yaml"
        }
        self.pelican_settings.update({bs.BOOKSHELF_KEY: custom_config})
        self.pelican_settings.update({"OUTPUT_PATH": "default_path/"})

        self.mock_pelican_obj.settings = self.pelican_settings
        bs.init_config(self.mock_pelican_obj)
        assert "custom_path/bookshelf.yaml" == bs.BOOKSHELF_SETTING["BOOKSHELF_PATH"]

    def test_load_bookshelf(self):
        config = bs.DEFAULT_BOOKSHELF
        config.update({"BOOKSHELF_PATH": "output/bookshelf.yaml"})
        self.pelican_settings.update({bs.BOOKSHELF_KEY: config})
        self.mock_pelican_obj.settings = self.pelican_settings
        book_info = {
            "1449351": {
                "name": "呐喊",
                "url": "https://book.douban.com/subject/1449351/",
                "cover": "https://img9.doubanio.com/view/subject/l/public/s34099286.jpg",
                "author": "鲁迅"
            }
        }

        yaml.dump(book_info, open("output/bookshelf.yaml", "w+", encoding="utf-8"), sort_keys=True, allow_unicode=True)
        bs.init_config(self.mock_pelican_obj)
        assert book_info == bs.bookshelf
        os.remove("output/bookshelf.yaml")


@pytest.mark.skip
class TestBookshelf:
    def setup_class(self):
        pelican_settings = {"OUTPUT_PATH": "./output/"}
        pelican_settings[bs.BOOKSHELF_KEY] = bs.DEFAULT_BOOKSHELF

        self.pelican_settings = pelican_settings

    def setup_method(self):
        mock_pelican_obj = mock.Mock()
        mock_pelican_obj.settings = self.pelican_settings
        bs.init_config(mock_pelican_obj)

    @pytest.mark.skip
    @mock.patch("bookshelf.get_page")
    def test_replace(self, mock_get_page: mock.Mock):
        book_page = "./book_page.html"
        article_page = "./article_page.html"
        with open(book_page, "r", encoding="utf-8") as f:
            html = f.read()
        mock_get_page.return_value = html

        bs.replace(article_page)
        utils.render_output(article_page)
