# 📚 pelican-bookshelf

pelican-bookshelf 是一款用于在 Pelican 博客上获取并展示豆瓣图书信息的插件，也可以在我的[博客页面](https://leonis.cc/sui-sui-nian/2023-02-22-create-pelican-plugin.html)看到更具体的效果。

![screenshot](https://raw.githubusercontent.com/Tseing/pelican-bookshelf/master/screenshot.png)

具体来说，在撰写文章时，在 Markdown 中以**独立一段**写入 `[GETBOOK://<ID>.<图书名称>]`，例如：

```md
context, ……

[GETBOOK://27154094.海子的诗]

……, context
```

生成网页时该字段会被替换为以下结构的 HTML 片段：

```
<div class="bookshelf">
  <div class="book">
    <img src="https://img2.doubanio.com/view/subject/s/public/s29610741.jpg" referrerPolicy="no-referrer"/>
    <div class="infos">
      <a class="title" href="https://book.douban.com/subject/27154094/">海子的诗</a>
      <div class="作者">作者：海子</div>
      <div class="出版社">出版社：江西人民出版社</div>
      <div class="出版年">出版年：2017-10</div>
      <div class="页数">页数：193</div>
      <div class="定价">定价：42.00元</div>
      <div class="ISBN">ISBN：9787210097136</div>
    </div>
  </div>
</div>
```

修改 CSS 文件就可以自定义 bookshelf 样式。

### 豆瓣书籍

将 `<ID>` 指定为豆瓣 ID，插件会自动爬取相关页面并保存信息至 `bookshelf.yaml` 中。豆瓣 ID 可以在豆瓣图书的 URL 中找到，例如这样一条 URL `https://book.douban.com/subject/27154094/`，其 ID 就是 `27154094`。

### 手动添加

由于各种原因爬虫失效时，可能需要**手动添加豆瓣书籍信息**，这时可以在 `bookshelf.yaml` 中手动添加条目，书籍条目的格式为

```yaml
'2715409':
  ISBN: 9787210097136
  author: 海子
  cover: https://img2.doubanio.com/view/subject/s/public/s29610741.jpg
  name: 海子的诗
  page: '194'
  press: 江西人民出版社
  price: 42.00元
  url: https://book.douban.com/subject/27154094/
  year: 2017-10
```

插件同样支持**手动添加非豆瓣来源的图书**，这时候不能使用纯数字的 ID，否则会导致数据的混乱，可以添加字母作为 ID，条目格式与上例相同。


## 依赖

请先在 Python 环境中安装以下依赖：

```
faker==17.0.0
lxml==4.9.2
```

## 安装方法

1. 下载本仓库，将 `pelican-bookshelf` 文件夹放入 Pelican plugins 路径下；
2. 在 `pelicanconf.py` 中的 `PLUGINS` 列表中添加 `'pelican-bookshelf'`；
3. 将 `pelican-bookshelf/bookshelf.css` 移入 `themes/主题/static` 文件夹中；
4. 在 `pelicanconf.py` 中添加 `CSS_OVERRIDE = ['theme/css/bookshelf.css']`。

## 默认设置

插件的默认设置是

```
DEFAULT_BOOKSHELF = {"FIELDS": ["year", "page", "price", "ISBN"],
                     "WAIT_TIME": 2}
```

- 图书标题（name）、封面（cover）、作者（author）、出版社（press）是必须显示的信息。其余需要显示的字段由 `FIELDS` 指定。目前支持的字段包括以下几项：
  - 出版年（year）
  - 页数（page）
  - 价格（price）
  - 丛书（series）
  - 装帧（binding）
  - ISBN
- `WAIT_TIME` 设定了爬虫间歇时间，若爬虫无法获取信息时可以适当增加。

添加设置的方法是在 `pelicanconf.py` 添加例如以下的内容：

```py
BOOKSHELF = {"FIELD": ["year", "page", "price", "ISBN"],
             "WAIT_TIME": 2}
```

## 自定义样式

仓库中提供了默认样式 `bookshelf.css`，修改样式文件从而自定义 bookshelf 的显示效果。

## TODO

该插件还在开发中，Bug 在所难免

- [] 完善 README.md
- [] 用 class 重写主要功能