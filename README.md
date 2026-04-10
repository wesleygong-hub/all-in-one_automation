# All-in-One Automation

一个基于 Playwright 的浏览器自动化基座项目，用于承载可复用的企业业务自动化 flow。

当前版本已经完成“浏览器自动化基座 + 档案材料上传业务 flow”的第一阶段收敛，主运行链路已经稳定落在：

- `automation/`：通用浏览器自动化基座
- `flows/archive_upload/`：档案材料上传业务 flow
- `main.py` + `automation/cli.py`：统一 CLI 入口

## 当前定位

这个仓库是原 DSN 档案上传工具的架构演进版，目标是演进为：

`浏览器自动化基座 + 多业务自动化 flow`

当前已稳定支持：

- 批次级浏览器会话复用
- 登录外部系统
- 进入档案上传页面
- 选择人员
- 选择所属业务与业务类型
- 上传文件
- 提交并确认
- 回列表页做结果校验
- SQLite 留痕、失败截图、CSV 回写、批次报告输出

后续规划：

- 继续清理迁移期遗留文件与目录
- 收口配置与文档口径
- 基于当前基座接入新的业务 flow，例如报销单自动填写

## 当前仓库结构

- `automation/`：可复用的浏览器自动化基座
- `flows/`：具体业务 flow
- `config/`：各 flow 的运行配置
- `samples/`：样例任务文件与启动脚本
- `runtime/`：本地真实任务清单与附件
- `doc/`：中文业务与重构文档
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
New-Item -ItemType Directory -Path .\runtime\archive_upload -Force | Out-Null
Copy-Item .\samples\archive_tasks.sample.csv .\runtime\archive_upload\task.csv
```

然后按你的真实业务数据更新 `runtime/archive_upload/task.csv`，并把本地附件放到 `runtime/archive_upload/file/`。

### 3. 校验任务文件

```powershell
python .\main.py validate archive-upload --config .\config\archive_upload.yaml --tasks .\runtime\archive_upload\task.csv
```

### 4. 执行档案上传 flow

```powershell
python .\main.py run archive-upload --config .\config\archive_upload.yaml --tasks .\runtime\archive_upload\task.csv --headed
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

任务执行结果会回写到 `runtime/archive_upload/task.csv` 的 `G` 列 `upload_result`。

## 说明

- 当前主运行配置是 `config/archive_upload.yaml`。
- 当前主业务实现位于 `flows/archive_upload/flow.py`。
- 当前通用自动化能力位于 `automation/`。
- 这个仓库的长期目标是继续在现有基座之上承载更多业务 flow，而不是回到“单业务专用脚本”模式。
