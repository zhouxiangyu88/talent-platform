# 达人运营平台

这是一个用于学习全栈开发和 vibe coding 的达人运营平台 MVP。

当前版本已经完成第一版核心闭环：

- 登录注册：账号密码登录、邀请码注册、退出登录
- 达人库：新增、编辑、搜索、筛选、详情、同平台同名防重复
- 项目库：新增、编辑、搜索、筛选、详情、项目编号防重复
- 内容库：新增、编辑、搜索、筛选、详情
- 内容关联：一条内容必须关联一个达人，可选关联一个项目
- 数据回收：播放、点赞、评论、收藏、转发
- 链接治理：保存原始链接、标准链接、平台内容 ID，并做防重复
- 首页仪表盘：达人、项目、内容、播放、互动、近期内容、平台分布、同步状态

## 启动项目

项目暂时只使用 macOS 自带的 Python 3 和 SQLite，不需要安装第三方依赖。

```bash
python3 server.py
```

然后在浏览器访问：

```text
http://127.0.0.1:8000
```

注意：不要直接打开 `public/index.html`。这个项目需要通过后端服务访问，否则页面样式、接口和数据库都无法正常工作。

按 `Ctrl+C` 停止服务。

## 登录注册

平台已增加轻量登录能力：

- `/login.html`：登录
- `/register.html`：邀请码注册
- `/api/auth/logout`：退出登录

本地默认邀请码：

```text
talent2026
```

上线时建议通过环境变量设置正式邀请码：

```bash
INVITE_CODE=你的正式邀请码
```

## 数据保存在哪里

本地数据保存在：

```text
data/talent_platform.db
```

也可以通过环境变量指定数据库路径：

```bash
DATABASE_PATH=/var/data/talent_platform.db
```

`data/` 目录已加入 `.gitignore`，不会提交到 GitHub。这样可以避免把本地测试数据、业务数据误上传。

## 部署到 Render

项目已提供 `render.yaml`，适合先部署到 Render 试用。

推荐配置：

- Web Service：Python
- Start Command：`python3 server.py`
- Health Check Path：`/healthz`
- Persistent Disk：挂载到 `/var/data`
- `DATABASE_PATH`：`/var/data/talent_platform.db`
- `HOST`：`0.0.0.0`
- `INVITE_CODE`：在 Render 后台手动填写正式邀请码

上线前注意：

- 必须配置持久化磁盘，否则云服务重启后 SQLite 数据可能丢失。
- 不要把正式邀请码写进 GitHub。
- 第一次上线后，先用邀请码注册自己的账号，再把链接发给其他人。

## 免费部署方案：PythonAnywhere

如果没有海外卡，可以优先使用 PythonAnywhere 免费方案。

项目已新增：

```text
wsgi.py
```

用于适配 PythonAnywhere 的 WSGI Web App。

详细步骤见：

```text
docs/11-PythonAnywhere免费部署说明-V1.2.md
```

## 项目结构

```text
.
├── server.py          # 后端：HTTP 服务、API、SQLite 数据库操作
├── public/
│   ├── index.html     # 前端：页面结构
│   ├── styles.css     # 前端：视觉样式
│   └── app.js         # 前端：交互逻辑和 API 请求
├── docs/              # PRD、交互、UI、数据库、技术方案、开发计划
├── data/              # 本地 SQLite 数据库，已忽略，不提交
└── README.md          # 项目说明
```

## 当前核心业务对象

### 达人

达人以“达人名称 + 媒体平台”作为唯一规则。

同一个达人在不同平台可以是不同记录，例如：

- 某达人 / 小红书
- 某达人 / 抖音

### 项目

项目是独立资料库，内容可以关联项目，也可以不关联项目。

项目编号如果填写，需要唯一。

### 内容

内容必须是发布后录入，因为需要内容链接。

内容规则：

- 必须关联一个达人
- 可以选择关联一个项目
- 内容链接不能重复
- 平台会根据达人自动带出
- 数据回收字段包括播放、点赞、评论、收藏、转发

## 链接防重复规则

系统保存内容时会生成三类链接信息：

- `content_url`：用户原始粘贴链接
- `canonical_url`：清洗后的标准链接
- `platform_content_id`：平台内容 ID，例如小红书 `/explore/{id}` 里的 `{id}`

防重复会同时检查：

- 原始链接
- 标准链接
- 同平台内容 ID

这样可以减少 PC 链接、移动端链接、分享参数不同导致的重复录入。

短链跳转解析后续会在爬虫/API 同步阶段增强。

## 当前 API

```text
GET  /api/dashboard/summary

POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/me

GET  /api/influencers
POST /api/influencers
GET  /api/influencers/{id}
PUT  /api/influencers/{id}

GET  /api/projects
POST /api/projects
GET  /api/projects/{id}
PUT  /api/projects/{id}

GET  /api/contents
POST /api/contents
GET  /api/contents/{id}
PUT  /api/contents/{id}
```

## 学习重点

这个项目目前能帮助理解：

- 前端页面如何收集用户输入
- 前端如何通过 API 请求后端
- 后端如何校验数据和防重复
- 数据如何保存到 SQLite
- 多张表如何通过 ID 关联
- 多张表如何汇总成首页运营指标

核心链路：

```text
用户操作 -> JavaScript -> HTTP API -> Python 后端 -> SQLite 数据库 -> 页面展示
```

## 第一版版本说明

当前版本建议作为 GitHub 第一版：

```text
v1.0.0 - 达人运营平台 MVP
```

已完成：

- 首页仪表盘
- 达人库
- 项目库
- 内容库
- 内容数据回收
- 链接标准化防重复

后续可继续迭代：

- 内容库按项目筛选
- 达人报价字段
- 内容互动率
- 数据同步任务入口
- 爬虫/API 自动回收数据
- 登录和权限
- 部署到线上环境
