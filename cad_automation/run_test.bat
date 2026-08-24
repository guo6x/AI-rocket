@echo off
echo ========================================================
echo Project Ad Astra: Cast Sword Bureau (NX Node)
echo Testing NXOpen Python Environment
echo ========================================================

if "%UGII_BASE_DIR%"=="" (
    echo [ERROR] UGII_BASE_DIR environment variable is not set.
    echo Please ensure NX 12.0 is installed correctly.
    pause
    exit /b 1
)

echo [INFO] Found NX Installation at: %UGII_BASE_DIR%
echo [INFO] Executing run_journal.exe with hello_nx.py ...

"%UGII_BASE_DIR%\NXBIN\run_journal.exe" "hello_nx.py"

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Journal execution failed with code %ERRORLEVEL%.
) else (
    echo [SUCCESS] Journal executed successfully! Check your NX session or folder for outputs.
)
pause
