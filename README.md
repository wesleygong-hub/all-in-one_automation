# DSN 档案上传 CLI 【POC】

## 安装

```powershell
pip install -r requirements.txt
python -m playwright install chromium
```

## 准备配置

1. 复制 `config.yaml.example` 为 `config.yaml`
2. 复制 `task.sample.csv` 为 `task.csv`
3. 设置环境变量

PowerShell:

```powershell
$env:DSN_USERNAME = "你的用户名"
$env:DSN_PASSWORD = "你的密码"
```

如果通过 `.bat` 启动:

```bat
@echo off
set DSN_USERNAME=your_username
set DSN_PASSWORD=your_password
python main.py run --config .\config.yaml --tasks .\task.csv --headed
pause
```

如果通过 PowerShell 脚本启动:

```powershell
$ErrorActionPreference = "Stop"
$env:DSN_USERNAME = "your_username"
$env:DSN_PASSWORD = "your_password"
python .\main.py run --config .\config.yaml --tasks .\task.csv --headed
```

如果 Playwright 自带 Chromium 没有安装好，程序会优先尝试本机 `Microsoft Edge`。也可以在 `config.yaml` 中显式指定：

```yaml
system:
  browser_channel: "msedge"
  browser_executable_path: ""
```

## 命令

校验任务清单:

```powershell
python main.py validate --config .\config.yaml --tasks .\task.csv
```

执行上传:

```powershell
python main.py run --config .\config.yaml --tasks .\task.csv --headed
```

查看执行报告:

```powershell
python main.py report --config .\config.yaml
```

## 输出

- SQLite: `./data/runtime.db`
- 失败截图: `./output/screenshots/`
- 批次报告: `./output/reports/`
