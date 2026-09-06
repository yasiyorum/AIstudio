# 🤖 AI Model Stüdyosu (v2.5 Modern & Restorasyonlu Sürüm)

Yerel (**Ollama**) ve bulut tabanlı (**OpenAI**, **Google Gemini**, **Anthropic Claude**) yapay zeka modelleriyle çalışan, modern ve modüler bir AI geliştirme platformu.

Kullanıcı dostu masaüstü arayüzü (`CustomTkinter`) sayesinde teknik kodlama gerektirmeden **5 farklı model oluşturma stratejisini**, gerçek zamanlı **token streaming sohbeti**, **RAG doküman yönetimini** ve **otomatik ayar kalıcılığını** tek çatı altında sunar.

---

## ✨ Temel Özellikler

### 🎓 5 Model Oluşturma Stratejisi

1. **📚 Bilgi Bankası (RAG)**
   - Vektör veritabanı tabanlı (`ChromaDB` + `all-MiniLM-L6-v2`)
   - Büyük dosyalarla çalışır, GPU gerektirmez (CPU dostu)
   - PDF, DOCX, TXT, Excel, **CSV, JSON ve JSONL** desteği
   - Model içerisindeki dokümanları tek tek inceleme ve silme desteği

2. **🚀 Taşınabilir Model (Ollama Modelfile)**
   - Doküman içeriğini doğrudan Ollama sistem istemine gömer
   - Farklı bilgisayarlara taşınabilir, GPU gerektirmez
   - Ollama ile yerel olarak tek komutla çalışır

3. **🧠 Beyin Modeli (Talimat Tabanlı)**
   - Dosyasız veya opsiyonel dosyalarla çalışır
   - Özel asistan kişiliği, uzmanlık alanı ve davranış kuralları tanımlar

4. **🔬 Gerçek Eğitim (Fine-Tuning)**
   - Model ağırlıklarını kalıcı olarak eğitir
   - LoRA (PEFT) ve Unsloth kütüphanesi ile yüksek verim
   - Eğitim sonunda GGUF formatına dönüştürüp doğrudan Ollama'ya aktarma

5. **🧪 Sıfırdan Eğitim (Scratch GPT-2)**
   - Hazır ağırlık kullanmadan sıfırdan BPE Tokenizer ve GPT-2 mimarisi eğitir
   - Deneysel modelleme ve yapay zeka eğitimi süreçlerini öğrenmek için idealdir

---

### 💬 Gelişmiş Sohbet Deneyimi

- **⚡ Canlı Token Streaming:** Yanıtlar harf harf ekrana akar (ChatGPT / Claude akıcılığında).
- **⏹ Yanıtı Durdurma:** Model yanıt üretirken tek tıkla üretimi kesebilme imkanı.
- **💻 Zengin Kod Blokları:** Yanıttaki kod parçacıkları (` ```python ` vb.) özel kutularda gösterilir ve bağımsız "Kopyala" butonuna sahiptir.
- **📜 Akıllı Oturum Geçmişi:** Konuşmalar model bazlı olarak zaman damgalı JSON dosyalarında saklanır; geçmiş sohbetler kolayca yüklenip silinebilir.
- **🔍 Tıklanabilir Kaynaklar:** RAG bilgi bankası ile yapılan sohbetlerde yanıtın dayandığı kaynak dosyalar gösterilir.

---

### 🤖 Çoklu AI Motoru Desteği

- **Ollama (Yerel & Ücretsiz):** `llama3`, `deepseek-r1`, `qwen2.5`, `mistral`, `phi3` vb.
- **OpenAI:** `gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo` (RAG destekli veya bağımsız sohbet)
- **Google AI:** `gemini-1.5-flash`, `gemini-pro`
- **Anthropic:** `claude-3-haiku`, `claude-3-5-sonnet`

---

### ⚙️ Kalıcı Ayar ve Sistem Yönetimi

- **Otomatik Kalıcılık (`config.json`):** Seçilen AI sağlayıcısı, API anahtarları ve model tercihleri oturumlar arasında güvenle saklanır.
- **Dönen Loglama (`app.log`):** Tüm sistem olayları seviyeli (INFO, WARNING, ERROR) olarak hem terminale hem de log dosyasına yazılır.
- **Birim Testleri (`tests/test_core.py`):** Çekirdek modülleri doğrulayan otomatik test paketi.

---

## 📁 Proje Mimarisi

```
AI studio/
├── main.py                    # Uygulama ana giriş noktası
├── run.bat                    # Windows otomatik başlatıcı
├── run.sh                     # Linux/macOS otomatik başlatıcı
├── requirements.txt           # Python bağımlılıkları
│
├── backend/                   # Arka plan iş mantığı & AI motoru
│   ├── __init__.py
│   ├── chat_engine.py         # Sohbet motoru, streaming & hafıza yönetimi
│   ├── model_manager.py       # 5 model stratejisi, RAG & doküman yönetimi
│   ├── config_manager.py      # Thread-safe kalıcı ayar yöneticisi
│   └── logger.py              # Merkezi loglama altyapısı
│
├── ui/                        # Grafik kullanıcı arayüzü (CustomTkinter)
│   ├── __init__.py
│   ├── app_ui.py              # Ana pencere ve sayfa denetleyicileri
│   ├── theme.py               # Modern karanlık tema renkleri & tipografi
│   └── widgets.py             # ChatBubble, TypingIndicator, LoadingOverlay
│
├── tests/                     # Birim testleri
│   └── test_core.py           # Otomatik unittest paketi
│
├── models_db/                 # RAG ChromaDB vektör veritabanları
├── chat_history/              # Sohbet geçmişi JSON dosyaları
└── data_storage/              # config.json ve app.log deposu
```

---

## 🚀 Kurulum

### 1. Gereksinimler
- **Python 3.9+** (Python 3.10, 3.11 veya 3.12 önerilir)
- **Ollama** (Yerel modeller için ücretsiz): [ollama.com/download](https://ollama.com/download)

### 2. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

*(İsteğe bağlı: Fine-tuning kullanacaksanız PyTorch ve Unsloth paketlerini yükleyin.)*

### 3. Çalıştırın

**Windows:**
```cmd
run.bat
```

**Linux / macOS:**
```bash
chmod +x run.sh
./run.sh
```

**Doğrudan Python ile:**
```bash
python main.py
```

---

## 🧪 Testleri Çalıştırma

Projenin çekirdek bileşenlerini test etmek için:

```bash
python -m unittest tests/test_core.py
```

---

## 📖 Kullanım Kılavuzu

### 1. RAG Modeli Oluşturma ve Yönetme
1. **Modellerim** sayfasına gidin.
2. Strateji olarak **📚 Bilgi Bankası** seçin.
3. Model ismi girin ve dokümanlarınızı (PDF, Word, Excel, CSV, JSON, TXT) seçin.
4. **Modeli Oluştur** butonuna tıklayın.
5. Oluşturulan modelin dokümanlarını incelemek veya tekil dosyaları silmek için sayfanın altındaki **"📚 Bilgi Bankası (RAG) Doküman Yöneticisi"** kartını kullanın.

### 2. Sohbet ve Canlı Streaming
1. **Sohbet** sayfasına gidin.
2. Üstteki menüden bir model seçin.
3. Sorunuzu yazın ve **Gönder ➤** butonuna basın.
4. Yanıt canlı olarak akarken istediğiniz an **⏹ Durdur** butonuna basarak üretimi sonlandırabilirsiniz.
5. Kod bloklarını sağ üstteki **Kopyala** butonuyla anında panoya kopyalayabilirsiniz.

### 3. Ayarlar
- AI motorunu **Ollama**, **OpenAI**, **Google AI** veya **Anthropic** olarak belirleyin.
- Bulut modelleri için API anahtarınızı girip **💾 Ayarları Kaydet** butonuna tıklayın.

---

## 📝 Lisans

MIT License © 2026 AI Model Stüdyosu
