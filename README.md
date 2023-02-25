# 📚 pelican-bookshelf

pelican-bookshelf 是一款用于在 Pelican 博客上获取并展示豆瓣图书信息的插件，也可以在我的[博客页面](https://leonis.cc/sui-sui-nian/2023-02-22-create-pelican-plugin.html)看到更具体的效果。

![screenshot]()

具体来说，在撰写文章时，在 Markdown 中写入 `{GET 图书名称 豆瓣URL}`，生成网页时该字段会被替换为类似以下的 HTML 片段：

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

所以可以自己修改 CSS 文件设定你的 bookshelf 样式。

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
4. 在 `pelicanconf.py` 中添加 `CSS_OVERRIDE = ['theme/css/plugins.css', 'theme/css/bookshelf.css']`。

## 默认设置

插件的默认设置是

```
DEFAULT_BOOKSHELF = {"INFOS": ["出版年", "页数", "定价", "ISBN"],
                     "SAVE_TO_MD": False,
                     "WAIT_TIME": 2}
```

- 图书标题、封面、作者、出版社是必须显示的信息，`INFOS` 指定了其他需要从豆瓣图书页面获取的信息（例如丛书、装帧等）。
- `SAVE_TO_MD` 指定是否将 HTML 片段写入 Markdown 文件，如果设置为 `False`，每次生成网页时都会向豆瓣图书发起爬虫，会减慢生成网页的速度。若要设置为 `True`，**请确保已经备份好 Markdown 文件**。
- `WAIT_TIME` 设定了爬虫间歇时间，若爬虫无法获取信息时可以适当增加。

添加设置的方法是在 `pelicanconf.py` 添加例如以下的内容：

```
BOOKSHELF = {"INFOS": ["出版年", "页数", "定价", "ISBN"],
             "SAVE_TO_MD": True,
             "WAIT_TIME": 2}
```

## 目前已知 Bug

若要使用 `pelican -lr` 命令修改并检查网站，务必将 `SAVE_TO_MD` 设置为 `False`。