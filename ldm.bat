@echo off
chcp 65001 >nul 2>&1
title Shop Dien Thoai - Development Script

setlocal enabledelayedexpansion
cd /d "%~dp0"

set "PYTHON_EXE="
set "PYTHON_VERSION="
set "PY_MAJOR="
set "PY_MINOR="
set "TARGET_PYTHON_MINOR=8"
set "TARGET_PYTHON_DISPLAY=3.8"
set "IMPORTANT_PKGS=django django-allauth requests openpyxl python-dotenv"
set "VENV_DIR=.venv"

:: Tạo thư mục logs nếu chưa tồn tại
if not exist "logs" mkdir logs 2>nul

:: ========================================
:: Tự động xin quyền Admin nếu chưa có
:: ========================================
net session >nul 2>&1
if errorlevel 1 (
    echo [i] Đang yêu cầu quyền Administrator...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d \"%~dp0\" && \"%~f0\" %*' -Verb RunAs" >nul 2>&1
    exit /b
)

:main_menu
cls
echo ╔════════════════════════════════════════╗
echo ║       Shop Dien Thoai - Menu         ║
echo ╠════════════════════════════════════════╣
echo ║                                        ║
echo ║  [0] Setup Full Tự Động                ║
echo ║  ─────────────────────────────────     ║
echo ║  [1] Khởi động Server (Local)          ║
echo ║  [2] Khởi động Server (Production)     ║
echo ║  [3] Tạo Migration mới                ║
echo ║  [4] Chạy Migration                   ║
echo ║                                        ║
echo ║  [Q] Thoát                             ║
echo ║                                        ║
echo ╚════════════════════════════════════════╝
echo.
set /p choice="Chọn chức năng [0-4, Q]: "

if /i "%choice%"=="0" goto setup_full_auto
if /i "%choice%"=="1" goto start_server_local
if /i "%choice%"=="2" goto start_server_prod
if /i "%choice%"=="3" goto make_migration
if /i "%choice%"=="4" goto run_migration
if /i "%choice%"=="Q" goto exit_script

echo.
echo [!] Lựa chọn không hợp lệ!
timeout /t 2 >nul
goto main_menu


:detect_python
py -%TARGET_PYTHON_DISPLAY% --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py -%TARGET_PYTHON_DISPLAY%"
    goto detect_python_version
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    goto detect_python_version
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py -3"
    goto detect_python_version
)

set "PYTHON_EXE="
goto :eof

:detect_python_version
for /f "tokens=*" %%v in ('%PYTHON_EXE% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2^>nul') do set "PYTHON_VERSION=%%v"
for /f "tokens=*" %%v in ('%PYTHON_EXE% -c "import sys; print(sys.version_info.major)" 2^>nul') do set "PY_MAJOR=%%v"
for /f "tokens=*" %%v in ('%PYTHON_EXE% -c "import sys; print(sys.version_info.minor)" 2^>nul') do set "PY_MINOR=%%v"

if not "%PY_MAJOR%"=="3" (
    set "PYTHON_EXE="
    set "PYTHON_VERSION="
    set "PY_MAJOR="
    set "PY_MINOR="
    goto :eof
)

if not defined PY_MINOR (
    set "PYTHON_EXE="
    set "PYTHON_VERSION="
    set "PY_MAJOR="
    set "PY_MINOR="
    goto :eof
)

if %PY_MINOR% LSS 8 (
    set "PYTHON_EXE="
    set "PYTHON_VERSION="
    set "PY_MAJOR="
    set "PY_MINOR="
)
goto :eof


:activate_venv
:: Thử .venv trước, rồi venv
if exist "%VENV_DIR%\Scripts\activate.bat" (
    call %VENV_DIR%\Scripts\activate.bat >nul 2>&1
    if errorlevel 1 goto activate_venv_fail
    exit /b 0
)
if exist "venv\Scripts\activate.bat" (
    set "VENV_DIR=venv"
    call venv\Scripts\activate.bat >nul 2>&1
    if errorlevel 1 goto activate_venv_fail
    exit /b 0
)
echo [!] Không tìm thấy venv! Hãy chạy [0] Setup Full trước.
exit /b 1

:activate_venv_fail
echo [!] Không thể kích hoạt Virtual Environment.
echo     Venv có thể bị lỗi. Chạy [0] Setup Full để tạo lại.
exit /b 1


:verify_package
set "PKG_NAME=%~1"
python -c "import importlib, sys; importlib.import_module('%PKG_NAME%')" >nul 2>&1
if errorlevel 1 (
    echo    [THIẾU] %PKG_NAME%
    set /a MISSING_COUNT+=1
) else (
    echo    [OK] %PKG_NAME%
)
goto :eof


:start_server_local
cls
echo ==========================================
echo   Khởi Động Server (Chạy Local)
echo ==========================================
echo.
echo [i] Đang cấu hình biến môi trường cho Local...
echo     - DEBUG=True
echo     - ALLOWED_HOSTS=127.0.0.1, localhost
echo.
set "DEBUG=True"
set "ALLOWED_HOSTS=127.0.0.1,localhost,*"
set "VNPAY_RETURN_URL=http://127.0.0.1:8000/vnpay/return/"
set "VNPAY_IPN_URL=http://127.0.0.1:8000/vnpay/ipn/"
set "MOMO_RETURN_URL=http://127.0.0.1:8000/momo/return/"
set "MOMO_IPN_URL=http://127.0.0.1:8000/momo/ipn/"
goto start_server_common

:start_server_prod
cls
echo ==========================================
echo   Khởi Động Server (Production)
echo ==========================================
echo.
echo [i] Đang sử dụng cấu hình gốc từ file .env...
set "DEBUG=False"
goto start_server_common

:start_server_common
call :activate_venv
if errorlevel 1 (
    echo.
    echo [!] Không thể kích hoạt Virtual Environment!
    echo    Đảm bảo thư mục venv tồn tại.
    timeout /t 3 >nul
    goto main_menu
)

echo.
echo [i] Kiểm tra database...
python manage.py migrate --run-syncdb 2>nul

echo.
echo [OK] Database sẵn sàng!
echo.
if "%DEBUG%"=="True" (
    echo [i] Đang khởi động server LOCAL tại http://127.0.0.1:8000/
) else (
    echo [i] Đang khởi động server PRODUCTION theo cấu hình .env
)
echo [i] Bấm Ctrl+C để dừng server
echo.
python manage.py runserver
echo.
echo [i] Server đã dừng.
pause
goto main_menu


:make_migration
cls
echo ==========================================
echo   Tạo Migration Mới
echo ==========================================
echo.
call :activate_venv
if errorlevel 1 (
    timeout /t 3 >nul
    goto main_menu
)

set /p app_name="Nhập tên app (vd: store): "

echo.
echo [i] Đang tạo migration cho %app_name%...
python manage.py makemigrations %app_name%

if errorlevel 1 (
    echo.
    echo [THẤT BẠI] Tạo migration thất bại!
) else (
    echo.
    echo [OK] Migration đã được tạo!
)

echo.
pause
goto main_menu


:run_migration
cls
echo ==========================================
echo   Chạy Database Migration
echo ==========================================
echo.
call :activate_venv
if errorlevel 1 (
    timeout /t 3 >nul
    goto main_menu
)

echo [i] Đang chạy migration...
python manage.py migrate --run-syncdb

if errorlevel 1 (
    echo.
    echo [THẤT BẠI] Migration gặp lỗi!
) else (
    echo.
    echo [OK] Migration hoàn tất!
)

echo.
pause
goto main_menu


:setup_full_auto
cls
echo ╔════════════════════════════════════════╗
echo ║   SETUP FULL TỰ ĐỘNG - Shop Dien Thoai ║
echo ╠════════════════════════════════════════╣
echo ║                                        ║
echo ║  Script sẽ tự động:                    ║
echo ║  1. Kiểm tra Python                    ║
echo ║  2. Xóa venv lỗi + tạo venv mới        ║
echo ║  3. Cài tất cả thư viện                ║
echo ║  4. Chạy database migration            ║
echo ║  5. Kiểm tra .env                      ║
echo ║                                        ║
echo ║  Không cần thao tác thêm - chờ xong!   ║
echo ║                                        ║
echo ╚════════════════════════════════════════╝
echo.

set "MISSING_COUNT=0"
set "SETUP_ERRORS=0"

:: ──── BƯỚC 1: Kiểm tra Python ────
echo ────────────────────────────────────────
echo  [1/6] Kiểm tra Python...
echo ────────────────────────────────────────
call :detect_python
if "%PYTHON_EXE%"=="" (
    echo.
    echo  [THẤT BẠI] Không tìm thấy Python phù hợp!
    echo.
    echo  Vui lòng cài Python 3.8+ từ:
    echo     https://www.python.org/downloads/
    echo.
    echo  QUAN TRỌNG: Khi cài, tick Add Python to PATH
    echo.
    echo  Sau khi cài xong, đóng cửa sổ này va chay lai bat.
    echo.
    pause
    goto main_menu
)
for /f "tokens=*" %%v in ('%PYTHON_EXE% --version 2^>^&1') do echo  Phien ban: %%v
echo  [OK] Python hop le!
if not "%PY_MINOR%"=="%TARGET_PYTHON_MINOR%" (
    echo  [CANH BAO] May dang dung Python %PYTHON_VERSION%.
    echo           Khuyen nghi dung Python %TARGET_PYTHON_DISPLAY% de on dinh nhat.
)
echo.

:: ──── BƯỚC 2: Kiểm tra + Tạo venv ────
echo ────────────────────────────────────────
echo  [2/6] Kiem tra Virtual Environment...
echo ────────────────────────────────────────

set "VENV_NEED_CREATE=0"

:: Kiểm tra venv có tồn tại không
if not exist "%VENV_DIR%\Scripts\python.exe" (
    if not exist "venv\Scripts\python.exe" (
        echo  [i] Chua co venv - se tao moi.
        set "VENV_NEED_CREATE=1"
    ) else (
        set "VENV_DIR=venv"
    )
)

:: Kiểm tra venv có bị lỗi không
if "%VENV_NEED_CREATE%"=="0" (
    %VENV_DIR%\Scripts\python.exe --version >nul 2>&1
    if errorlevel 1 (
        echo  [!] Venv bi loi (Python path khong khop may hien tai)
        echo      Day la loi pho bien khi copy project giua cac may.
        echo      Dang xoa venv cu va tao lai...
        set "VENV_NEED_CREATE=1"
    ) else (
        echo  [OK] Venv hoat dong binh thuong.
    )
)

:: Tạo venv mới nếu cần
if "%VENV_NEED_CREATE%"=="1" (
    echo.
    echo  [i] Dang don dep venv cu...
    if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%" >nul 2>&1
    if exist "venv" rmdir /s /q "venv" >nul 2>&1
    set "VENV_DIR=.venv"
    echo  [i] Dang tao venv moi bang %PYTHON_EXE%...
    %PYTHON_EXE% -m venv %VENV_DIR% >nul 2>&1
    if errorlevel 1 (
        echo  [THAT BAI] Khong the tao venv!
        echo             Thu chay thu cong: %PYTHON_EXE% -m venv .venv
        set /a SETUP_ERRORS+=1
        pause
        goto main_menu
    )
    echo  [OK] Da tao venv moi tai %VENV_DIR%\
)
echo.

:: ──── BƯỚC 3: Kích hoạt venv + nâng cấp pip ────
echo ────────────────────────────────────────
echo  [3/6] Kich hoat venv + nang cap pip...
echo ────────────────────────────────────────
call :activate_venv
if errorlevel 1 (
    set /a SETUP_ERRORS+=1
    pause
    goto main_menu
)
python -m pip install --upgrade pip setuptools wheel --quiet --disable-pip-version-check --no-warn-script-location
if errorlevel 1 (
    echo  [CANH BAO] Khong the cap nhat pip - tiep tuc cai thu vien.
) else (
    echo  [OK] pip/setuptools/wheel da duoc cap nhat.
)
echo.

:: ──── BƯỚC 4: Cài thư viện ────
echo ────────────────────────────────────────
echo  [4/6] Cai dat thu vien...
echo ────────────────────────────────────────
echo.

:: 4a: Core requirements
if not exist "requirements.txt" (
    echo  [THAT BAI] Khong tim thay requirements.txt
    set /a SETUP_ERRORS+=1
    pause
    goto main_menu
)

echo  [i] Dang cai core packages (requirements.txt)...
pip install -r requirements.txt --disable-pip-version-check --no-warn-script-location
if errorlevel 1 (
    echo.
    echo  [THAT BAI] Cai dat core requirements gap loi!
    echo  Kiem tra ket noi mang roi chay lai [0].
    set /a SETUP_ERRORS+=1
) else (
    echo  [OK] Core packages da cai xong.
)
echo.

:: 4b: Packages bổ sung thường thiếu
echo  [i] Dang cai packages bo sung (Pillow, PyJWT, cryptography)...
pip install Pillow PyJWT cryptography --disable-pip-version-check --no-warn-script-location --quiet
if errorlevel 1 (
    echo  [CANH BAO] Mot so package bo sung cai loi.
) else (
    echo  [OK] Packages bo sung da cai xong.
)
echo.

:: 4c: Kiểm tra packages quan trọng
echo  [i] Kiem tra nhanh packages quan trọng...
for %%p in (%IMPORTANT_PKGS%) do call :verify_package %%p

echo.
if "%MISSING_COUNT%"=="0" (
    echo  [OK] Tat ca packages deu san sang!
) else (
    echo  [CANH BAO] Con %MISSING_COUNT% package chua import duoc.
)
echo.

:: ──── BƯỚC 5: Database migration ────
echo ────────────────────────────────────────
echo  [5/6] Chay database migration...
echo ────────────────────────────────────────
echo.
python manage.py migrate --run-syncdb
if errorlevel 1 (
    echo.
    echo  [CANH BAO] Migration gap van de - co the can cau hinh .env truoc.
    set /a SETUP_ERRORS+=1
) else (
    echo.
    echo  [OK] Database san sang.
)
echo.

:: ──── BƯỚC 6: Kiểm tra .env ────
echo ────────────────────────────────────────
echo  [6/6] Kiem tra file .env...
echo ────────────────────────────────────────
echo.
if not exist ".env" (
    if not exist ".env.local" (
        if not exist ".env.production" (
            echo  [CANH BAO] Chua co file .env!
            echo.
            echo  Tao file .env.local trong thu muc goc voi noi dung toi thieu:
            echo.
            echo    DEBUG=True
            echo    SECRET_KEY=your-secret-key-change-this
            echo    ALLOWED_HOSTS=127.0.0.1,localhost
            echo.
            echo  Xem day du trong README.md hoac .env.example
        ) else (
            echo  [OK] File .env.production da co san.
        )
    ) else (
        echo  [OK] File .env.local da co san.
    )
) else (
    echo  [OK] File .env da co san.
)
echo.

:: ──── TỔNG KẾT ────
echo.
if "%SETUP_ERRORS%"=="0" (
    echo ╔════════════════════════════════════════╗
    echo ║   SETUP HOAN TAT THANH CONG!           ║
    echo ╠════════════════════════════════════════╣
    echo ║                                        ║
    echo ║  Buoc tiep theo:                       ║
    echo ║    Chon [1] de khoi dong server        ║
    echo ║    Truy cap: http://127.0.0.1:8000/   ║
    echo ║                                        ║
    echo ╚════════════════════════════════════════╝
) else (
    echo ╔════════════════════════════════════════╗
    echo ║   HOAN TAT (co %SETUP_ERRORS% canh bao)║
    echo ╠════════════════════════════════════════╣
    echo ║                                        ║
    echo ║  Co mot so loi nho, kiem tra lai:     ║
    echo ║    - File .env da tao chua?            ║
    echo ║    - Ket noi Internet on khong?        ║
    echo ║    - Thu chay lai [0] sau khi fix      ║
    echo ║                                        ║
    echo ╚════════════════════════════════════════╝
)
echo.
pause
goto main_menu


:exit_script
cls
echo ╔════════════════════════════════════════╗
echo ║           Cam on da su dung!            ║
echo ╚════════════════════════════════════════╝
echo.
timeout /t 2 >nul
exit /b 0
