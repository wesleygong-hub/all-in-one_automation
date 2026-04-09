# All-in-One Automation

一个基于 Playwright 的浏览器自动化基座项目，用于承载可复用的企业业务自动化 flow。当前已完成第一轮重构起步，包含可运行的 `archive-upload` 档案上传 flow，以及可继续扩展的 CLI / executor 基础结构。

## 当前定位

这个仓库是原 DSN 档案上传工具的架构演进版。

当前范围：
- 通用浏览器自动化基础能力
- 面向 flow 的 CLI 入口
- 可运行的 `archive-upload` 档案上传 flow
- SQLite 留痕、失败截图、CSV 回写、批次报告输出

后续计划：
- 继续把通用浏览器动作沉淀到自动化基座中
- 将档案上传能力补齐到完全替代旧版 v0.1 的程度
- 逐步接入新的业务 flow，例如报销单自动填写

## 仓库结构

- `automation/`：可复用的浏览器自动化基座
- `config/`：各个 flow 的运行配置
- `docs/`：架构与迁移说明
- `dsn_uploader/`：迁移阶段的兼容层
- `flows/`：具体业务 flow
- `samples/`：样例任务文件
- `main.py`：CLI 入口

## 环境准备

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

如果 Playwright 自带 Chromium 不可用，项目会优先尝试本机 Edge / Chrome。

## 快速开始

### 1. 准备账号环境变量

PowerShell：

```powershell
$env:DSN_USERNAME = "你的用户名"
$env:DSN_PASSWORD = "你的密码"
```

### 2. 准备任务文件

先以样例文件为模板：

```powershell
Copy-Item .\samples\archive_tasks.sample.csv .\task.csv
```

然后按你的真实业务数据和本地文件路径更新 `task.csv`。

### 3. 校验任务文件

```powershell
python .\main.py validate archive-upload --config .\config\archive_upload.yaml --tasks .\task.csv
```

### 4. 执行档案上传 flow

```powershell
python .\main.py run archive-upload --config .\config\archive_upload.yaml --tasks .\task.csv --headed
```

### 5. 查看批次报告

```powershell
python .\main.py report --config .\config\archive_upload.yaml
```

## 输出内容

运行产物默认写入：
- `./data/runtime.db`
- `./output/screenshots/`
- `./output/reports/`

任务执行结果会回写到 `task.csv` 的 `G` 列 `upload_result`。

## 说明

- `config/config.yaml.example` 和 `config/archive_upload.yaml` 是新架构下的主要配置文件。
- 根目录的 `config.yaml` 以及 `dsn_uploader/` 中的部分代码目前仍属于迁移阶段的兼容实现。
- 这个仓库的长期目标是演进为“浏览器自动化基座 + 多业务 flow”的统一平台。