@echo off
set SCRIPT_DIR=%~dp0
cd /d %SCRIPT_DIR%

echo ========================================================
echo Project Ad Astra: TVC Generation (Industrial Grade)
echo Targeting: 70mm EDF + SG92R Servos
echo ========================================================

if "%UGII_BASE_DIR%"=="" (
    echo [ERROR] UGII_BASE_DIR not found. Set it to your NX install path.
    exit /b 1
)

echo [RUNNING] Executing NX Journal: generate_tvc_nx.py...
"%UGII_BASE_DIR%\NXBIN\run_journal.exe" "generate_tvc_nx.py"

if %ERRORLEVEL% NEQ 0 (
    echo [FAIL] TVC generation failed. Check nx_debug.log.
) else (
    echo [DONE] TVC generated. Output: cad_automation\EDF70_TVC_Industrial.prt
)
