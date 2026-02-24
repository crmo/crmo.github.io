#!/usr/bin/env python3
"""
Hexo → Hugo 迁移脚本
从旧站 HTML 提取元数据，匹配 MWeb Markdown 原稿，生成 Hugo page bundle。

用法: python3 migrate.py
依赖: pip3 install beautifulsoup4 lxml
"""

import os
import re
import shutil
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

# ============ 配置 ============
HEXO_BACKUP = Path("/tmp/hexo-backup")
MWEB_DOCS = Path("/Users/link/Documents/Mweb/docs")
MWEB_MEDIA = MWEB_DOCS / "media"
HUGO_ROOT = Path("/Users/link/Documents/Code/crmo.github.io")
CONTENT_DIR = HUGO_ROOT / "content" / "post"

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ============ 手动映射：HTML og:title → MWeb 文件中的 H1 标题 ============
# 用于 og:title 和 MWeb 标题不完全匹配的情况
MANUAL_TITLE_MAP = {
    "GCD 解决生产者消费者问题": "用 GCD 实现生产者消费者",
    "应对iOS隐私政策三步曲": "应对苹果隐私政策看我就够了",
    "UIWebView获取详细浏览记录": "UIWebView获取详细浏览记录",
    "Core Animation学习笔记（一）- CALayer": "Core Animation学习笔记（一）- CALayer",
    "Core Animation学习笔记（二）- 图层几何布局": "Core Animation学习笔记（二）- 图层几何布局",
    "Core Animation学习笔记（三）- 视觉效果": "Core Animation学习笔记（三）- 视觉效果",
    "iOS定义长字符串的实用宏": "iOS定义长字符串的实用宏",
    "iOS消息转发小记": "消息转发笔记",
}


def extract_metadata_from_html(html_path: Path) -> dict:
    """从旧站 HTML 页面提取文章元数据。"""
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    meta = {}

    # 标题
    og_title = soup.find("meta", property="og:title")
    meta["title"] = og_title["content"] if og_title else ""

    # 发布日期
    time_tag = soup.find("time", attrs={"datetime": True})
    meta["date"] = time_tag["datetime"] if time_tag else ""

    # 更新时间
    og_updated = soup.find("meta", property="og:updated_time")
    meta["lastmod"] = og_updated["content"] if og_updated else ""

    # 标签
    tags_div = soup.find("div", class_="post-tags")
    if tags_div:
        meta["tags"] = [a.get_text(strip=True).lstrip("# ") for a in tags_div.find_all("a")]
    else:
        meta["tags"] = []

    # 从文件路径提取 slug（中文目录名）和日期
    # 路径格式: /tmp/hexo-backup/2018/07/31/runtime实现私有变量搜索/index.html
    parts = html_path.parts
    try:
        year_idx = next(i for i, p in enumerate(parts) if re.match(r"20\d{2}$", p))
        meta["slug"] = parts[year_idx + 3]  # 中文目录名
        meta["url_date"] = f"{parts[year_idx]}-{parts[year_idx+1]}-{parts[year_idx+2]}"
    except (StopIteration, IndexError):
        meta["slug"] = ""
        meta["url_date"] = ""

    log.info(f"提取元数据: {meta['title']} | {meta['date'][:10] if meta['date'] else 'N/A'} | tags={meta['tags']}")
    return meta


def scan_all_html_metadata() -> list[dict]:
    """扫描所有备份的 HTML 文件，提取元数据。"""
    results = []
    for html_path in HEXO_BACKUP.rglob("index.html"):
        # 只处理 YYYY/MM/DD/ 路径下的文章
        rel = str(html_path.relative_to(HEXO_BACKUP))
        if re.match(r"20\d{2}/\d{2}/\d{2}/", rel):
            meta = extract_metadata_from_html(html_path)
            if meta["title"]:
                results.append(meta)
    log.info(f"共提取 {len(results)} 篇文章元数据")
    return results


def scan_mweb_docs() -> dict[str, tuple[Path, str]]:
    """扫描 MWeb 文档，返回 {标题: (文件路径, 文档ID)} 映射。"""
    title_map = {}
    for md_path in sorted(MWEB_DOCS.glob("*.md")):
        with open(md_path, "r", encoding="utf-8") as f:
            first_lines = f.read(500)

        # 提取第一个 H1 标题
        match = re.search(r"^#\s+(.+)$", first_lines, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            doc_id = md_path.stem  # 文件名不含扩展名，如 "15144239816914"
            title_map[title] = (md_path, doc_id)

    log.info(f"扫描到 {len(title_map)} 个 MWeb 文档")
    return title_map


def normalize_title(title: str) -> str:
    """标准化标题用于匹配：移除空格、标点、大小写差异。"""
    title = title.strip()
    # 统一全角/半角空格
    title = re.sub(r"[\s\u3000]+", "", title)
    # 统一括号
    title = title.replace("（", "(").replace("）", ")")
    # 转小写
    title = title.lower()
    return title


def match_title(html_title: str, mweb_titles: dict) -> str | None:
    """尝试匹配 HTML 标题与 MWeb 标题，返回匹配到的 MWeb 标题或 None。"""
    # 1. 精确匹配
    if html_title in mweb_titles:
        return html_title

    # 2. 手动映射
    mapped = MANUAL_TITLE_MAP.get(html_title)
    if mapped and mapped in mweb_titles:
        return mapped

    # 3. 标准化匹配
    norm_html = normalize_title(html_title)
    for mweb_title in mweb_titles:
        if normalize_title(mweb_title) == norm_html:
            return mweb_title

    # 4. 模糊匹配（相似度 > 0.75）
    best_ratio = 0
    best_match = None
    for mweb_title in mweb_titles:
        ratio = SequenceMatcher(None, norm_html, normalize_title(mweb_title)).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = mweb_title

    if best_ratio > 0.75:
        log.info(f"  模糊匹配: '{html_title}' → '{best_match}' (相似度={best_ratio:.2f})")
        return best_match

    return None


def generate_front_matter(meta: dict) -> str:
    """生成 YAML front matter。"""
    lines = ["---"]
    # 标题中的引号需要转义
    title_escaped = meta["title"].replace('"', '\\"')
    lines.append(f'title: "{title_escaped}"')

    # 日期：优先使用 datetime 属性中的日期
    if meta["date"]:
        lines.append(f'date: {meta["date"]}')

    if meta["lastmod"]:
        lines.append(f'lastmod: {meta["lastmod"]}')

    # 用 url 字段精确控制 URL 路径（Hugo 的 slug 会做 urlize 处理，
    # 会把空格变连字符、转小写，不适合保持旧站 URL 兼容）
    if meta["slug"] and meta["date"]:
        date_str = meta["date"][:10]  # YYYY-MM-DD
        parts = date_str.split("-")
        url_path = f"/{parts[0]}/{parts[1]}/{parts[2]}/{meta['slug']}/"
        url_escaped = url_path.replace('"', '\\"')
        lines.append(f'url: "{url_escaped}"')

    # 标签
    if meta["tags"]:
        lines.append("tags:")
        for tag in meta["tags"]:
            lines.append(f'  - "{tag}"')

    lines.append("draft: false")
    lines.append("---")
    return "\n".join(lines) + "\n"


def collect_referenced_media(content: str) -> list[tuple[str, str]]:
    """从 Markdown 内容中收集所有引用的 media 文件。
    返回 [(media_dir_id, filename), ...] 列表。
    """
    # 匹配 media/{id}/{filename} 格式的引用
    return re.findall(r"media/(\d+)/([^\s\)\"]+)", content)


def process_markdown_content(content: str, doc_id: str) -> str:
    """处理 Markdown 内容：移除 H1 标题、修复图片路径。"""
    # 移除第一个 H1 标题行（front matter 中的 title 已包含）
    content = re.sub(r"^#\s+.+\n+", "", content, count=1)

    # 修复所有 MWeb 图片路径: media/{any_id}/xxx.jpg → xxx.jpg
    content = re.sub(r"media/\d+/", "", content)

    return content


def extract_content_from_html(html_path: Path) -> str:
    """从旧站 HTML 提取文章正文（作为 MWeb 原稿不存在时的回退方案）。"""
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    # 文章正文在 <div class="post-body"> 中
    post_body = soup.find("div", class_="post-body")
    if not post_body:
        return ""

    # 将 HTML 转换为简单 Markdown（保留代码块和基本格式）
    lines = []
    for elem in post_body.children:
        if elem.name is None:
            text = str(elem).strip()
            if text:
                lines.append(text)
        elif elem.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(elem.name[1])
            lines.append(f"\n{'#' * level} {elem.get_text(strip=True)}\n")
        elif elem.name == "p":
            lines.append(elem.get_text() + "\n")
        elif elem.name == "blockquote":
            for p in elem.find_all("p"):
                lines.append(f"> {p.get_text()}\n")
        elif elem.name == "figure" and elem.find("table"):
            # 代码块（Hexo NexT 把代码包在 figure > table 中）
            code = elem.find("td", class_="code")
            if code:
                pre = code.find("pre")
                if pre:
                    lines.append(f"\n```\n{pre.get_text()}\n```\n")
        elif elem.name == "ul":
            for li in elem.find_all("li", recursive=False):
                lines.append(f"- {li.get_text(strip=True)}")
            lines.append("")
        elif elem.name == "ol":
            for i, li in enumerate(elem.find_all("li", recursive=False), 1):
                lines.append(f"{i}. {li.get_text(strip=True)}")
            lines.append("")
        elif elem.name == "img":
            src = elem.get("src", "")
            alt = elem.get("alt", "")
            lines.append(f"![{alt}]({src})\n")
        else:
            text = elem.get_text(strip=True)
            if text:
                lines.append(text + "\n")

    return "\n".join(lines)


def copy_media_files(raw_content: str, doc_id: str, dest_dir: Path) -> int:
    """复制文章引用的所有 MWeb media 文件到 page bundle 目录。
    先复制当前文档的 media 目录，再补充跨目录引用的文件。
    """
    count = 0
    copied_files = set()

    # 1. 复制当前文档的 media 目录中的所有文件
    media_dir = MWEB_MEDIA / doc_id
    if media_dir.exists():
        for media_file in media_dir.iterdir():
            if media_file.is_file():
                shutil.copy2(media_file, dest_dir / media_file.name)
                copied_files.add(media_file.name)
                count += 1

    # 2. 扫描 Markdown 中引用的跨目录 media 文件
    for ref_dir_id, filename in collect_referenced_media(raw_content):
        if filename not in copied_files:
            src = MWEB_MEDIA / ref_dir_id / filename
            if src.exists():
                shutil.copy2(src, dest_dir / filename)
                copied_files.add(filename)
                count += 1
            else:
                log.warning(f"  引用的图片不存在: media/{ref_dir_id}/{filename}")

    return count


def main():
    log.info("=" * 60)
    log.info("开始 Hexo → Hugo 迁移")
    log.info("=" * 60)

    # 1. 扫描旧站 HTML 元数据
    html_metadata = scan_all_html_metadata()

    # 2. 扫描 MWeb 文档
    mweb_titles = scan_mweb_docs()

    # 3. 创建输出目录
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    # 4. 逐篇匹配并生成 Hugo 文章
    matched = 0
    unmatched = []

    for meta in html_metadata:
        mweb_title = match_title(meta["title"], mweb_titles)

        slug = meta["slug"] or meta["title"]
        post_dir = CONTENT_DIR / slug
        post_dir.mkdir(parents=True, exist_ok=True)

        if mweb_title is not None:
            # MWeb 原稿匹配成功
            md_path, doc_id = mweb_titles[mweb_title]

            with open(md_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

            processed = process_markdown_content(raw_content, doc_id)
            media_count = copy_media_files(raw_content, doc_id, post_dir)
            source = "MWeb"
        else:
            # 回退：从旧站 HTML 提取内容
            html_path = next(HEXO_BACKUP.rglob(f"{slug}/index.html"), None)
            if html_path:
                processed = extract_content_from_html(html_path)
                source = "HTML"
            else:
                unmatched.append(meta["title"])
                log.warning(f"未匹配且无 HTML 回退: {meta['title']}")
                continue
            media_count = 0

        # 生成 front matter + 内容
        front_matter = generate_front_matter(meta)
        final_content = front_matter + "\n" + processed

        # 写入 index.md
        output_path = post_dir / "index.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        matched += 1
        log.info(f"✓ [{matched}] {meta['title']} → {slug}/ (来源: {source}, 图片: {media_count})")

    # 5. 输出总结
    log.info("=" * 60)
    log.info(f"迁移完成: {matched} 篇匹配成功, {len(unmatched)} 篇未匹配")

    if unmatched:
        log.warning("未匹配的文章:")
        for title in unmatched:
            log.warning(f"  - {title}")

    # 检查是否有重复的 slug（两篇文章可能 slug 不同但标题近似）
    slugs = [meta["slug"] for meta in html_metadata if meta["slug"]]
    dup_slugs = [s for s in slugs if slugs.count(s) > 1]
    if dup_slugs:
        log.warning(f"发现重复 slug: {set(dup_slugs)}")

    log.info("=" * 60)


if __name__ == "__main__":
    main()
