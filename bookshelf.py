import re
import os
import time
import requests
import faker
import logging
import pelican.plugins.signals
from lxml import etree

logger = logging.getLogger(__name__)
BOOKSHELF_KEY = "BOOKSHELF"
DEFAULT_BOOKSHELF = {"INFOS": ["出版年", "页数", "定价", "ISBN"],
                     "SAVE_TO_MD": False,
                     "WAIT_TIME": 2}


def init_config(pelican_object):
    global BOOKSHELF_SETTING
    BOOKSHELF_SETTING = pelican_object.settings.get(BOOKSHELF_KEY, DEFAULT_BOOKSHELF)


def parse_str(string):
    name, url = string.strip("{}").split()[1:]
    return name, url


def get_page(url):
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


def parse_page(html):
    meta = {}
    selector = etree.HTML(html)
    get_cover(meta, selector)
    get_author(meta, selector)
    get_press(meta, selector)

    if "丛书" in BOOKSHELF_SETTING["INFOS"]:
        get_series(meta, selector)

    tags = ["出版年", "页数", "定价", "装帧", "ISBN"]
    for tag in BOOKSHELF_SETTING["INFOS"]:
        if tag not in tags:
            logger.critical(f"There is not {tag} info in the website, please check settings.")
            raise ValueError(f"网页没有所指定的{tag}信息！")
        else:
            get_info_of(tag, meta, selector)

    return meta


def get_cover(meta, selector):
    regex = '//img[@rel="v:photo"]/@src'
    match = selector.xpath(regex)
    if match:
        meta["cover"] = str(match[0])
    else:
        meta["cover"] = ""
    return meta


def get_author(meta, selector):
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
        meta["作者"] = author
    else:
        meta["作者"] = "暂无"

    return meta


def get_press(meta, selector):
    regex = '//div[@id="info"]/child::span[contains(text(), "出版社")]/following-sibling::*[1]/text()'
    match = selector.xpath(regex)
    if match:
        meta["出版社"] = str(match[0])
    else:
        meta["出版社"] = "暂无"
    return meta


def get_series(meta, selector):
    regex = '//div[@id="info"]/child::span[contains(text(), "丛书")]/following-sibling::*[1]/text()'
    match = selector.xpath(regex)
    if match:
        meta["丛书"] = str(match[0])
    else:
        meta["丛书"] = "暂无"
    return meta


def get_info_of(tag, meta, selector):
    # 获取出版信息中的 text 标签
    regex = f'//text()[preceding-sibling::span[1][contains(text(),"{tag}")]][following-sibling::br[1]]'
    match = selector.xpath(regex)
    if match:
        meta[f"{tag}"] = str(match[0]).strip()
    else:
        meta[f"{tag}"] = "暂无"
    return meta


def generate_bookshelf(meta, book_name, url):
    bookshelf = etree.Element("div", {"class": "bookshelf"})
    book = etree.SubElement(bookshelf, "div", {"class": "book"})
    etree.SubElement(book, "img", {"src": meta["cover"], "referrerPolicy": "no-referrer"})
    del meta["cover"]
    infos = etree.SubElement(book, "div", {"class": "infos"})
    title = etree.SubElement(infos, "a", {"class": "title", "href": url})
    title.text = book_name
    for key, value in meta.items():
        info = etree.SubElement(infos, "div", {"class": key})
        info.text = "：".join([key, value])
    bookshelf = etree.tostring(bookshelf, encoding='utf-8', pretty_print=True).decode()
    return bookshelf


def replace(path, context=None):
    suffix = os.path.splitext(str(path))[-1]
    if suffix != ".html" and suffix != ".md":
        pass
    elif suffix == ".md" and not BOOKSHELF_SETTING["SAVE_TO_MD"]:
        pass
    else:
        pattern = r"\{GET\s\S+\s[a-zA-z]+://[^\s]*\}"
        with open(str(path), 'r', encoding="utf-8") as f:
            s = f.read()
            search_target = re.search(pattern, s)
            while search_target is not None:
                _, book, url = search_target.group().strip("{}").split()
                html = get_page(url)
                # anti spider, but generation will be lagged.
                time.sleep(BOOKSHELF_SETTING["WAIT_TIME"])
                if html is not None:
                    meta = parse_page(html)
                    s = s.replace(search_target.group(), generate_bookshelf(meta, book, url))
                    search_target = re.search(pattern, s)
                else:
                    search_target = re.search(pattern, s)
                    continue
        with open(str(path), 'w', encoding="utf-8") as f:
            f.write(s)


def register():
    pelican.signals.initialized.connect(init_config)
    # 写入 Markdown，避免爬虫次数过多
    pelican.signals.content_object_init.connect(replace)
    # 写入到输出的 html，不修改 Markdown
    pelican.signals.content_written.connect(replace)
