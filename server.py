import json
import sqlite3
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse


ROOT = Path(__file__).parent
PUBLIC_DIR = ROOT / "public"
DATABASE_PATH = ROOT / "data" / "talent_platform.db"
HOST = "127.0.0.1"
PORT = 8000


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
]


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
                        "https://example.com/xiaolu",
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
                        "https://example.com/achuan",
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
                        "https://example.com/digital",
                        "数码",
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
    for key in [
        "view_count",
        "like_count",
        "comment_count",
        "collect_count",
        "share_count",
    ]:
        result[key] = int(result.get(key) or 0)
    result["interaction_count"] = (
        result["like_count"]
        + result["comment_count"]
        + result["collect_count"]
        + result["share_count"]
    )
    return result


def parse_json_body(handler):
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length <= 0 or content_length > 100_000:
        raise ValueError("请求内容为空或过大")
    return json.loads(handler.rfile.read(content_length))


def clean_text(payload, key, default=""):
    return str(payload.get(key, default) or "").strip()


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
    category = clean_text(payload, "category")
    status = clean_text(payload, "status", "正常") or "正常"

    if not name:
        raise ValueError("达人名称不能为空")
    if not platform:
        raise ValueError("媒体平台不能为空")
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
        "profile_url": clean_text(payload, "profile_url"),
        "category": category,
        "followers_count": followers_count,
        "wechat": clean_text(payload, "wechat"),
        "phone": clean_text(payload, "phone"),
        "email": clean_text(payload, "email"),
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


class TalentPlatformHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()

    def send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message, status=HTTPStatus.BAD_REQUEST):
        self.send_json({"message": message}, status)

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/dashboard/summary":
            with get_connection() as connection:
                summary = get_dashboard_summary(connection)
            self.send_json(summary)
            return

        if path == "/api/influencers":
            params = parse_qs(parsed_url.query)
            keyword = (params.get("keyword", [""])[0] or "").strip()
            platform = (params.get("platform", [""])[0] or "").strip()

            where = []
            values = []
            if keyword:
                where.append("name LIKE ?")
                values.append(f"%{keyword}%")
            if platform:
                where.append("platform = ?")
                values.append(platform)

            fields = ", ".join(INFLUENCER_FIELDS)
            sql = f"SELECT {fields} FROM influencers"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY updated_at DESC, id DESC"

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

            where = []
            values = []
            if keyword:
                where.append("(name LIKE ? OR project_code LIKE ?)")
                values.extend([f"%{keyword}%", f"%{keyword}%"])
            if status:
                where.append("status = ?")
                values.append(status)

            fields = ", ".join(PROJECT_FIELDS)
            sql = f"SELECT {fields} FROM projects"
            if where:
                sql += " WHERE " + " AND ".join(where)
            sql += " ORDER BY updated_at DESC, id DESC"

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

            where = []
            values = []
            if keyword:
                where.append("(c.title LIKE ? OR c.content_url LIKE ? OR i.name LIKE ?)")
                values.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
            if platform:
                where.append("c.platform = ?")
                values.append(platform)

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
            sql += " ORDER BY c.published_at DESC, c.updated_at DESC, c.id DESC"

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

        if path == "/":
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
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

    def do_PUT(self):
        path = urlparse(self.path).path
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
