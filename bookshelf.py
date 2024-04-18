import copy
import logging
import os
import re
import time
from typing import Dict, List, Optional, Tuple

import faker
import pelican.plugins.signals
import requests
import yaml
from jinja2 import Template
from lxml import etree

logger = logging.getLogger(__name__)
BOOKSHELF_KEY = "BOOKSHELF"
DEFAULT_BOOKSHELF = {
    "FIELDS": ["pub_year", "pages", "price", "isbn"],
    "WAIT_TIME": 2,
    "UPDATE": False,
}


class Bookshelf:
    def __init__(self) -> None:
        self._SUPPORTED_FIELDS = ["pub_year", "pages", "price", "series", "binding", "isbn"]
        self._BOOKSHELF_SETTING = None
        BASE_PATH = os.path.abspath(__file__)
        with open(os.path.join(BASE_PATH, "template/bookcard.html")) as f:
            self.bookcard = Template(f.read())

    def init_config(self, pelican_object):
        self._BOOKSHELF_SETTING = pelican_object.settings.get(BOOKSHELF_KEY, DEFAULT_BOOKSHELF)

        for field in self._BOOKSHELF_SETTING["FIELDS"]:
            if field not in self._SUPPORTED_FIELDS:
                logger.critical(
                    f"Pelican bookshelf does not support {field}. Please check settings."
                )
                raise RuntimeError(f"Not support {field}")

        bookshelf_path = self._BOOKSHELF_SETTING.get("BOOKSHELF_PATH")

        if bookshelf_path is None:
            output_path = pelican_object.settings.get("OUTPUT_PATH", "output/")
            bookshelf_path = os.path.join(output_path, "bookshelf.yaml")
            self._BOOKSHELF_SETTING.update({"BOOKSHELF_PATH": bookshelf_path})

            if not os.path.exists(bookshelf_path):
                yaml.dump(
                    {},
                    open(bookshelf_path, "w+", encoding="utf-8"),
                )

        elif self._BOOKSHELF_SETTING.get("UPDATE", False):
            self.update_bookshelf()

        self.bookshelf = yaml.load(open(bookshelf_path, "r", encoding="utf-8"), yaml.FullLoader)
        self.douban_parser = DoubanParser(
            self._BOOKSHELF_SETTING["FIELDS"], self._BOOKSHELF_SETTING["WAIT_TIME"]
        )

    # TODO: update information in yaml, such as rank
    def update_bookshelf(self) -> None:
        """update all information of items in bookshelf.yaml"""
        ...

    def write_bookshelf(self) -> None:
        if self.bookshelf:
            yaml.dump(
                self.bookshelf,
                open(self._BOOKSHELF_SETTING["BOOKSHELF_PATH"], "w+", encoding="utf-8"),
                sort_keys=True,
                allow_unicode=True,
            )

    # Generate book card with Jinja
    def generate_book_card(self, infos: dict) -> Optional[str]:
        infos = self.douban_parser.check_specified_fields(infos)
        if infos is None:
            return None
        else:
            return self.bookcard.render(book=infos, order=self._BOOKSHELF_SETTING["FIELDS"])

    def search_replace_str(self, s: str, pattern: str, file_name: str) -> str:
        results = re.search(pattern, s)
        while results is not None:
            matched_str = results.group()
            params = matched_str.strip("<p>[GETBOOK://]</p>").split(".")
            if 3 == len(params):
                params = dict(zip(["id", "title", "cover"], params))
            elif 2 == len(params):
                params = dict(zip(["id", "title"], params))
            else:
                logger.critical(
                    f"Pelican bookshelf cannot parse command '{matched_str}' in '{file_name}'."
                )
                raise RuntimeError(f"Cannot parse right parameters from '{matched_str}'.")

            id_ = params["id"]
            if id_.startswith("douban"):
                infos = self.bookshelf.get(id_, self.douban_parser.fetch_remote_book(id_))
            else:
                assert False, "Only support douban media now."

            infos.update(params)
            content = self.generate_book_card(infos)
            if content is not None:
                s = s.replace(matched_str, content)
                results = re.search(pattern, s)
            else:
                logger.warning(
                    f"'{matched_str}' in file '{file_name}' was not been replaced. "
                    f"Please check information of id `{id_}` in `{self._BOOKSHELF_SETTING['BOOKSHELF_PATH']}`."
                )
                break
        return s

    def replace(self, path: str, context=None) -> None:
        suffix = os.path.splitext(path)[-1]
        if suffix != ".html":
            pass
        else:
            # TODO: support NeoDB
            # replace <p>[GETBOOK://douban<id>.<book_name>(.<image_url>)]</p>
            pattern = r"<p>\[GETBOOK://douban[a-zA-z0-9]+?\..+?\]</p>"
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()

            with open(path, "w", encoding="utf-8") as f:
                f.write(self.search_replace_str(text, pattern, path))


class DoubanParser:
    def __init__(self, custom_fields: List[str], wait_time: float) -> None:
        self._text_label_map = {
            "pub_year": "出版年",
            "pages": "页数",
            "price": "定价",
            "binding": "装帧",
            "isbn": "ISBN",
            "rank": "评分",
        }

        necessary_fields = ["id", "title", "cover", "url"]
        self._custom_fields = custom_fields
        self._all_fields = necessary_fields + custom_fields
        self._wait_time = wait_time

        self.RE_NUMBERS = re.compile(r"\d+\d*")
        self.RE_WHITESPACES = re.compile(r"\s+")

        self._warp_label_func = {label: self.get_info_of for label in self._text_label_map.keys()}
        self._warp_label_func.update(
            {"author": self.get_author, "pub_house": self.get_press, "series": self.get_series}
        )

    def parse_url2id(url: str) -> str:
        return "".join(["douban", str(int(url.strip("/").split("/")[-1]))])

    def parse_id2url(id: str) -> str:
        try:
            # TODO: handle other book origin
            id = int(id.strip("douban"))
        except:
            raise RuntimeError(
                f"ID `{id}` is not a valid douban ID. Cannot be transformer into URL."
                f"Or do you forget to add this ID into `bookshelf.yaml`?"
            )
        return "".join(["https://book.douban.com/subject/", str(id), "/"])

    @staticmethod
    def get_page(url: str) -> Optional[str]:
        fake = faker.Faker()
        headers = {"User-Agent": fake.user_agent()}
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            logger.warning(f"Can't connect to URL: {url}, please try later.")
            return None
        else:
            html = response.text
            logger.info(f"Request response: {response.status_code}.")
            return html

    @staticmethod
    def get_title(selector) -> Optional[str]:
        regex = "//h1/span//text()"
        match = selector.xpath(regex)
        if match:
            return str(match[0])
        else:
            return None

    # TODO: get rank
    def get_rank(): ...

    @staticmethod
    def get_cover(selector) -> Optional[str]:
        regex = '//a[@class="nbg"]/@href'
        match = selector.xpath(regex)
        if match:
            return str(match[0])
        else:
            return None

    @staticmethod
    def get_author(selector) -> List[str]:
        regex = '//div[@id="info"]/span[child::span[@class="pl"][contains(text(), "作者")]]//text()'
        match = selector.xpath(regex)
        authors = []
        for i in match:
            text = str(i).strip()
            if text == "作者" or text == ":" or text == "":
                continue
            else:
                authors.append(text)
        if authors:
            return authors
        else:
            return None

    @staticmethod
    def get_press(selector) -> Optional[str]:
        regex = '//div[@id="info"]/child::span[contains(text(), "出版社")]/following-sibling::*[1]/text()'
        match = selector.xpath(regex)
        if match:
            return str(match[0])
        else:
            return None

    @staticmethod
    def get_series(selector) -> Optional[str]:
        regex = (
            '//div[@id="info"]/child::span[contains(text(), "丛书")]/following-sibling::*[1]/text()'
        )
        match = selector.xpath(regex)
        if match:
            return str(match[0])
        else:
            return None

    def get_info_of(self, field: str, selector) -> Optional[str]:
        # 获取出版信息中的 text 标签
        zh_label = self._text_label_map[field]
        regex = f'//text()[preceding-sibling::span[1][contains(text(),"{zh_label}")]][following-sibling::br[1]]'
        match = selector.xpath(regex)
        if match:
            return str(match[0]).strip()
        else:
            return None

    # def parse_page(self, html: str) -> Dict[str, str]:
    #     infos = {}
    #     fields = copy.deepcopy(self._custom_fields)
    #     selector = etree.HTML(html)

    #     # infos["title"] = self.get_title(selector)
    #     infos["cover"] = self.get_cover(selector)

    #     for field in fields:
    #         if field in self._text_label_map.keys():
    #             infos[field] = self._warp_label_func[field](field, selector)
    #         else:
    #             infos[field] = self._warp_label_func[field](selector)

    #     return infos

    def fetch_remote_book(self, id: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """Fetch all fields from douban book web so keep it when get response."""
        url = self.parse_id2url(id)
        html = self.get_page(url)
        time.sleep(self._wait_time)
        if html is not None:
            infos = self.parse(html)
            infos.update({"url": url})
            return infos
        else:
            return None

    def check_specified_fields(self, infos: dict) -> Optional[dict]:
        try:
            assert all(field in infos for field in self._all_fields)
            return infos
        except AssertionError:
            return self.fetch_remote_book(infos["id"])

    def parse(self, content: str) -> Dict[str, str]:
        isbn_elem = content.xpath("//div[@id='info']//span[text()='ISBN:']/following::text()")
        isbn = isbn_elem[0].strip() if isbn_elem else None

        title_elem = content.xpath("/html/body//h1/span/text()")
        title = title_elem[0].strip() if title_elem else f"Unknown Title {self.id_value}"

        subtitle_elem = content.xpath("//div[@id='info']//span[text()='副标题:']/following::text()")
        subtitle = subtitle_elem[0].strip()[:500] if subtitle_elem else None

        orig_title_elem = content.xpath(
            "//div[@id='info']//span[text()='原作名:']/following::text()"
        )
        orig_title = orig_title_elem[0].strip()[:500] if orig_title_elem else None

        language_elem = content.xpath("//div[@id='info']//span[text()='语言:']/following::text()")
        language = language_elem[0].strip() if language_elem else None

        pub_house_elem = content.xpath(
            "//div[@id='info']//span[text()='出版社:']/following::text()"
        )
        pub_house = pub_house_elem[0].strip() if pub_house_elem else None
        if not pub_house:
            pub_house_elem = content.xpath(
                "//div[@id='info']//span[text()='出版社:']/following-sibling::a/text()"
            )
            pub_house = pub_house_elem[0].strip() if pub_house_elem else None

        pub_date_elem = content.xpath("//div[@id='info']//span[text()='出版年:']/following::text()")
        pub_date = pub_date_elem[0].strip() if pub_date_elem else ""
        year_month_day = self.RE_NUMBERS.findall(pub_date)
        if len(year_month_day) in (2, 3):
            pub_year = int(year_month_day[0])
            pub_month = int(year_month_day[1])
        elif len(year_month_day) == 1:
            pub_year = int(year_month_day[0])
            pub_month = None
        else:
            pub_year = None
            pub_month = None
        if pub_year and pub_month and pub_year < pub_month:
            pub_year, pub_month = pub_month, pub_year
        pub_year = None if pub_year is not None and pub_year not in range(0, 3000) else pub_year
        pub_month = None if pub_month is not None and pub_month not in range(1, 12) else pub_month

        binding_elem = content.xpath("//div[@id='info']//span[text()='装帧:']/following::text()")
        binding = binding_elem[0].strip() if binding_elem else None

        price_elem = content.xpath("//div[@id='info']//span[text()='定价:']/following::text()")
        price = price_elem[0].strip() if price_elem else None

        pages_elem = content.xpath("//div[@id='info']//span[text()='页数:']/following::text()")
        pages = pages_elem[0].strip() if pages_elem else None
        if pages is not None:
            pages = int(RE_NUMBERS.findall(pages)[0]) if RE_NUMBERS.findall(pages) else None
            if pages and (pages > 999999 or pages < 1):
                pages = None

        brief_elem = content.xpath(
            "//h2/span[text()='内容简介']/../following-sibling::div[1]//div[@class='intro'][not(ancestor::span[@class='short'])]/p/text()"
        )
        brief = "\n".join(p.strip() for p in brief_elem) if brief_elem else None

        img_url_elem = content.xpath("//*[@id='mainpic']/a/img/@src")
        img_url = img_url_elem[0].strip() if img_url_elem else None

        # there are two html formats for authors and translators
        authors_elem = content.xpath(
            """//div[@id='info']//span[text()='作者:']/following-sibling::br[1]/
            preceding-sibling::a[preceding-sibling::span[text()='作者:']]/text()"""
        )
        if not authors_elem:
            authors_elem = content.xpath(
                """//div[@id='info']//span[text()=' 作者']/following-sibling::a/text()"""
            )
        if authors_elem:
            authors = []
            for author in authors_elem:
                authors.append(self.RE_WHITESPACES.sub(" ", author.strip())[:200])
        else:
            authors = None

        translators_elem = content.xpath(
            """//div[@id='info']//span[text()='译者:']/following-sibling::br[1]/
            preceding-sibling::a[preceding-sibling::span[text()='译者:']]/text()"""
        )
        if not translators_elem:
            translators_elem = content.xpath(
                """//div[@id='info']//span[text()=' 译者']/following-sibling::a/text()"""
            )
        if translators_elem:
            translators = []
            for translator in translators_elem:
                translators.append(self.RE_WHITESPACES.sub(" ", translator.strip()))
        else:
            translators = None

        cncode_elem = content.xpath("//div[@id='info']//span[text()='统一书号:']/following::text()")
        cubn = cncode_elem[0].strip() if cncode_elem else None

        series_elem = content.xpath(
            "//div[@id='info']//span[text()='丛书:']/following-sibling::a[1]/text()"
        )
        series = series_elem[0].strip() if series_elem else None

        imprint_elem = content.xpath(
            "//div[@id='info']//span[text()='出品方:']/following-sibling::a[1]/text()"
        )
        imprint = imprint_elem[0].strip() if imprint_elem else None

        data = {
            "title": title,
            "subtitle": subtitle,
            "orig_title": orig_title,
            "author": authors,
            "translator": translators,
            "language": language,
            "pub_house": pub_house,
            "pub_year": pub_year,
            "pub_month": pub_month,
            "binding": binding,
            "price": price,
            "pages": pages,
            "isbn": isbn,
            "cubn": cubn,
            "brief": brief,
            "series": series,
            "imprint": imprint,
            "cove": img_url,
        }

        return data


def register():
    bookshelf = Bookshelf()
    pelican.signals.initialized.connect(bookshelf.init_config)
    pelican.signals.content_written.connect(bookshelf.replace)
    pelican.signals.finalized.connect(bookshelf.write_bookshelf)
