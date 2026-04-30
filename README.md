# All-in-One Automation

一个基于 Playwright 的浏览器自动化基座项目，用于承载可复用的企业业务自动化 flow。

当前版本已经完成“浏览器自动化基座 + 档案材料上传业务 flow + 报销单自动填报 flow”的阶段性收敛，主运行链路已经稳定落在：

- `automation/`：通用浏览器自动化基座
- `flows/archive_upload/`：档案材料上传业务 flow
- `flows/reimbursement_fill/`：报销单自动填报业务 flow
- `main.py` + `automation/cli.py`：统一 CLI 入口

## 当前定位

这个仓库是原 DSN 档案上传工具的架构演进版，目标是演进为：

`浏览器自动化基座 + 多业务自动化 flow`

当前已经进入“主体能力可用、主流程稳定可回归”的阶段，适合作为后续业务扩展和版本迭代的统一载体。

## 当前已稳定支持

### 1. 自动化基座能力

- 批次级浏览器会话复用
- 基于配置的选择器与页面上下文管理
- 多 iframe / 多上下文场景下的页面定位与切换
- SQLite 运行留痕
- 任务结果回写
- 失败截图输出
- 运行日志与批次报告输出

### 2. 档案上传 flow

当前已经稳定支持以下主链路：

- 登录外部系统
- 进入档案上传页面
- 选择人员
- 选择所属业务与业务类型
- 上传文件
- 提交并确认
- 回列表页做结果校验

### 3. 报销单自动填报 flow

当前已经稳定支持以下主链路：

- 进入“我要报账”页面
- 新建报销单据
- 打开电子影像并上传附件
- 识别电子发票
- 检测重复发票并中止异常任务
- 填写报销单表头字段
- 按不同单据类型切换内部 tab 后填写明细
- 保存单据
- 失败场景下关闭电子影像、关闭报销单据并回到列表

当前已重点稳定的单据类型包括：

- `市内交通费报销`
- `业务招待费报销`

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

### 1. 档案上传 flow

#### 1.1 准备账号环境变量

PowerShell：

```powershell
$env:DSN_USERNAME = "你的用户名"
$env:DSN_PASSWORD = "你的密码"
```

说明：

- `archive-upload` flow 使用 `DSN_USERNAME` 与 `DSN_PASSWORD`
- `config/archive_upload.yaml` 默认从这两个环境变量读取账号密码

#### 1.2 准备任务文件

先以样例文件为模板：

```powershell
New-Item -ItemType Directory -Path .\runtime\archive_upload -Force | Out-Null
Copy-Item .\samples\archive_tasks.sample.csv .\runtime\archive_upload\task.csv
```

然后按真实业务数据更新 `runtime/archive_upload/task.csv`，并把本地附件放到 `runtime/archive_upload/file/`。

#### 1.3 校验任务文件

```powershell
python .\main.py validate archive-upload --config .\config\archive_upload.yaml --tasks .\runtime\archive_upload\task.csv
```

#### 1.4 执行档案上传

```powershell
python .\main.py run archive-upload --config .\config\archive_upload.yaml --tasks .\runtime\archive_upload\task.csv --headed
```

#### 1.5 查看批次报告

```powershell
python .\main.py report --config .\config\archive_upload.yaml
```

说明：

- `report` 命令本质读取的是 `sqlite_path` 指向的批次数据
- 只要配置文件中的 `paths.sqlite_path` 指向同一个运行库，使用 `archive_upload.yaml` 或 `reimbursement_fill.yaml` 都可以查看同一份批次汇总

### 2. 报销单自动填报 flow

#### 2.1 准备账号环境变量

如果使用环境变量方式提供报销系统账号，PowerShell 可以这样设置：

```powershell
$env:IAM_USERNAME = "你的用户名"
$env:IAM_PASSWORD = "你的密码"
```

说明：

- `reimbursement-fill` flow 使用 `IAM_USERNAME` 与 `IAM_PASSWORD`
- `config/reimbursement_fill.yaml` 默认从这两个环境变量读取账号密码
- `config/reimbursement_fill.local.yaml` 可用于本地覆盖配置
- 如果 `reimbursement_fill.local.yaml` 中已经直接填写了账号密码，则不需要再额外设置环境变量

#### 2.2 准备任务文件

当前报销单 flow 默认使用 Excel 任务清单：

```powershell
New-Item -ItemType Directory -Path .\runtime\reimbursement_fill -Force | Out-Null
```

任务文件路径：

- `runtime/reimbursement_fill/task.xlsx`

本地待上传附件目录：

- `runtime/reimbursement_fill/file/`

任务文件结构要求：

- 必须包含 `task` sheet
- 必须包含 `invoice` sheet
- `validate reimbursement-fill` 会校验这两个 sheet 的字段完整性

#### 2.3 校验任务文件

```powershell
python .\main.py validate reimbursement-fill --config .\config\reimbursement_fill.yaml --tasks .\runtime\reimbursement_fill\task.xlsx
```

#### 2.4 执行报销单自动填报

```powershell
python .\main.py run reimbursement-fill --config .\config\reimbursement_fill.local.yaml --tasks .\runtime\reimbursement_fill\task.xlsx --headed
```

补充说明：

- 如果你希望严格走环境变量注入账号，使用 `config/reimbursement_fill.yaml`
- 如果你希望使用本地覆盖配置，使用 `config/reimbursement_fill.local.yaml`

### 3. 执行入口自检

```powershell
python .\main.py selfcheck
```

## 输出内容

运行产物默认写入：

- `./data/runtime.db`
- `./output/screenshots/`
- `./output/logs/`

其中：

- 运行日志：`./output/logs/<时间戳>.log`
- 批次报告：`./output/logs/<batch_id>_report.log`
- 失败截图：`./output/screenshots/yyyyymmdd_hhmmss_任务编号.png`

任务执行结果会回写到任务文件中：

- 档案上传：回写 `runtime/archive_upload/task.csv`
- 报销单自动填报：回写 `runtime/reimbursement_fill/task.xlsx`

补充说明：

- `report` 命令读取的是 SQLite 中的批次汇总数据
- 运行日志与批次报告文件都会同步写入 `output/logs`
- 报销单失败截图会优先保留报错当下的浏览器界面
- 终端里看到的运行日志会同步写入对应的 `.log` 文件

## v0.5.0 更新内容

本版完成报销单自动化基座能力沉淀收尾，重点不是继续扩展报销业务逻辑，而是把已经验证过的通用执行策略、失败收口、等待模型和诊断能力沉淀到 `automation/`。

### 1. Runtime 执行策略基座

- 新增 `automation/runtime/steps.py`
- `run_task_substep` 支持默认快失败、快重试
- 支持 `retry_attempts` 与 `non_retryable_exceptions`
- retry 耗尽时统一输出 `FAILED ... retries_exhausted`
- 明确异常不误重试，例如重复发票会直接进入业务异常处理

### 2. 任务失败收口基座

- 新增 `automation/runtime/failures.py`
- 新增 `handle_task_failure`
- 统一处理未预期失败后的截图、失败截图路径缓存、失败清场和降级日志
- 截图失败或清场失败不会覆盖最初导致任务失败的异常

### 3. Core 通用能力增强

- 新增 `automation/core/diagnostics.py`
- 新增 `AttemptLog`，统一 attempts 诊断格式
- 新增 `poll_until`，收口短轮询等待模型
- 新增 `click_with_fallbacks`，统一普通点击、force 点击、JS 点击三段式兜底
- 将新增能力导出到 `automation/core/__init__.py`

### 4. 报销 flow 接入基座

- 发票识别完成检测接入 `run_task_substep`
- 重复发票异常通过 `non_retryable_exceptions` 直通，不参与误重试
- 未预期任务失败接入 `handle_task_failure`
- 上传发票快速检测接入 `poll_until`
- 上传发票失败诊断接入 `AttemptLog`

### 5. SQLite 与忽略规则清理

- 删除现有 `runtime.db` 中无业务用途的 `_dsn_healthcheck` 表
- SQLite 写入探测改为通用瞬时表 `__sqlite_write_check`，不再残留业务命名表
- fallback 临时目录从历史业务名改为 `automation_sqlite`
- `.gitignore` 中的 `runtime/` 改为 `/runtime/`，避免误忽略 `automation/runtime/steps.py`

### 6. 文档基线更新

- 重整 `doc/报销单自动化基座能力沉淀说明.md`
- 文档从历史流水账整理为当前版本基座能力总览
- 明确哪些能力已进入 `automation/`，哪些报销业务能力继续留在 `flows/reimbursement_fill/`

## 相关文档

- [报销单自动化基座能力沉淀说明](./doc/报销单自动化基座能力沉淀说明.md)

## 说明

- 当前主运行配置包括：
  - `config/archive_upload.yaml`
  - `config/reimbursement_fill.yaml`
  - `config/reimbursement_fill.local.yaml`
- 当前主业务实现位于：
  - `flows/archive_upload/flow.py`
  - `flows/reimbursement_fill/flow.py`
- 当前通用自动化能力位于 `automation/`
- 这个仓库的长期目标是继续在现有基座之上承载更多业务 flow，而不是回到“单业务专用脚本”模式
