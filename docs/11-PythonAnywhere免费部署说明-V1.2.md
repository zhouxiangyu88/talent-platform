# PythonAnywhere 免费部署说明 V1.2

更新时间：2026-06-23

## 1. 为什么选择 PythonAnywhere

因为当前希望使用不需要海外卡的免费方案。PythonAnywhere 免费账号适合先部署这个 Python + SQLite 小平台，用于内部试用和演示。

当前方案：

- 代码：GitHub 仓库
- 运行：PythonAnywhere Web App
- 数据：SQLite 文件保存在 PythonAnywhere 私有文件空间
- 登录：站内账号密码 + 邀请码注册

## 2. 你需要准备

- PythonAnywhere 账号
- GitHub 仓库地址：

```text
https://github.com/zhouxiangyu88/talent-platform
```

- 一个正式邀请码，例如公司内部自定义一串不容易猜到的字符。

## 3. PythonAnywhere 操作步骤

### 3.1 注册或登录

打开：

```text
https://www.pythonanywhere.com/
```

注册免费账号并登录。

### 3.2 打开 Bash 控制台

进入 Dashboard 后：

```text
Consoles → Bash
```

在控制台执行：

```bash
git clone https://github.com/zhouxiangyu88/talent-platform.git
```

### 3.3 创建 Web App

进入：

```text
Web → Add a new web app
```

选择：

```text
Manual configuration
Python 3.10 或 Python 3.11
```

### 3.4 配置源码目录

在 Web App 页面设置：

```text
Source code: /home/你的用户名/talent-platform
Working directory: /home/你的用户名/talent-platform
```

### 3.5 配置 WSGI 文件

点击 WSGI configuration file，替换为：

```python
import sys

project_home = "/home/你的用户名/talent-platform"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from wsgi import application
```

把 `你的用户名` 换成你的 PythonAnywhere 用户名。

### 3.6 配置静态文件

在 Static files 中新增：

```text
URL: /static/
Directory: /home/你的用户名/talent-platform/public/
```

当前项目页面仍然可以通过 WSGI 访问静态资源；这个配置主要是为后续优化预留。

### 3.7 设置环境变量

PythonAnywhere 免费版的环境变量配置能力有限。第一版可以先使用默认邀请码：

```text
talent2026
```

如果要修改邀请码，可以在 `server.py` 中临时修改 `DEFAULT_INVITE_CODE`，后续再升级为更安全的配置方式。

### 3.8 Reload

回到 Web 页面，点击：

```text
Reload
```

然后访问：

```text
https://你的用户名.pythonanywhere.com/
```

应该会先进入登录页。

## 4. 第一次上线后

1. 打开线上地址。
2. 点击注册。
3. 输入邀请码注册你的第一个账号。
4. 登录后测试达人库、项目库、内容库。
5. 确认数据能正常保存。
6. 再把链接发给其他人。

## 5. 注意事项

- 免费版适合试用和小范围内部测试。
- SQLite 文件会保存在 PythonAnywhere 私有文件空间中。
- 不要把正式邀请码发到公开地方。
- 如果后续多人同时频繁使用，建议升级到 PostgreSQL 或更正式的云部署。
- 小红书同步仍然是网页解析试点，可能因页面风控或结构变化失败。
