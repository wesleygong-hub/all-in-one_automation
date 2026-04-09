# Web自动化新仓库重构设计文档

## 1. 文档目的

本文档用于指导新仓库 `all-in-one_automation` 的第一阶段架构重构与后续持续迭代。

本文档聚焦以下目标：

- 明确新仓库的定位
- 定义新仓库目录结构
- 制定旧仓库到新仓库的迁移计划
- 明确第一轮与第二轮迭代目标
- 给出第一轮重构任务拆解表

本文档的用途不是替代 PRD，而是作为后续代码重构时的工程设计依据。

---

## 2. 重构背景

当前旧仓库已经具备一个可运行的 `v0.1 CLI POC`，能够完成：

- 登录外部系统
- 进入档案上传页面
- 选择人员
- 选择业务信息
- 上传文件
- 提交并确认
- 回列表页做结果校验
- 写 SQLite、日志、截图和 `task.csv`

但当前旧仓库的结构仍然偏“单业务专用工具”：

- 自动化基础能力和业务流程耦合较深
- `workflow.py` 承担了过多职责
- 后续如果扩展“报销系统自动填写报销单”等新业务，复用成本较高

因此，需要在新仓库中进行一次结构性重构，将项目演进为：

- 一个可复用的 Web 自动化底座
- 承载多个具体业务 flow
- 当前优先承载：
  - 档案上传
  - 报销单自动填写

---

## 3. 新仓库目标定位

新仓库 `all-in-one_automation` 的定位如下：

- 一个基于 Playwright 的通用 Web 自动化 CLI 平台
- 支持多个业务流程共用同一套浏览器自动化底座
- 支持配置化页面 selector、任务清单、批次运行、结果留痕

不再把项目定义为“档案上传专用脚本”，而是定义为：

`浏览器自动化底座 + 多业务自动化 flow`

---

## 4. 重构原则

整个重构过程遵循以下原则：

### 4.1 先跑通，再抽象

优先保证新架构下的档案上传主链路重新可跑，再逐步提高抽象层次。

### 4.2 先搬运，再优化

第一轮重构优先迁移旧能力，不追求一步到位的完美设计。

### 4.3 保留旧仓库稳定版本

旧仓库继续作为稳定交付版使用，新仓库作为架构演进版推进。

### 4.4 一次只解决一层问题

避免在同一轮同时做：

- 大规模目录调整
- 业务流程重写
- 新业务接入
- 测试体系重建

### 4.5 让新仓库先承接旧业务，再扩展新业务

先让档案上传 flow 在新底座上跑通，再接入报销单 flow。

---

## 5. 新仓库目录设计

建议新仓库 `all-in-one_automation` 采用如下结构：

```text
all-in-one_automation/
├─ main.py
├─ README.md
├─ requirements.txt
├─ .gitignore
├─ config/
│  ├─ config.yaml.example
│  ├─ archive_upload.yaml
│  └─ reimbursement.yaml
├─ docs/
│  ├─ architecture.md
│  ├─ migration-plan.md
│  ├─ refactor-design.md
│  └─ flows/
│     ├─ archive-upload.md
│     └─ reimbursement.md
├─ scripts/
│  ├─ run_archive.ps1
│  └─ run_reimbursement.ps1
├─ samples/
│  ├─ archive_tasks.sample.csv
│  └─ reimbursement_tasks.sample.csv
├─ automation/
│  ├─ __init__.py
│  ├─ browser/
│  │  ├─ session.py
│  │  └─ context.py
│  ├─ core/
│  │  ├─ actions.py
│  │  ├─ waits.py
│  │  ├─ selectors.py
│  │  ├─ state.py
│  │  └─ errors.py
│  ├─ runtime/
│  │  ├─ executor.py
│  │  ├─ logger.py
│  │  ├─ screenshots.py
│  │  └─ results.py
│  ├─ storage/
│  │  ├─ db.py
│  │  └─ task_writer.py
│  └─ config/
│     ├─ loader.py
│     └─ models.py
├─ flows/
│  ├─ __init__.py
│  ├─ archive_upload/
│  │  ├─ flow.py
│  │  ├─ task_loader.py
│  │  ├─ task_model.py
│  │  └─ selectors.py
│  └─ reimbursement/
│     ├─ flow.py
│     ├─ task_loader.py
│     ├─ task_model.py
│     └─ selectors.py
└─ tests/
   ├─ unit/
   └─ smoke/
```

---

## 6. 各层职责说明

### 6.1 根目录

- `main.py`
  - CLI 主入口
- `requirements.txt`
  - 依赖清单
- `.gitignore`
  - 本地配置、运行产物、样例文件忽略规则

### 6.2 `config/`

放运行配置文件，不与代码混杂。

- `config.yaml.example`
  - 公共模板
- `archive_upload.yaml`
  - 档案上传 flow 配置
- `reimbursement.yaml`
  - 报销 flow 配置

### 6.3 `docs/`

放架构、迁移和各业务说明。

### 6.4 `scripts/`

放真实使用者启动脚本。

### 6.5 `samples/`

放脱敏后的任务样例。

### 6.6 `automation/`

放通用浏览器自动化底座。

这部分不应直接写死某一业务流程。

### 6.7 `flows/`

放具体业务自动化流程。

每个业务 flow 自己管理：

- 任务模型
- 任务加载
- selector 默认值
- 业务流程编排

### 6.8 `tests/`

后续用于补充单元测试和 smoke test。

第一轮可先保留空结构。

---

## 7. 旧仓库到新仓库的迁移计划

### 7.1 总体迁移路径

推荐迁移路径如下：

1. 复制旧仓库当前可用代码到新仓库
2. 建立新目录结构
3. 先迁底层公共能力
4. 再迁档案上传 flow
5. 新 CLI 跑通档案上传
6. 再进行第二轮补齐
7. 最后接入报销单 flow

### 7.2 优先迁移的公共能力

从旧仓库中优先抽出的底层能力包括：

- 浏览器启动和会话管理
- 页面元素点击、输入、等待
- 下拉选择
- 文件上传
- 弹窗处理
- 页面状态判断
- 任务执行日志
- 截图
- SQLite 留痕
- 结果回写 CSV

### 7.3 档案上传 flow 的迁移策略

不建议直接重写档案上传流程，而应：

1. 先保留旧逻辑的执行顺序
2. 逐步替换为调用新底座 API
3. 让 `archive_upload.flow` 成为新架构下的第一个真实 flow

### 7.4 报销 flow 的接入策略

报销单自动填写不应在第一轮重构中直接接入。

正确顺序是：

1. 先让新底座承接档案上传
2. 再基于同一底座接入报销 flow

---

## 8. 第一轮迭代目标定义

### 8.1 目标关键词

`跑通 + 架构落位 + 可继续扩展`

### 8.2 目标说明

第一轮重构的目的不是一步达到旧仓库完全体，而是：

- 在新仓库中建立“通用自动化底座 + 档案上传 flow”的第一版结构
- 让档案上传流程在新结构上重新跑通
- 验证新底座能承载真实浏览器自动化任务
- 为后续接入报销单 flow 提供骨架

### 8.3 第一轮必须达成

- 新目录结构建立完成
- 通用浏览器自动化能力已抽到基础层
- 档案上传 flow 已迁移到新底座
- 新 CLI 能调用 `archive-upload` flow
- 单任务可跑通
- 小批量任务可跑通
- 批次只登录一次
- 任务结果可写 SQLite
- 任务结果可写回 CSV
- README 和样例配置可以指导运行

### 8.4 第一轮允许暂时不完全对齐旧版的部分

- 某些 selector 兜底逻辑可以先简化
- 某些等待和刷新时序可以先做到可运行
- 某些异常处理可以先不做到旧版那么细
- 浏览器保持打开、自动打开结果文件等体验细节可以先弱化
- 多任务长批次稳定性不要求一开始就完全等同旧版

### 8.5 第一轮验收标准

新仓库在“档案上传”上达到旧仓库 `v0.1` 的基本可用水平。

即：

- 主流程可跑
- 结构清晰
- 可以继续扩展

---

## 9. 第二轮迭代目标定义

### 9.1 目标关键词

`补齐稳定性 + 完整替代旧版 + 准备承接新业务`

### 9.2 目标说明

第二轮迭代的目的，是在第一轮架构落位之后，把档案上传能力补齐到旧仓库 `v0.1` 的完全可用水平。

届时，新仓库应能真正接替旧仓库成为主维护版本。

### 9.3 第二轮必须补齐

- selector 稳定性补齐
- 旧版已有等待和兜底策略补齐
- 页面状态收敛能力补齐
- 结果校验稳定性补齐
- CSV 回写体验补齐
- SQLite 和截图留痕行为补齐
- 批次结束收尾体验补齐
- 多条任务连续运行稳定性补齐

### 9.4 第二轮验收标准

新仓库在“档案上传”上达到旧仓库 `v0.1` 的完全可用水平。

即：

- 旧仓库当前能稳定完成的能力
- 新仓库都能稳定完成

完成第二轮后，旧仓库可以进入：

- 只读维护
- 或停止继续增强

---

## 10. 第一轮重构任务拆解表

### 阶段 1：建立新骨架

1. 创建新目录结构
- 新建 `automation/`
- 新建 `flows/archive_upload/`
- 新建 `config/`
- 新建 `samples/`
- 新建 `docs/`

2. 放置基础文件
- 保留 `main.py`
- 迁移 `requirements.txt`
- 建立新的 `.gitignore`
- 建立 `config/config.yaml.example`
- 建立 `samples/archive_tasks.sample.csv`

验收标准：

- 新仓库目录结构完整
- 基础模块可正常 import

### 阶段 2：迁移底层公共能力

3. 迁移配置加载层
- 从旧仓库迁移配置读取逻辑
- 落到 `automation/config/loader.py`

4. 迁移基础模型
- 提取配置模型、结果模型、执行结果结构

5. 迁移浏览器启动层
- 迁移浏览器启动和本机浏览器优先逻辑
- 落到 `automation/browser/session.py`

验收标准：

- 最小脚本可成功启动浏览器并打开页面

### 阶段 3：迁移通用页面操作能力

6. 抽 `actions.py`
- 点击
- 输入
- 文件上传
- 下拉选择

7. 抽 `waits.py`
- 元素等待
- URL 等待
- 弹窗等待
- 列表刷新等待

8. 抽 `state.py`
- 判断当前页面是否为登录页、列表页、上传页

9. 抽 `errors.py`
- 定义清晰的自动化异常

验收标准：

- 旧 `workflow.py` 中一半以上通用动作已可由底座提供

### 阶段 4：迁移运行时能力

10. 迁移日志层
- 迁移终端输出和日志格式控制

11. 迁移 SQLite 层
- 迁移任务记录和步骤日志
- 保留 Windows SQLite 兜底逻辑

12. 迁移结果回写
- 将 CSV 回写逻辑迁出

13. 抽执行器
- 批次开始
- 逐任务调度
- 截图
- 写 SQLite
- 写结果文件
- 输出总结

验收标准：

- 逐任务执行控制不再依赖单一业务实现

### 阶段 5：迁移档案上传 flow

14. 建 `flows/archive_upload/task_model.py`
- 定义档案上传任务结构

15. 建 `flows/archive_upload/task_loader.py`
- 迁移档案任务读取逻辑

16. 建 `flows/archive_upload/selectors.py`
- 放档案上传 selector 默认值

17. 建 `flows/archive_upload/flow.py`
- 迁移档案上传业务编排
- 底层统一调用 `automation/` 能力

验收标准：

- 档案上传 flow 已从旧仓库结构中解耦出来

### 阶段 6：重做 CLI 接口

18. 重构 `main.py`
- 改为 flow 导向入口

19. 新建统一 CLI
- 支持类似：

```powershell
python main.py validate archive-upload --config .\config\archive_upload.yaml --tasks .\task.csv
python main.py run archive-upload --config .\config\archive_upload.yaml --tasks .\task.csv --headed
```

20. 接入执行器和 flow
- `cli -> executor -> archive_upload.flow`

验收标准：

- 新 CLI 下单任务可跑通

### 阶段 7：验证与回归

21. 单任务回归
- 登录
- 上传
- 校验
- 回写

22. 小批量回归
- 同批次只登录一次
- 多条连续运行不串扰

23. 文档同步
- README
- 架构说明
- 配置样例

验收标准：

- 新仓库在“档案上传”上达到旧仓库 `v0.1` 的基本可用水平

---

## 11. 第一轮明确不做

第一轮不纳入范围：

- 报销单 flow
- 插件化 flow 注册
- 并发任务
- 完整测试体系
- GUI / Web 前端
- 多账号轮转

---

## 12. 推荐执行顺序

建议实际执行顺序如下：

1. 建立新骨架
2. 迁移底层公共能力
3. 迁移通用页面操作
4. 迁移档案上传 flow
5. 迁移运行时能力
6. 重做 CLI
7. 回归验证

理由：

- 尽早让新底座承接真实 flow
- 避免先做太多抽象却没有业务落地

---

## 13. 后续整体演进路线

### 阶段一

完成第一轮重构：

- 新底座落位
- 档案上传 flow 跑通

### 阶段二

完成第二轮补齐：

- 达到旧版完全替代水平

### 阶段三

接入 `reimbursement` flow：

- 登录报销系统
- 自动填写报销单
- 复用同一底座

### 阶段四

继续演进为统一自动化平台：

- 多 flow 共存
- 更强配置化
- 更清晰执行器

---

## 14. 一句话理解整个计划

这个重构计划的核心不是“把旧代码搬到新目录”，而是：

`先搭出可复用自动化底座 -> 先用档案上传验证底座 -> 再让新仓库完整接班旧版 -> 最后承接报销单等新业务`

