@echo off
echo =========================
echo Start data uploading...
echo =========================
set DSN_USERNAME=your_username
set DSN_PASSWORD=your_password
python main.py run archive-upload --config .\config\archive_upload.yaml --tasks .\runtime\archive_upload\task.csv --headed
echo.
echo Execution complete. Please check the results log.
