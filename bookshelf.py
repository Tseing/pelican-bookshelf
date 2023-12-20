import logging
import os
import re
import time
from typing import Optional

import faker
import pelican.plugins.signals
import requests
import yaml
from lxml import etree


logger = logging.getLogger(__name__)
BOOKSHELF_KEY = "BOOKSHELF"
DEFAULT_BOOKSHELF = {
    "FIELDS": ["year", "page", "price", "ISBN"],
    "WAIT_TIME": 2,
    "UPDATE": False,
}


def init_config(pelican_object):
    global BOOKSHELF_SETTING
    BOOKSHELF_SETTING = pelican_object.settings.get(BOOKSHELF_KEY, DEFAULT_BOOKSHELF)

    global FIELD_MAP
    FIELD_MAP = {
        "year": "出版年",
        "page": "页数",
        "price": "定价",
        "binding": "装帧",
        "ISBN": "ISBN",
        "rank": "评分",
    }

    global SUPPORTED_FIELDS
    SUPPORTED_FIELDS = ["year", "page", "price", "series", "binding", "ISBN"]
    # TODO: rank

    for field in BOOKSHELF_SETTING["FIELDS"]:
        if field not in SUPPORTED_FIELDS:
            logger.critical(f"Pelican bookshelf does not support {field}. Please check settings.")
            raise RuntimeError(f"Not support {field}")

    output_path = pelican_object.settings.get("OUTPUT_PATH", "output/")
    bookshelf_path = os.path.join(output_path, "bookshelf.yaml")
    bookshelf_path = BOOKSHELF_SETTING.get("BOOKSHELF_PATH", bookshelf_path)
    BOOKSHELF_SETTING.update({"BOOKSHELF_PATH": bookshelf_path})

    if BOOKSHELF_SETTING.get("UPDATE", False):
        update_bookshelf()

    try:
        global bookshelf
        bookshelf = yaml.load(open(bookshelf_path, "r", encoding="utf-8"), yaml.FullLoader)
    except FileNotFoundError:
        bookshelf = {}


# TODO: update information in yaml, such as rank
def update_bookshelf() -> None:
    """update all information of items in bookshelf.yaml"""
    ...


def write_bookshelf() -> None:
    if bookshelf is None or bookshelf == {}:
        pass
    else:
        yaml.dump(
            bookshelf,
            open(BOOKSHELF_SETTING["BOOKSHELF_PATH"], "w+", encoding="utf-8"),
            sort_keys=True,
            allow_unicode=True,
        )


def parse_url2id(url: str) -> str:
    return str(int(url.strip("/").split("/")[-1]))


def parse_id2url(id: str) -> str:
    try:
        id = int(id)
    except:
        raise RuntimeError(
            f"ID `{id}` is not a valid douban ID. Cannot be transformer into URL."
            f"Or do you forget to add this ID into `bookshelf.yaml`?"
        )
    return "".join(["https://book.douban.com/subject/", str(id), "/"])


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


def parse_page(html: str, url: str) -> dict:
    infos = {}
    selector = etree.HTML(html)
    get_name(infos, selector)
    get_cover(infos, selector)
    get_author(infos, selector)
    get_press(infos, selector)
    infos.update({"url": url})

    if "series" in BOOKSHELF_SETTING["FIELDS"]:
        get_series(infos, selector)

    for tag in BOOKSHELF_SETTING["FIELDS"]:
        if tag == "series":
            continue
        else:
            get_info_of(tag, infos, selector)

    return infos


def get_name(infos: dict, selector):
    regex = "//h1/span//text()"
    match = selector.xpath(regex)
    if match:
        infos["name"] = str(match[0])
    else:
        infos["name"] = "暂无"
    return infos


# TODO: get rank
def get_rank():
    ...


def get_cover(infos: dict, selector):
    regex = '//img[@rel="v:photo"]/@src'
    match = selector.xpath(regex)
    if match:
        infos["cover"] = str(match[0])
    else:
        infos["cover"] = ""
    return infos


def get_author(infos: dict, selector):
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
        author = "".join(authors)
        infos["author"] = author
    else:
        infos["author"] = "暂无"

    return infos


def get_press(infos: dict, selector):
    regex = '//div[@id="info"]/child::span[contains(text(), "出版社")]/following-sibling::*[1]/text()'
    match = selector.xpath(regex)
    if match:
        infos["press"] = str(match[0])
    else:
        infos["press"] = "暂无"
    return infos


def get_series(infos: dict, selector):
    regex = '//div[@id="info"]/child::span[contains(text(), "丛书")]/following-sibling::*[1]/text()'
    match = selector.xpath(regex)
    if match:
        infos["series"] = str(match[0])
    else:
        infos["series"] = "暂无"
    return infos


def get_info_of(field, infos, selector):
    # 获取出版信息中的 text 标签
    zh_field = FIELD_MAP[field]
    regex = f'//text()[preceding-sibling::span[1][contains(text(),"{zh_field}")]][following-sibling::br[1]]'
    match = selector.xpath(regex)
    if match:
        infos[f"{field}"] = str(match[0]).strip()
    else:
        infos[f"{field}"] = "暂无"
    return infos


def fetch_local_book(bookshelf: dict, id: str) -> dict:
    return bookshelf[id]


def fetch_remote_book(url: str) -> Optional[dict]:
    """Fetch all fields from douban book web so keep it when get response."""
    id = parse_url2id(url)
    global bookshelf
    html = get_page(url)
    time.sleep(BOOKSHELF_SETTING["WAIT_TIME"])
    if html is not None:
        infos = parse_page(html, url)
        bookshelf.update({id: infos})
        return infos
    else:
        return None


def check_url_info(infos: dict) -> None:
    assert "url" in infos, f"The item has no key named 'url': \n {infos}"


def check_specified_fields(infos: dict, fields: list) -> Optional[dict]:
    default_fields = ["name", "cover"]
    fields = default_fields + fields
    try:
        assert all(field in infos for field in fields)
        return infos
    except AssertionError:
        url = infos["url"]
        if url is not None:
            return fetch_remote_book()
        else:
            return None


def generate_book_card(infos: dict, fields: list) -> Optional[str]:
    check_url_info(infos)
    infos = check_specified_fields(infos, fields)
    if infos is None:
        return None
    else:
        book_card = etree.Element("div", {"class": "bookshelf"})
        book = etree.SubElement(book_card, "div", {"class": "book"})
        etree.SubElement(book, "img", {"src": infos["cover"], "referrerPolicy": "no-referrer"})
        infos_block = etree.SubElement(book, "div", {"class": "infos"})
        title = etree.SubElement(infos_block, "a", {"class": "title", "href": infos["url"]})
        title.text = infos["name"]

        for key in fields:
            info = etree.SubElement(infos_block, "div", {"class": key})
            info.text = "：".join([FIELD_MAP[key], infos[key]])

        book_card = etree.tostring(book_card, encoding="utf-8", pretty_print=True).decode()
        return book_card


def search_replace_str(s: str, pattern: str, file_name: str) -> str:
    results = re.search(pattern, s)
    while results is not None:
        matched_str = results.group()
        id, _ = matched_str.strip("<p>[GETBOOK://]</p>").split(".")
        try:
            assert bookshelf is not None and bookshelf != {}
            infos = fetch_local_book(bookshelf, id)
        except (AssertionError, KeyError):
            infos = fetch_remote_book(parse_id2url(id))

        content = generate_book_card(infos, BOOKSHELF_SETTING["FIELDS"])
        if content is not None:
            s = s.replace(matched_str, content)
            results = re.search(pattern, s)
        else:
            logger.warning(
                f"`{matched_str}` in file `{file_name}` was not been replaced. "
                f"Please check information of id `{id}` in `{BOOKSHELF_SETTING['BOOKSHELF_PATH']}`."
            )
            break
    return s


def replace(path: str, context=None) -> None:
    suffix = os.path.splitext(path)[-1]
    if suffix != ".html":
        pass
    else:
        # replace <p>[GETBOOK://id.book_name]</p>
        pattern = r"<p>\[GETBOOK://[a-zA-z0-9]+?\..+?\]</p>"
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        with open(path, "w", encoding="utf-8") as f:
            f.write(search_replace_str(text, pattern, path))

# TODO: reactor func into class

def register():
    pelican.signals.initialized.connect(init_config)
    pelican.signals.content_written.connect(replace)
    pelican.signals.finalized.connect(write_bookshelf)
