import json
import os
import re
import secrets
import sqlite3
import hashlib
import hmac
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).parent
PUBLIC_DIR = ROOT / "public"
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", DATA_DIR / "talent_platform.db"))
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
SESSION_COOKIE_NAME = "talent_session"
DEFAULT_INVITE_CODE = "talent2026"
PASSWORD_ITERATIONS = 200_000


INFLUENCER_FIELDS = [
    "id",
    "name",
    "platform",
    "account_id",
    "profile_url",
    "category",
    "followers_count",
    "wechat",
    "phone",
    "email",
    "other_contact",
    "owner",
    "status",
    "remark",
    "created_at",
    "updated_at",
]

PROJECT_FIELDS = [
    "id",
    "name",
    "project_code",
    "status",
    "owner",
    "start_date",
    "end_date",
    "description",
    "created_at",
    "updated_at",
]

CONTENT_LIST_FIELDS = [
    "c.id",
    "c.title",
    "c.influencer_id",
    "i.name AS influencer_name",
    "c.project_id",
    "COALESCE(p.name, '') AS project_name",
    "c.platform",
    "c.content_url",
    "c.canonical_url",
    "c.platform_content_id",
    "c.published_at",
    "c.content_type",
    "c.owner",
    "c.status",
    "c.remark",
    "c.created_at",
    "c.updated_at",
    "m.view_count",
    "m.like_count",
    "m.comment_count",
    "m.collect_count",
    "m.share_count",
    "m.data_source",
    "m.sync_status",
    "m.last_sync_at",
    "m.failed_reason",
]

METRIC_FIELDS = ["view_count", "like_count", "comment_count", "collect_count", "share_count"]
XIAOHONGSHU_SYNC_FIELDS = ["like_count", "comment_count", "collect_count"]
INFLUENCER_PLATFORMS = {"小红书", "抖音", "B站", "视频号", "微博", "快手", "其他"}
INFLUENCER_CATEGORIES = {
    "影视娱乐",
    "音乐",
    "生活",
    "人文艺术",
    "摄影",
    "旅游",
    "搞笑趣闻",
    "情感",
    "教育",
    "母婴育儿",
    "财经",
    "游戏动漫",
    "健康",
    "运动",
    "科学科普",
    "科技",
    "互联网",
    "职场管理",
    "美食",
    "时尚",
    "美妆",
    "萌宠",
    "汽车",
}
PROFILE_URL_DOMAINS = {
    "小红书": ("xiaohongshu.com", "xhslink.com"),
    "抖音": ("douyin.com", "v.douyin.com", "iesdouyin.com"),
    "B站": ("bilibili.com", "space.bilibili.com", "b23.tv"),
    "视频号": ("channels.weixin.qq.com", "weixin.qq.com"),
    "微博": ("weibo.com", "weibo.cn"),
    "快手": ("kuaishou.com", "v.kuaishou.com", "live.kuaishou.com"),
}


def get_connection():
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def column_exists(connection, table_name, column_name):
    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column["name"] == column_name for column in columns)


def add_column_if_missing(connection, table_name, column_definition):
    column_name = column_definition.split(" ", 1)[0]
    if not column_exists(connection, table_name, column_name):
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_definition}")


def get_invite_code():
    return os.environ.get("INVITE_CODE", DEFAULT_INVITE_CODE)


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_ITERATIONS}${salt}${password_hash}"


def verify_password(password, stored_password):
    try:
        iterations_text, salt, expected_hash = stored_password.split("$", 2)
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_text),
        ).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(password_hash, expected_hash)


def generate_session_token():
    return secrets.token_urlsafe(32)


def extract_first_url(text):
    for part in str(text or "").split():
        if part.startswith(("http://", "https://")):
            return part.strip("，,。)")
    return str(text or "").strip()


def normalize_url(raw_url):
    url = extract_first_url(raw_url)
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url.rstrip("/")

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    if netloc.startswith("m."):
        netloc = netloc[2:]

    path = parsed.path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", "", ""))


def extract_platform_content_id(platform, raw_url):
    canonical_url = normalize_url(raw_url)
    parsed = urlparse(canonical_url)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if platform == "小红书" or "xiaohongshu.com" in host:
        for marker in ("explore", "discovery", "item"):
            if marker in path_parts:
                index = path_parts.index(marker)
                if len(path_parts) > index + 1:
                    return path_parts[index + 1]
        return ""

    if platform == "B站" or "bilibili.com" in host:
        if "video" in path_parts:
            index = path_parts.index("video")
            if len(path_parts) > index + 1:
                return path_parts[index + 1]
        for part in path_parts:
            if part.startswith(("BV", "av")):
                return part
        return ""

    if platform == "抖音" or "douyin.com" in host:
        for marker in ("video", "note"):
            if marker in path_parts:
                index = path_parts.index(marker)
                if len(path_parts) > index + 1:
                    return path_parts[index + 1]
        return ""

    if platform == "微博" or "weibo.com" in host:
        if len(path_parts) >= 2:
            return path_parts[-1]
        return ""

    return ""


def initialize_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT '正常',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS influencers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                account_id TEXT DEFAULT '',
                profile_url TEXT DEFAULT '',
                category TEXT DEFAULT '',
                followers_count INTEGER NOT NULL DEFAULT 0 CHECK (followers_count >= 0),
                wechat TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                email TEXT DEFAULT '',
                other_contact TEXT DEFAULT '',
                owner TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT '正常',
                remark TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        add_column_if_missing(connection, "influencers", "account_id TEXT DEFAULT ''")
        add_column_if_missing(connection, "influencers", "profile_url TEXT DEFAULT ''")
        add_column_if_missing(connection, "influencers", "followers_count INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(connection, "influencers", "wechat TEXT DEFAULT ''")
        add_column_if_missing(connection, "influencers", "phone TEXT DEFAULT ''")
        add_column_if_missing(connection, "influencers", "email TEXT DEFAULT ''")
        add_column_if_missing(connection, "influencers", "other_contact TEXT DEFAULT ''")
        add_column_if_missing(connection, "influencers", "owner TEXT DEFAULT ''")
        add_column_if_missing(connection, "influencers", "remark TEXT DEFAULT ''")
        add_column_if_missing(connection, "influencers", "updated_at TEXT DEFAULT ''")

        if column_exists(connection, "influencers", "followers"):
            connection.execute(
                """
                UPDATE influencers
                SET followers_count = followers
                WHERE followers_count = 0 AND followers IS NOT NULL
                """
            )

        connection.execute(
            """
            UPDATE influencers
            SET status = '正常'
            WHERE status IN ('待建联', '已建联', '合作中', '已完成') OR status IS NULL OR status = ''
            """
        )
        connection.execute(
            """
            UPDATE influencers
            SET updated_at = COALESCE(NULLIF(updated_at, ''), created_at, CURRENT_TIMESTAMP)
            WHERE updated_at IS NULL OR updated_at = ''
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_influencers_name_platform
            ON influencers (name, platform)
            """
        )

        count = connection.execute(
            "SELECT COUNT(*) AS total FROM influencers"
        ).fetchone()["total"]
        if count == 0:
            connection.executemany(
                """
                INSERT INTO influencers
                    (name, platform, account_id, profile_url, category, followers_count,
                     wechat, phone, email, other_contact, owner, status, remark)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "小鹿的厨房",
                        "小红书",
                        "redbook_1001",
                        "https://www.xiaohongshu.com/user/profile/redbook_1001",
                        "美食",
                        128000,
                        "xiaolu_ops",
                        "",
                        "",
                        "机构联系人：林同学",
                        "张运营",
                        "正常",
                        "适合新品种草内容",
                    ),
                    (
                        "阿川去旅行",
                        "抖音",
                        "douyin_achuan",
                        "https://www.douyin.com/user/douyin_achuan",
                        "旅行",
                        356000,
                        "",
                        "13800000000",
                        "",
                        "",
                        "李商务",
                        "正常",
                        "短视频表达能力强",
                    ),
                    (
                        "数码研究所",
                        "B站",
                        "bili_digital_lab",
                        "https://space.bilibili.com/2048",
                        "科技",
                        89000,
                        "",
                        "",
                        "creator@example.com",
                        "",
                        "王运营",
                        "停用",
                        "历史合作达人",
                    ),
                ],
            )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                project_code TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT '进行中',
                owner TEXT DEFAULT '',
                start_date TEXT DEFAULT '',
                end_date TEXT DEFAULT '',
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_project_code
            ON projects (project_code)
            WHERE project_code != ''
            """
        )

        project_count = connection.execute(
            "SELECT COUNT(*) AS total FROM projects"
        ).fetchone()["total"]
        if project_count == 0:
            connection.executemany(
                """
                INSERT INTO projects
                    (name, project_code, status, owner, start_date, end_date, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "夏季新品种草项目",
                        "PRJ-2026-SUMMER",
                        "进行中",
                        "张运营",
                        "2026-06-01",
                        "2026-07-15",
                        "用于承接夏季新品达人内容投放。",
                    ),
                    (
                        "品牌口碑内容沉淀",
                        "PRJ-2026-BRAND",
                        "进行中",
                        "李商务",
                        "2026-06-10",
                        "",
                        "长期合作内容沉淀项目。",
                    ),
                ],
            )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS contents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                influencer_id INTEGER NOT NULL,
                project_id INTEGER,
                platform TEXT NOT NULL,
                content_url TEXT NOT NULL UNIQUE,
                canonical_url TEXT DEFAULT '',
                platform_content_id TEXT DEFAULT '',
                published_at TEXT NOT NULL,
                content_type TEXT DEFAULT '',
                owner TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT '正常',
                remark TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (influencer_id) REFERENCES influencers(id),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
            """
        )
        add_column_if_missing(connection, "contents", "canonical_url TEXT DEFAULT ''")
        add_column_if_missing(connection, "contents", "platform_content_id TEXT DEFAULT ''")

        content_rows = connection.execute(
            """
            SELECT id, platform, content_url, canonical_url, platform_content_id
            FROM contents
            """
        ).fetchall()
        for row in content_rows:
            canonical_url = row["canonical_url"] or normalize_url(row["content_url"])
            platform_content_id = row["platform_content_id"] or extract_platform_content_id(
                row["platform"], row["content_url"]
            )
            connection.execute(
                """
                UPDATE contents
                SET canonical_url = ?, platform_content_id = ?
                WHERE id = ?
                """,
                (canonical_url, platform_content_id, row["id"]),
            )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS content_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER NOT NULL UNIQUE,
                view_count INTEGER NOT NULL DEFAULT 0 CHECK (view_count >= 0),
                like_count INTEGER NOT NULL DEFAULT 0 CHECK (like_count >= 0),
                comment_count INTEGER NOT NULL DEFAULT 0 CHECK (comment_count >= 0),
                collect_count INTEGER NOT NULL DEFAULT 0 CHECK (collect_count >= 0),
                share_count INTEGER NOT NULL DEFAULT 0 CHECK (share_count >= 0),
                data_source TEXT NOT NULL DEFAULT '手动',
                sync_status TEXT NOT NULL DEFAULT '待同步',
                last_sync_at TEXT DEFAULT '',
                next_sync_at TEXT DEFAULT '',
                failed_reason TEXT DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES contents(id)
            )
            """
        )
        add_column_if_missing(connection, "content_metrics", "last_sync_at TEXT DEFAULT ''")
        add_column_if_missing(connection, "content_metrics", "next_sync_at TEXT DEFAULT ''")
        add_column_if_missing(connection, "content_metrics", "failed_reason TEXT DEFAULT ''")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT DEFAULT '',
                raw_summary TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                FOREIGN KEY (content_id) REFERENCES contents(id)
            )
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_contents_content_url
            ON contents (content_url)
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_contents_canonical_url
            ON contents (canonical_url)
            WHERE canonical_url != ''
            """
        )
        connection.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_contents_platform_content_id
            ON contents (platform, platform_content_id)
            WHERE platform_content_id != ''
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_contents_influencer_id
            ON contents (influencer_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_contents_project_id
            ON contents (project_id)
            """
        )


def influencer_to_dict(row):
    result = dict(row)
    result["followers_count"] = int(result.get("followers_count") or 0)
    return result


def project_to_dict(row):
    return dict(row)


def content_to_dict(row):
    result = dict(row)
    for key in METRIC_FIELDS:
        result[key] = int(result.get(key) or 0)
    result["interaction_count"] = (
        result["like_count"]
        + result["comment_count"]
        + result["collect_count"]
        + result["share_count"]
    )
    return result


def parse_metric_number(value):
    text = str(value or "").strip().replace(",", "")
    if not text:
        return None
    text = text.replace("+", "")
    multiplier = 1
    lowered = text.lower()
    if "万" in text or "w" in lowered:
        multiplier = 10000
    elif "千" in text or "k" in lowered:
        multiplier = 1000
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    return int(float(match.group(0)) * multiplier)


def find_metric_value(page_text, field_names):
    for field_name in field_names:
        patterns = [
            rf'"{field_name}"\s*:\s*"([^"]+)"',
            rf'"{field_name}"\s*:\s*(\d+(?:\.\d+)?)',
            rf"'{field_name}'\s*:\s*'([^']+)'",
            rf"'{field_name}'\s*:\s*(\d+(?:\.\d+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, page_text, flags=re.IGNORECASE)
            if match:
                value = parse_metric_number(match.group(1))
                if value is not None:
                    return value
    return None


def find_labeled_metric(page_text, labels):
    compact_text = re.sub(r"\s+", "", page_text)
    for label in labels:
        patterns = [
            rf"{label}[:：]?([0-9,.]+(?:万|千|w|W|k|K)?)",
            rf"([0-9,.]+(?:万|千|w|W|k|K)?){label}",
        ]
        for pattern in patterns:
            match = re.search(pattern, compact_text)
            if match:
                value = parse_metric_number(match.group(1))
                if value is not None:
                    return value
    return None


def fetch_page_text(url):
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urlopen(request, timeout=18) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="ignore")


def scrape_xiaohongshu_metrics(content_url):
    page_text = fetch_page_text(content_url)
    if "验证" in page_text and "小红书" in page_text:
        raise ValueError("页面可能触发验证或风控，暂时无法自动抓取")

    metrics = {
        "like_count": find_metric_value(
            page_text,
            ["likedCount", "likeCount", "liked_count", "like_count", "likes"],
        ),
        "comment_count": find_metric_value(
            page_text,
            ["commentCount", "commentsCount", "comment_count", "comments"],
        ),
        "collect_count": find_metric_value(
            page_text,
            ["collectedCount", "collectCount", "favoriteCount", "collect_count", "favorites"],
        ),
    }

    label_fallbacks = {
        "like_count": ["点赞", "赞"],
        "comment_count": ["评论"],
        "collect_count": ["收藏"],
    }
    for key, labels in label_fallbacks.items():
        if metrics[key] is None:
            metrics[key] = find_labeled_metric(page_text, labels)

    parsed_metrics = {
        key: metrics[key]
        for key in XIAOHONGSHU_SYNC_FIELDS
        if metrics.get(key) is not None
    }
    if not parsed_metrics:
        raise ValueError("没有从页面中识别到点赞、评论或收藏数据")
    return parsed_metrics


def scrape_content_metrics(content):
    if content["platform"] != "小红书" and "xiaohongshu.com" not in content["content_url"]:
        raise ValueError("当前第一版只支持小红书链接自动同步")
    return scrape_xiaohongshu_metrics(content["content_url"])


def parse_json_body(handler):
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length <= 0 or content_length > 100_000:
        raise ValueError("请求内容为空或过大")
    return json.loads(handler.rfile.read(content_length))


def clean_text(payload, key, default=""):
    return str(payload.get(key, default) or "").strip()


def normalize_category_tags(value):
    tags = []
    for tag in re.split(r"[、,，]", str(value or "")):
        tag = tag.strip()
        if not tag:
            continue
        if tag not in INFLUENCER_CATEGORIES:
            raise ValueError(f"达人分类「{tag}」不在可选标签中")
        if tag not in tags:
            tags.append(tag)
    return "、".join(tags)


def host_matches_domain(host, allowed_domain):
    return host == allowed_domain or host.endswith(f".{allowed_domain}")


def normalize_profile_url(profile_url, platform):
    url = str(profile_url or "").strip()
    if not url:
        return ""
    if re.search(r"\s", url):
        raise ValueError("主页链接不能包含空格")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("主页链接必须以 http:// 或 https:// 开头")
    if platform == "其他":
        return url

    allowed_domains = PROFILE_URL_DOMAINS.get(platform, ())
    host = parsed.netloc.lower()
    if allowed_domains and not any(host_matches_domain(host, domain) for domain in allowed_domains):
        raise ValueError(f"当前媒体平台为{platform}，请填写{platform}相关主页链接")
    return url


def normalize_phone(phone):
    value = str(phone or "").strip()
    if not value:
        return ""
    compact = re.sub(r"[\s-]", "", value)
    if compact.startswith("+86"):
        compact = compact[3:]
    elif compact.startswith("0086"):
        compact = compact[4:]
    if not re.fullmatch(r"1[3-9]\d{9}", compact):
        raise ValueError("手机号格式不正确，请填写 11 位中国大陆手机号")
    return compact


def normalize_email(email):
    value = str(email or "").strip().lower()
    if not value:
        return ""
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise ValueError("邮箱格式不正确")
    return value


def clean_int(payload, key, default=0):
    raw_value = payload.get(key, default)
    if raw_value in ("", None):
        return default
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{key} 必须是数字") from error
    if value < 0:
        raise ValueError(f"{key} 不能小于 0")
    return value


def parse_optional_int_query(params, key):
    raw_value = (params.get(key, [""])[0] or "").strip()
    if raw_value == "":
        return None
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{key} 必须是数字") from error
    if value < 0:
        raise ValueError(f"{key} 不能小于 0")
    return value


def clean_optional_id(payload, key):
    raw_value = payload.get(key, "")
    if raw_value in ("", None):
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{key} 不正确") from error
    if value <= 0:
        raise ValueError(f"{key} 不正确")
    return value


def normalize_influencer_payload(payload):
    name = clean_text(payload, "name")
    platform = clean_text(payload, "platform")
    category = normalize_category_tags(clean_text(payload, "category"))
    status = clean_text(payload, "status", "正常") or "正常"

    if not name:
        raise ValueError("达人名称不能为空")
    if not platform:
        raise ValueError("媒体平台不能为空")
    if platform not in INFLUENCER_PLATFORMS:
        raise ValueError("媒体平台不在可选范围内")
    if status not in {"正常", "停用"}:
        raise ValueError("达人状态只能是正常或停用")

    raw_followers = payload.get("followers_count", payload.get("followers", 0))
    if raw_followers in ("", None):
        followers_count = 0
    else:
        try:
            followers_count = int(raw_followers)
        except (TypeError, ValueError) as error:
            raise ValueError("粉丝数必须是数字") from error
    if followers_count < 0:
        raise ValueError("粉丝数不能小于 0")

    return {
        "name": name,
        "platform": platform,
        "account_id": clean_text(payload, "account_id"),
        "profile_url": normalize_profile_url(clean_text(payload, "profile_url"), platform),
        "category": category,
        "followers_count": followers_count,
        "wechat": clean_text(payload, "wechat"),
        "phone": normalize_phone(clean_text(payload, "phone")),
        "email": normalize_email(clean_text(payload, "email")),
        "other_contact": clean_text(payload, "other_contact"),
        "owner": clean_text(payload, "owner"),
        "status": status,
        "remark": clean_text(payload, "remark"),
    }


def normalize_project_payload(payload):
    name = clean_text(payload, "name")
    status = clean_text(payload, "status", "进行中") or "进行中"

    if not name:
        raise ValueError("项目名称不能为空")
    if status not in {"进行中", "已结束", "归档"}:
        raise ValueError("项目状态只能是进行中、已结束或归档")

    return {
        "name": name,
        "project_code": clean_text(payload, "project_code"),
        "status": status,
        "owner": clean_text(payload, "owner"),
        "start_date": clean_text(payload, "start_date"),
        "end_date": clean_text(payload, "end_date"),
        "description": clean_text(payload, "description"),
    }


def normalize_content_payload(payload, connection):
    title = clean_text(payload, "title")
    content_url = clean_text(payload, "content_url")
    published_at = clean_text(payload, "published_at")
    influencer_id = clean_optional_id(payload, "influencer_id")
    project_id = clean_optional_id(payload, "project_id")
    status = clean_text(payload, "status", "正常") or "正常"
    content_type = clean_text(payload, "content_type", "视频") or "视频"

    if not title:
        raise ValueError("内容标题不能为空")
    if influencer_id is None:
        raise ValueError("内容必须选择一个达人")
    if not content_url:
        raise ValueError("内容链接不能为空")
    if not published_at:
        raise ValueError("发布时间不能为空")
    if status not in {"正常", "作废"}:
        raise ValueError("内容状态只能是正常或作废")

    influencer = fetch_influencer(connection, influencer_id)
    if influencer is None:
        raise ValueError("选择的达人不存在")
    if project_id is not None and fetch_project(connection, project_id) is None:
        raise ValueError("选择的项目不存在")
    canonical_url = normalize_url(content_url)
    platform_content_id = extract_platform_content_id(influencer["platform"], content_url)

    return {
        "title": title,
        "influencer_id": influencer_id,
        "project_id": project_id,
        "platform": influencer["platform"],
        "content_url": content_url,
        "canonical_url": canonical_url,
        "platform_content_id": platform_content_id,
        "published_at": published_at,
        "content_type": content_type,
        "owner": clean_text(payload, "owner"),
        "status": status,
        "remark": clean_text(payload, "remark"),
        "view_count": clean_int(payload, "view_count"),
        "like_count": clean_int(payload, "like_count"),
        "comment_count": clean_int(payload, "comment_count"),
        "collect_count": clean_int(payload, "collect_count"),
        "share_count": clean_int(payload, "share_count"),
        "data_source": clean_text(payload, "data_source", "手动") or "手动",
        "sync_status": clean_text(payload, "sync_status", "待同步") or "待同步",
    }


def fetch_influencer(connection, influencer_id):
    fields = ", ".join(INFLUENCER_FIELDS)
    row = connection.execute(
        f"SELECT {fields} FROM influencers WHERE id = ?",
        (influencer_id,),
    ).fetchone()
    return influencer_to_dict(row) if row else None


def fetch_project(connection, project_id):
    fields = ", ".join(PROJECT_FIELDS)
    row = connection.execute(
        f"SELECT {fields} FROM projects WHERE id = ?",
        (project_id,),
    ).fetchone()
    return project_to_dict(row) if row else None


def fetch_content(connection, content_id):
    fields = ", ".join(CONTENT_LIST_FIELDS)
    row = connection.execute(
        f"""
        SELECT {fields}
        FROM contents c
        JOIN influencers i ON i.id = c.influencer_id
        LEFT JOIN projects p ON p.id = c.project_id
        LEFT JOIN content_metrics m ON m.content_id = c.id
        WHERE c.id = ?
        """,
        (content_id,),
    ).fetchone()
    return content_to_dict(row) if row else None


def fetch_user(connection, user_id):
    row = connection.execute(
        """
        SELECT id, username, display_name
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    return user_to_dict(row) if row else None


def duplicate_exists(connection, name, platform, exclude_id=None):
    if exclude_id is None:
        row = connection.execute(
            "SELECT id FROM influencers WHERE name = ? AND platform = ?",
            (name, platform),
        ).fetchone()
    else:
        row = connection.execute(
            """
            SELECT id FROM influencers
            WHERE name = ? AND platform = ? AND id != ?
            """,
            (name, platform, exclude_id),
        ).fetchone()
    return row is not None


def project_code_exists(connection, project_code, exclude_id=None):
    if not project_code:
        return False
    if exclude_id is None:
        row = connection.execute(
            "SELECT id FROM projects WHERE project_code = ?",
            (project_code,),
        ).fetchone()
    else:
        row = connection.execute(
            "SELECT id FROM projects WHERE project_code = ? AND id != ?",
            (project_code, exclude_id),
        ).fetchone()
    return row is not None


def content_url_exists(connection, content_url, exclude_id=None):
    if exclude_id is None:
        row = connection.execute(
            "SELECT id FROM contents WHERE content_url = ?",
            (content_url,),
        ).fetchone()
    else:
        row = connection.execute(
            "SELECT id FROM contents WHERE content_url = ? AND id != ?",
            (content_url, exclude_id),
        ).fetchone()
    return row is not None


def content_identity_exists(connection, payload, exclude_id=None):
    checks = [("content_url", payload["content_url"])]
    if payload["canonical_url"]:
        checks.append(("canonical_url", payload["canonical_url"]))

    for field, value in checks:
        if exclude_id is None:
            row = connection.execute(
                f"SELECT id FROM contents WHERE {field} = ?",
                (value,),
            ).fetchone()
        else:
            row = connection.execute(
                f"SELECT id FROM contents WHERE {field} = ? AND id != ?",
                (value, exclude_id),
            ).fetchone()
        if row is not None:
            return True

    if payload["platform_content_id"]:
        if exclude_id is None:
            row = connection.execute(
                """
                SELECT id FROM contents
                WHERE platform = ? AND platform_content_id = ?
                """,
                (payload["platform"], payload["platform_content_id"]),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT id FROM contents
                WHERE platform = ? AND platform_content_id = ? AND id != ?
                """,
                (payload["platform"], payload["platform_content_id"], exclude_id),
            ).fetchone()
        if row is not None:
            return True

    return False


def get_dashboard_summary(connection):
    totals = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM influencers) AS influencer_count,
            (SELECT COUNT(*) FROM influencers WHERE status = '正常') AS active_influencer_count,
            (SELECT COUNT(*) FROM projects) AS project_count,
            (SELECT COUNT(*) FROM projects WHERE status = '进行中') AS active_project_count,
            (SELECT COUNT(*) FROM contents) AS content_count,
            COALESCE((SELECT SUM(view_count) FROM content_metrics), 0) AS total_views,
            COALESCE((
                SELECT SUM(like_count + comment_count + collect_count + share_count)
                FROM content_metrics
            ), 0) AS total_interactions
        """
    ).fetchone()

    recent_contents = connection.execute(
        """
        SELECT
            c.id,
            c.title,
            c.platform,
            c.published_at,
            i.name AS influencer_name,
            COALESCE(p.name, '') AS project_name,
            COALESCE(m.view_count, 0) AS view_count,
            COALESCE(m.like_count + m.comment_count + m.collect_count + m.share_count, 0)
                AS interaction_count,
            COALESCE(m.sync_status, '待同步') AS sync_status
        FROM contents c
        JOIN influencers i ON i.id = c.influencer_id
        LEFT JOIN projects p ON p.id = c.project_id
        LEFT JOIN content_metrics m ON m.content_id = c.id
        ORDER BY c.published_at DESC, c.id DESC
        LIMIT 5
        """
    ).fetchall()

    platform_distribution = connection.execute(
        """
        SELECT platform, COUNT(*) AS content_count, COALESCE(SUM(view_count), 0) AS view_count
        FROM contents c
        LEFT JOIN content_metrics m ON m.content_id = c.id
        GROUP BY platform
        ORDER BY content_count DESC, view_count DESC
        """
    ).fetchall()

    sync_distribution = connection.execute(
        """
        SELECT sync_status, COUNT(*) AS content_count
        FROM content_metrics
        GROUP BY sync_status
        ORDER BY content_count DESC
        """
    ).fetchall()

    return {
        "totals": dict(totals),
        "recent_contents": [dict(row) for row in recent_contents],
        "platform_distribution": [dict(row) for row in platform_distribution],
        "sync_distribution": [dict(row) for row in sync_distribution],
    }


def has_legacy_followers_column(connection):
    return column_exists(connection, "influencers", "followers")


def user_to_dict(row):
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"] or row["username"],
    }


class TalentPlatformHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def send_json(self, data, status=HTTPStatus.OK, cookie_token=None, clear_cookie=False):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if cookie_token:
            self.set_session_cookie(cookie_token)
        if clear_cookie:
            self.clear_session_cookie()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message, status=HTTPStatus.BAD_REQUEST):
        self.send_json({"message": message}, status)

    def get_session_token(self):
        cookie_header = self.headers.get("Cookie", "")
        cookie = SimpleCookie()
        cookie.load(cookie_header)
        morsel = cookie.get(SESSION_COOKIE_NAME)
        return morsel.value if morsel else ""

    def get_current_user(self):
        token = self.get_session_token()
        if not token:
            return None
        with get_connection() as connection:
            row = connection.execute(
                """
                SELECT u.id, u.username, u.display_name
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = ? AND u.status = '正常'
                """,
                (token,),
            ).fetchone()
            if row:
                connection.execute(
                    "UPDATE sessions SET last_seen_at = CURRENT_TIMESTAMP WHERE token = ?",
                    (token,),
                )
        return user_to_dict(row) if row else None

    def require_user(self):
        user = self.get_current_user()
        if user is None:
            if self.path.startswith("/api/"):
                self.send_error_json("请先登录", HTTPStatus.UNAUTHORIZED)
            else:
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", "/login.html")
                self.end_headers()
            return None
        return user

    def set_session_cookie(self, token):
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}={token}; HttpOnly; Path=/; SameSite=Lax",
        )

    def clear_session_cookie(self):
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0",
        )

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        public_paths = {"/login.html", "/register.html", "/auth.js", "/styles.css"}
        if path in public_paths:
            super().do_GET()
            return

        if path == "/healthz":
            self.send_json({"status": "ok"})
            return

        if path == "/api/auth/me":
            user = self.require_user()
            if user is not None:
                self.send_json({"user": user})
            return

        if path == "/":
            if self.require_user() is None:
                return
            self.path = "/index.html"
            super().do_GET()
            return

        if path == "/index.html":
            if self.require_user() is None:
                return
            super().do_GET()
            return

        if path.startswith("/api/") and path not in {"/api/auth/me"}:
            if self.require_user() is None:
                return

        if path == "/api/dashboard/summary":
            with get_connection() as connection:
                summary = get_dashboard_summary(connection)
            self.send_json(summary)
            return

        if path == "/api/influencers":
            params = parse_qs(parsed_url.query)
            keyword = (params.get("keyword", [""])[0] or "").strip()
            platform = (params.get("platform", [""])[0] or "").strip()
            category = (params.get("category", [""])[0] or "").strip()
            owner = (params.get("owner", [""])[0] or "").strip()
            try:
                followers_min = parse_optional_int_query(params, "followers_min")
                followers_max = parse_optional_int_query(params, "followers_max")
            except ValueError as error:
                self.send_error_json(str(error), HTTPStatus.BAD_REQUEST)
                return
            if followers_min is not None and followers_max is not None and followers_min > followers_max:
                self.send_error_json("粉丝数最小值不能大于最大值", HTTPStatus.BAD_REQUEST)
                return

            where = []
            values = []
            if keyword:
                where.append("name LIKE ?")
                values.append(f"%{keyword}%")
            if platform:
                where.append("platform = ?")
                values.append(platform)
            if category:
                where.append("category LIKE ?")
                values.append(f"%{category}%")
            if owner:
                where.append("owner LIKE ?")
                values.append(f"%{owner}%")
            if followers_min is not None:
                where.append("followers_count >= ?")
                values.append(followers_min)
            if followers_max is not None:
                where.append("followers_count <= ?")
                values.append(followers_max)

            fields = ", ".join(INFLUENCER_FIELDS)
            sql = f"SELECT {fields} FROM influencers"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY created_at DESC, id DESC"

            with get_connection() as connection:
                rows = connection.execute(sql, values).fetchall()
            self.send_json([influencer_to_dict(row) for row in rows])
            return

        if path.startswith("/api/influencers/"):
            influencer_id = self.extract_id(path)
            if influencer_id is None:
                self.send_error_json("达人 ID 不正确", HTTPStatus.BAD_REQUEST)
                return

            with get_connection() as connection:
                influencer = fetch_influencer(connection, influencer_id)
            if influencer is None:
                self.send_error_json("达人不存在", HTTPStatus.NOT_FOUND)
                return
            self.send_json(influencer)
            return

        if path == "/api/projects":
            params = parse_qs(parsed_url.query)
            keyword = (params.get("keyword", [""])[0] or "").strip()
            status = (params.get("status", [""])[0] or "").strip()
            owner = (params.get("owner", [""])[0] or "").strip()

            where = []
            values = []
            if keyword:
                where.append("(name LIKE ? OR project_code LIKE ?)")
                values.extend([f"%{keyword}%", f"%{keyword}%"])
            if status:
                where.append("status = ?")
                values.append(status)
            if owner:
                where.append("owner LIKE ?")
                values.append(f"%{owner}%")

            fields = ", ".join(PROJECT_FIELDS)
            sql = f"SELECT {fields} FROM projects"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY created_at DESC, id DESC"

            with get_connection() as connection:
                rows = connection.execute(sql, values).fetchall()
            self.send_json([project_to_dict(row) for row in rows])
            return

        if path.startswith("/api/projects/"):
            project_id = self.extract_id(path)
            if project_id is None:
                self.send_error_json("项目 ID 不正确", HTTPStatus.BAD_REQUEST)
                return

            with get_connection() as connection:
                project = fetch_project(connection, project_id)
            if project is None:
                self.send_error_json("项目不存在", HTTPStatus.NOT_FOUND)
                return
            self.send_json(project)
            return

        if path == "/api/contents":
            params = parse_qs(parsed_url.query)
            keyword = (params.get("keyword", [""])[0] or "").strip()
            platform = (params.get("platform", [""])[0] or "").strip()
            project_id = (params.get("project_id", [""])[0] or "").strip()
            try:
                views_min = parse_optional_int_query(params, "views_min")
                views_max = parse_optional_int_query(params, "views_max")
                interactions_min = parse_optional_int_query(params, "interactions_min")
                interactions_max = parse_optional_int_query(params, "interactions_max")
            except ValueError as error:
                self.send_error_json(str(error), HTTPStatus.BAD_REQUEST)
                return
            if views_min is not None and views_max is not None and views_min > views_max:
                self.send_error_json("播放量最小值不能大于最大值", HTTPStatus.BAD_REQUEST)
                return
            if (
                interactions_min is not None
                and interactions_max is not None
                and interactions_min > interactions_max
            ):
                self.send_error_json("互动量最小值不能大于最大值", HTTPStatus.BAD_REQUEST)
                return

            where = []
            values = []
            if keyword:
                where.append("(c.title LIKE ? OR c.content_url LIKE ? OR i.name LIKE ?)")
                values.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
            if platform:
                where.append("c.platform = ?")
                values.append(platform)
            if project_id == "none":
                where.append("c.project_id IS NULL")
            elif project_id:
                try:
                    project_id_value = int(project_id)
                except ValueError:
                    self.send_error_json("项目筛选不正确", HTTPStatus.BAD_REQUEST)
                    return
                where.append("c.project_id = ?")
                values.append(project_id_value)
            if views_min is not None:
                where.append("COALESCE(m.view_count, 0) >= ?")
                values.append(views_min)
            if views_max is not None:
                where.append("COALESCE(m.view_count, 0) <= ?")
                values.append(views_max)
            interaction_expression = (
                "COALESCE(m.like_count, 0) + COALESCE(m.comment_count, 0) + "
                "COALESCE(m.collect_count, 0) + COALESCE(m.share_count, 0)"
            )
            if interactions_min is not None:
                where.append(f"({interaction_expression}) >= ?")
                values.append(interactions_min)
            if interactions_max is not None:
                where.append(f"({interaction_expression}) <= ?")
                values.append(interactions_max)

            fields = ", ".join(CONTENT_LIST_FIELDS)
            sql = f"""
                SELECT {fields}
                FROM contents c
                JOIN influencers i ON i.id = c.influencer_id
                LEFT JOIN projects p ON p.id = c.project_id
                LEFT JOIN content_metrics m ON m.content_id = c.id
            """
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY c.created_at DESC, c.id DESC"

            with get_connection() as connection:
                rows = connection.execute(sql, values).fetchall()
            self.send_json([content_to_dict(row) for row in rows])
            return

        if path.startswith("/api/contents/"):
            content_id = self.extract_id(path)
            if content_id is None:
                self.send_error_json("内容 ID 不正确", HTTPStatus.BAD_REQUEST)
                return

            with get_connection() as connection:
                content = fetch_content(connection, content_id)
            if content is None:
                self.send_error_json("内容不存在", HTTPStatus.NOT_FOUND)
                return
            self.send_json(content)
            return

        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/auth/register":
            self.register_user()
            return
        if path == "/api/auth/login":
            self.login_user()
            return
        if path == "/api/auth/logout":
            self.logout_user()
            return
        if self.require_user() is None:
            return
        if path.startswith("/api/contents/") and path.endswith("/sync"):
            self.sync_content(path)
            return
        if path == "/api/contents":
            self.create_content()
            return
        if path == "/api/projects":
            self.create_project()
            return
        if path != "/api/influencers":
            self.send_error_json("接口不存在", HTTPStatus.NOT_FOUND)
            return

        try:
            payload = normalize_influencer_payload(parse_json_body(self))
            with get_connection() as connection:
                if duplicate_exists(connection, payload["name"], payload["platform"]):
                    raise ValueError("同一个媒体平台下已存在同名达人，不能重复录入")

                columns = [
                    "name",
                    "platform",
                    "account_id",
                    "profile_url",
                    "category",
                    "followers_count",
                    "wechat",
                    "phone",
                    "email",
                    "other_contact",
                    "owner",
                    "status",
                    "remark",
                ]
                values = [
                    ":name",
                    ":platform",
                    ":account_id",
                    ":profile_url",
                    ":category",
                    ":followers_count",
                    ":wechat",
                    ":phone",
                    ":email",
                    ":other_contact",
                    ":owner",
                    ":status",
                    ":remark",
                ]
                if has_legacy_followers_column(connection):
                    columns.append("followers")
                    values.append(":followers_count")
                columns.append("updated_at")
                values.append("CURRENT_TIMESTAMP")

                cursor = connection.execute(
                    f"""
                    INSERT INTO influencers ({", ".join(columns)})
                    VALUES ({", ".join(values)})
                    """,
                    payload,
                )
                influencer = fetch_influencer(connection, cursor.lastrowid)
            self.send_json(influencer, HTTPStatus.CREATED)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_error_json(str(error), HTTPStatus.BAD_REQUEST)
        except sqlite3.IntegrityError:
            self.send_error_json("同一个媒体平台下已存在同名达人，不能重复录入", HTTPStatus.BAD_REQUEST)

    def register_user(self):
        try:
            payload = parse_json_body(self)
            username = clean_text(payload, "username").lower()
            display_name = clean_text(payload, "display_name")
            password = clean_text(payload, "password")
            invite_code = clean_text(payload, "invite_code")

            if not username:
                raise ValueError("账号不能为空")
            if len(username) < 3 or len(username) > 40:
                raise ValueError("账号长度需要在 3-40 位之间")
            if not re.fullmatch(r"[a-z0-9_.@-]+", username):
                raise ValueError("账号只能包含字母、数字、下划线、点、@ 或横线")
            if len(password) < 6:
                raise ValueError("密码至少 6 位")
            if invite_code != get_invite_code():
                raise ValueError("邀请码不正确")

            password_hash = hash_password(password)
            token = generate_session_token()
            with get_connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (username, password_hash, display_name, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (username, password_hash, display_name),
                )
                user_id = cursor.lastrowid
                connection.execute(
                    "INSERT INTO sessions (token, user_id) VALUES (?, ?)",
                    (token, user_id),
                )
                user = fetch_user(connection, user_id)
            self.send_json({"user": user}, HTTPStatus.CREATED, cookie_token=token)
        except sqlite3.IntegrityError:
            self.send_error_json("账号已存在", HTTPStatus.BAD_REQUEST)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_error_json(str(error), HTTPStatus.BAD_REQUEST)

    def login_user(self):
        try:
            payload = parse_json_body(self)
            username = clean_text(payload, "username").lower()
            password = clean_text(payload, "password")
            if not username or not password:
                raise ValueError("账号和密码不能为空")

            with get_connection() as connection:
                row = connection.execute(
                    """
                    SELECT id, username, password_hash, display_name
                    FROM users
                    WHERE username = ? AND status = '正常'
                    """,
                    (username,),
                ).fetchone()
                if row is None or not verify_password(password, row["password_hash"]):
                    raise ValueError("账号或密码不正确")
                token = generate_session_token()
                connection.execute(
                    "INSERT INTO sessions (token, user_id) VALUES (?, ?)",
                    (token, row["id"]),
                )
                user = user_to_dict(row)
            self.send_json({"user": user}, cookie_token=token)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_error_json(str(error), HTTPStatus.BAD_REQUEST)

    def logout_user(self):
        token = self.get_session_token()
        if token:
            with get_connection() as connection:
                connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
        self.send_json({"message": "已退出"}, clear_cookie=True)

    def do_PUT(self):
        path = urlparse(self.path).path
        if self.require_user() is None:
            return
        if path.startswith("/api/contents/"):
            self.update_content(path)
            return
        if path.startswith("/api/projects/"):
            self.update_project(path)
            return
        if not path.startswith("/api/influencers/"):
            self.send_error_json("接口不存在", HTTPStatus.NOT_FOUND)
            return

        influencer_id = self.extract_id(path)
        if influencer_id is None:
            self.send_error_json("达人 ID 不正确", HTTPStatus.BAD_REQUEST)
            return

        try:
            payload = normalize_influencer_payload(parse_json_body(self))
            with get_connection() as connection:
                if fetch_influencer(connection, influencer_id) is None:
                    self.send_error_json("达人不存在", HTTPStatus.NOT_FOUND)
                    return
                if duplicate_exists(connection, payload["name"], payload["platform"], influencer_id):
                    raise ValueError("同一个媒体平台下已存在同名达人，不能重复录入")

                update_payload = {**payload, "id": influencer_id}
                assignments = [
                    "name = :name",
                    "platform = :platform",
                    "account_id = :account_id",
                    "profile_url = :profile_url",
                    "category = :category",
                    "followers_count = :followers_count",
                    "wechat = :wechat",
                    "phone = :phone",
                    "email = :email",
                    "other_contact = :other_contact",
                    "owner = :owner",
                    "status = :status",
                    "remark = :remark",
                ]
                if has_legacy_followers_column(connection):
                    assignments.append("followers = :followers_count")
                assignments.append("updated_at = CURRENT_TIMESTAMP")

                connection.execute(
                    f"""
                    UPDATE influencers
                    SET {", ".join(assignments)}
                    WHERE id = :id
                    """,
                    update_payload,
                )
                influencer = fetch_influencer(connection, influencer_id)
            self.send_json(influencer)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_error_json(str(error), HTTPStatus.BAD_REQUEST)
        except sqlite3.IntegrityError:
            self.send_error_json("同一个媒体平台下已存在同名达人，不能重复录入", HTTPStatus.BAD_REQUEST)

    def create_project(self):
        try:
            payload = normalize_project_payload(parse_json_body(self))
            with get_connection() as connection:
                if project_code_exists(connection, payload["project_code"]):
                    raise ValueError("项目编号已存在，不能重复录入")

                cursor = connection.execute(
                    """
                    INSERT INTO projects
                        (name, project_code, status, owner, start_date, end_date,
                         description, updated_at)
                    VALUES
                        (:name, :project_code, :status, :owner, :start_date, :end_date,
                         :description, CURRENT_TIMESTAMP)
                    """,
                    payload,
                )
                project = fetch_project(connection, cursor.lastrowid)
            self.send_json(project, HTTPStatus.CREATED)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_error_json(str(error), HTTPStatus.BAD_REQUEST)
        except sqlite3.IntegrityError:
            self.send_error_json("项目编号已存在，不能重复录入", HTTPStatus.BAD_REQUEST)

    def update_project(self, path):
        project_id = self.extract_id(path)
        if project_id is None:
            self.send_error_json("项目 ID 不正确", HTTPStatus.BAD_REQUEST)
            return

        try:
            payload = normalize_project_payload(parse_json_body(self))
            with get_connection() as connection:
                if fetch_project(connection, project_id) is None:
                    self.send_error_json("项目不存在", HTTPStatus.NOT_FOUND)
                    return
                if project_code_exists(connection, payload["project_code"], project_id):
                    raise ValueError("项目编号已存在，不能重复录入")

                update_payload = {**payload, "id": project_id}
                connection.execute(
                    """
                    UPDATE projects
                    SET
                        name = :name,
                        project_code = :project_code,
                        status = :status,
                        owner = :owner,
                        start_date = :start_date,
                        end_date = :end_date,
                        description = :description,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """,
                    update_payload,
                )
                project = fetch_project(connection, project_id)
            self.send_json(project)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_error_json(str(error), HTTPStatus.BAD_REQUEST)
        except sqlite3.IntegrityError:
            self.send_error_json("项目编号已存在，不能重复录入", HTTPStatus.BAD_REQUEST)

    def create_content(self):
        try:
            with get_connection() as connection:
                payload = normalize_content_payload(parse_json_body(self), connection)
                if content_identity_exists(connection, payload):
                    raise ValueError("内容链接已存在，不能重复录入")

                cursor = connection.execute(
                    """
                    INSERT INTO contents
                        (title, influencer_id, project_id, platform, content_url, canonical_url,
                         platform_content_id, published_at, content_type, owner, status, remark,
                         updated_at)
                    VALUES
                        (:title, :influencer_id, :project_id, :platform, :content_url,
                         :canonical_url, :platform_content_id, :published_at, :content_type,
                         :owner, :status, :remark, CURRENT_TIMESTAMP)
                    """,
                    payload,
                )
                content_id = cursor.lastrowid
                connection.execute(
                    """
                    INSERT INTO content_metrics
                        (content_id, view_count, like_count, comment_count, collect_count,
                         share_count, data_source, sync_status, updated_at)
                    VALUES
                        (:content_id, :view_count, :like_count, :comment_count, :collect_count,
                         :share_count, :data_source, :sync_status, CURRENT_TIMESTAMP)
                    """,
                    {**payload, "content_id": content_id},
                )
                content = fetch_content(connection, content_id)
            self.send_json(content, HTTPStatus.CREATED)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_error_json(str(error), HTTPStatus.BAD_REQUEST)
        except sqlite3.IntegrityError:
            self.send_error_json("内容链接已存在，不能重复录入", HTTPStatus.BAD_REQUEST)

    def sync_content(self, path):
        parts = path.strip("/").split("/")
        if len(parts) != 4 or parts[:2] != ["api", "contents"] or parts[3] != "sync":
            self.send_error_json("同步接口不存在", HTTPStatus.NOT_FOUND)
            return
        try:
            content_id = int(parts[2])
        except ValueError:
            self.send_error_json("内容 ID 不正确", HTTPStatus.BAD_REQUEST)
            return

        with get_connection() as connection:
            content = fetch_content(connection, content_id)
            if content is None:
                self.send_error_json("内容不存在", HTTPStatus.NOT_FOUND)
                return

        started_source = "网页解析"
        try:
            scraped_metrics = scrape_content_metrics(content)
            merged_metrics = {
                key: scraped_metrics.get(key, content.get(key, 0))
                for key in METRIC_FIELDS
            }
            merged_metrics["view_count"] = content.get("view_count", 0)
            merged_metrics["share_count"] = content.get("share_count", 0)
            with get_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO content_metrics
                        (content_id, view_count, like_count, comment_count, collect_count,
                         share_count, data_source, sync_status, last_sync_at, failed_reason,
                         updated_at)
                    VALUES
                        (:content_id, :view_count, :like_count, :comment_count, :collect_count,
                         :share_count, :data_source, '同步成功', CURRENT_TIMESTAMP, '',
                         CURRENT_TIMESTAMP)
                    ON CONFLICT(content_id) DO UPDATE SET
                        view_count = excluded.view_count,
                        like_count = excluded.like_count,
                        comment_count = excluded.comment_count,
                        collect_count = excluded.collect_count,
                        share_count = excluded.share_count,
                        data_source = excluded.data_source,
                        sync_status = '同步成功',
                        last_sync_at = CURRENT_TIMESTAMP,
                        failed_reason = '',
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    {
                        "content_id": content_id,
                        "data_source": started_source,
                        **merged_metrics,
                    },
                )
                connection.execute(
                    """
                    INSERT INTO sync_logs
                        (content_id, source, status, finished_at, raw_summary)
                    VALUES
                        (?, ?, '成功', CURRENT_TIMESTAMP, ?)
                    """,
                    (content_id, started_source, json.dumps(scraped_metrics, ensure_ascii=False)),
                )
                synced_content = fetch_content(connection, content_id)
            self.send_json(
                {
                    "message": "同步成功",
                    "metrics": scraped_metrics,
                    "content": synced_content,
                }
            )
        except Exception as error:
            failed_reason = str(error) or "同步失败"
            with get_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO content_metrics
                        (content_id, view_count, like_count, comment_count, collect_count,
                         share_count, data_source, sync_status, last_sync_at, failed_reason,
                         updated_at)
                    VALUES
                        (?, ?, ?, ?, ?, ?, ?, '同步失败', CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(content_id) DO UPDATE SET
                        data_source = excluded.data_source,
                        sync_status = '同步失败',
                        last_sync_at = CURRENT_TIMESTAMP,
                        failed_reason = excluded.failed_reason,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        content_id,
                        content.get("view_count", 0),
                        content.get("like_count", 0),
                        content.get("comment_count", 0),
                        content.get("collect_count", 0),
                        content.get("share_count", 0),
                        started_source,
                        failed_reason,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO sync_logs
                        (content_id, source, status, finished_at, error_message)
                    VALUES
                        (?, ?, '失败', CURRENT_TIMESTAMP, ?)
                    """,
                    (content_id, started_source, failed_reason),
                )
                failed_content = fetch_content(connection, content_id)
            self.send_json(
                {
                    "message": failed_reason,
                    "content": failed_content,
                },
                HTTPStatus.BAD_REQUEST,
            )

    def update_content(self, path):
        content_id = self.extract_id(path)
        if content_id is None:
            self.send_error_json("内容 ID 不正确", HTTPStatus.BAD_REQUEST)
            return

        try:
            with get_connection() as connection:
                if fetch_content(connection, content_id) is None:
                    self.send_error_json("内容不存在", HTTPStatus.NOT_FOUND)
                    return
                payload = normalize_content_payload(parse_json_body(self), connection)
                if content_identity_exists(connection, payload, content_id):
                    raise ValueError("内容链接已存在，不能重复录入")

                update_payload = {**payload, "id": content_id}
                connection.execute(
                    """
                    UPDATE contents
                    SET
                        title = :title,
                        influencer_id = :influencer_id,
                        project_id = :project_id,
                        platform = :platform,
                        content_url = :content_url,
                        canonical_url = :canonical_url,
                        platform_content_id = :platform_content_id,
                        published_at = :published_at,
                        content_type = :content_type,
                        owner = :owner,
                        status = :status,
                        remark = :remark,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """,
                    update_payload,
                )
                connection.execute(
                    """
                    INSERT INTO content_metrics
                        (content_id, view_count, like_count, comment_count, collect_count,
                         share_count, data_source, sync_status, updated_at)
                    VALUES
                        (:id, :view_count, :like_count, :comment_count, :collect_count,
                         :share_count, :data_source, :sync_status, CURRENT_TIMESTAMP)
                    ON CONFLICT(content_id) DO UPDATE SET
                        view_count = excluded.view_count,
                        like_count = excluded.like_count,
                        comment_count = excluded.comment_count,
                        collect_count = excluded.collect_count,
                        share_count = excluded.share_count,
                        data_source = excluded.data_source,
                        sync_status = excluded.sync_status,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    update_payload,
                )
                content = fetch_content(connection, content_id)
            self.send_json(content)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_error_json(str(error), HTTPStatus.BAD_REQUEST)
        except sqlite3.IntegrityError:
            self.send_error_json("内容链接已存在，不能重复录入", HTTPStatus.BAD_REQUEST)

    def extract_id(self, path):
        parts = path.strip("/").split("/")
        if len(parts) != 3:
            return None
        try:
            return int(parts[2])
        except ValueError:
            return None

    def log_message(self, format, *args):
        print(f"[HTTP] {self.address_string()} - {format % args}")


if __name__ == "__main__":
    initialize_database()
    server = ThreadingHTTPServer((HOST, PORT), TalentPlatformHandler)
    print(f"达人运营平台已启动：http://{HOST}:{PORT}")
    print("按 Ctrl+C 停止服务")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")
    finally:
        server.server_close()
