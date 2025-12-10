#!/bin/bash

# Renkli çıktı için
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "╔════════════════════════════════════════╗"
echo "║   🤖 AI Model Stüdyosu Başlatılıyor   ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 bulunamadı!${NC}"
    echo ""
    echo "Python3 kurmanız gerekiyor:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
    echo "  macOS: brew install python3"
    echo "  Fedora: sudo dnf install python3 python3-pip"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Python bulundu${NC}"
python3 --version
echo ""

# Virtual environment kontrolü
if [ ! -d "env" ]; then
    echo -e "${BLUE}📦 Virtual environment oluşturuluyor...${NC}"
    python3 -m venv env
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Virtual environment oluşturulamadı!${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Virtual environment oluşturuldu${NC}"
    echo ""
fi

# Virtual environment aktivasyonu
echo -e "${BLUE}🔄 Virtual environment aktive ediliyor...${NC}"
source env/bin/activate
echo ""

# Requirements kontrolü
echo -e "${BLUE}📋 Bağımlılıklar kontrol ediliyor...${NC}"
python -c "import customtkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Gerekli paketler yüklü değil!${NC}"
    echo -e "${BLUE}📦 Paketler yükleniyor...${NC}"
    echo ""
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo ""
        echo -e "${RED}❌ Paket yüklemesi başarısız!${NC}"
        echo ""
        exit 1
    fi
    echo ""
    echo -e "${GREEN}✓ Tüm paketler yüklendi${NC}"
    echo ""
else
    echo -e "${GREEN}✓ Bağımlılıklar tamam${NC}"
    echo ""
fi

# Ollama kontrolü
echo -e "${BLUE}🦙 Ollama kontrol ediliyor...${NC}"
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama bulunamadı${NC}"
    echo ""
    echo "Ollama kurmaniz onerilir - opsiyonel"
    echo "  Linux: curl -fsSL https//ollama.com/install.sh | sh"
    echo "  macOS: brew install ollama"
    echo "  Web: https//ollama.com/download"
    echo ""
else
    echo -e "${GREEN}✓ Ollama bulundu${NC}"
    ollama --version
    echo ""
fi

# Uygulamayı başlat
echo "════════════════════════════════════════"
echo -e "${GREEN}🚀 Uygulama başlatılıyor...${NC}"
echo "════════════════════════════════════════"
echo ""

python main.py

# Hata kontrolü
if [ $? -ne 0 ]; then
    echo ""
    echo "════════════════════════════════════════"
    echo -e "${RED}❌ Uygulama hata ile sonlandı!${NC}"
    echo "════════════════════════════════════════"
    echo ""
    exit 1
fi

echo ""
echo -e "${GREEN}✓ Uygulama kapandı${NC}"
