@echo off
echo =========================
echo Start data uploading...
echo =========================
set DSN_USERNAME=your_username
set DSN_PASSWORD=your_password
python main.py run --config .\config.yaml --tasks .\task.csv --headed
echo.
echo Execution complete. Please check the results log.
