@echo off
chcp 65001 > nul
title AI Model Stüdyosu

echo.
echo ╔════════════════════════════════════════╗
echo ║   🤖 AI Model Stüdyosu Başlatılıyor   ║
echo ╔════════════════════════════════════════╝
echo.

REM Python kontrolü
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python bulunamadı!
    echo.
    echo Python kurmanız gerekiyor:
    echo   https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo ✓ Python bulundu
python --version
echo.

REM Virtual environment kontrolü
if not exist "env\Scripts\activate.bat" (
    echo 📦 Virtual environment oluşturuluyor...
    python -m venv env
    if errorlevel 1 (
        echo ❌ Virtual environment oluşturulamadı!
        pause
        exit /b 1
    )
    echo ✓ Virtual environment oluşturuldu
    echo.
)

REM Virtual environment aktivasyonu
echo 🔄 Virtual environment aktive ediliyor...
call env\Scripts\activate.bat
echo.

REM Requirements kontrolü
echo 📋 Bağımlılıklar kontrol ediliyor...
python -c "import customtkinter" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️  Gerekli paketler yüklü değil!
    echo 📦 Paketler yükleniyor...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ❌ Paket yüklemesi başarısız!
        echo.
        pause
        exit /b 1
    )
    echo.
    echo ✓ Tüm paketler yüklendi
    echo.
) else (
    echo ✓ Bağımlılıklar tamam
    echo.
)

REM Ollama kontrolü
echo 🦙 Ollama kontrol ediliyor...
ollama --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Ollama bulunamadı
    echo.
    echo Ollama kurmaniz onerilir - opsiyonel
    echo   https//ollama.com/download
    echo.
) else (
    echo ✓ Ollama bulundu
    ollama --version
    echo.
)

REM Uygulamayı başlat
echo ════════════════════════════════════════
echo 🚀 Uygulama başlatılıyor...
echo ════════════════════════════════════════
echo.

python main.py

REM Hata kontrolü
if errorlevel 1 (
    echo.
    echo ════════════════════════════════════════
    echo ❌ Uygulama hata ile sonlandı!
    echo ════════════════════════════════════════
    echo.
    pause
    exit /b 1
)

echo.
echo Pencereyi kapatabilirsiniz.
pause
