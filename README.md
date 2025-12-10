# 🤖 AI Model Stüdyosu

Modern yapay zeka modelleri oluşturun ve eğitin. RAG, Ollama Modelfile ve Fine-Tuning desteği ile güçlü AI asistanları yaratın.

## ✨ Özellikler

### 🎓 3 Model Oluşturma Stratejisi

1. **📚 Bilgi Bankası (RAG)**
   - Hızlı ve kolay
   - GPU gerektirmez
   - Büyük dosyalarla çalışır
   - Vektör veritabanı kullanır

2. **🚀 Taşınabilir Model (Ollama Modelfile)**
   - Orta boyut modeller
   - Başka bilgisayarlarda çalışır
   - Ollama ile entegre
   - GPU gerektirmez

3. **🔬 Gerçek Eğitim (Fine-Tuning)**
   - Model ağırlıklarını değiştirir
   - GPU/CPU/AMD/Apple Silicon desteği
   - LoRA ile verimli eğitim
   - Unsloth kütüphanesi kullanır

### 💬 Akıllı Sohbet Sistemi

- Sohbet geçmişi kaydedilir
- Geçmiş konuşmalara dönülebilir
- Model başına ayrı geçmiş
- Geçmiş sohbetleri silme

### 🤖 Çoklu AI Sağlayıcı

- **Ollama** (Yerel - Ücretsiz)
- **OpenAI** (GPT-4, GPT-3.5)
- **Google AI** (Gemini)
- **Anthropic** (Claude)

### 🎨 Modern Arayüz

- Karanlık tema
- Responsive tasarım
- Açılıp kapanan yan paneller
- Emoji'lerle zenginleştirilmiş

## 🚀 Kurulum

### 1. Gereksinimler

- Python 3.9+
- Ollama (yerel modeller için) - [ollama.com](https://ollama.com)

### 2. Bağımlılıkları Yükleyin

**Temel özellikler (RAG + Ollama Modelfile):**
```bash
pip install -r requirements.txt
```

**Fine-Tuning için ek paketler:**

NVIDIA GPU:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install transformers datasets trl
pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
```

AMD GPU (ROCm):
```bash
pip install torch --index-url https://download.pytorch.org/whl/rocm5.7
pip install transformers datasets trl
```

CPU veya Apple Silicon:
```bash
pip install torch transformers datasets trl
```

### 3. Çalıştırın

Windows:
```bash
run.bat
```

Veya doğrudan:
```bash
python main.py
```

## 📖 Kullanım

### RAG Modeli Oluşturma

1. **Modellerim** → **Bilgi Bankası** seçin
2. Model adı girin
3. PDF, DOCX, TXT, Excel dosyalarını seçin
4. **Modeli Oluştur** butonuna tıklayın
5. Saniyeler içinde hazır!

### Taşınabilir Model Oluşturma

1. **Modellerim** → **Taşınabilr Model** seçin
2. Baz model seçin (Ollama modellerinizden)
3. Dosyalarınızı seçin
4. Model oluşturulacak ve Ollama'ya eklenecek

### Fine-Tuning

1. **Modellerim** → **Gerçek Eğitim** seçin
2. Baz model seçin
3. Eğitim dosyalarını yükleyin
4. Eğitim başlayacak (GPU gerektirir)
5. Model otomatik kaydedilir

### Sohbet

1. **Sohbet** sayfasına gidin
2. Model seçin (dropdown menüden)
3. Mesajınızı yazın ve gönderin
4. Sol üstteki ☰ ile geçmiş sohbetleri açın

### Ayarlar

- **AI Motoru**: Ollama, OpenAI, Google veya Anthropic
- **RAG Modeli**: Hangi Ollama modelini kullanacak
- **Sohbet Geçmişi**: Klasörü aç veya sil

## 📁 Proje Yapısı

```
aiteacher/
├── main.py                 # Ana giriş noktası
├── run.bat                 # Windows başlatıcı
├── requirements.txt        # Bağımlılıklar
├── backend/
│   ├── model_manager.py   # Model oluşturma & yönetimi
│   └── chat_engine.py     # Sohbet motoru
├── ui/
│   └── app_ui.py          # Kullanıcı arayüzü
├── models_db/             # RAG modelleri (ChromaDB)
├── chat_history/          # Sohbet geçmişi (JSON)
└── finetune_output/       # Fine-tune edilmiş modeller
```

## 🛠️ Sistem Gereksinimleri

### Minimum (RAG & Ollama Modelfile)
- CPU: Herhangi bir modern işlemci
- RAM: 8GB
- Disk: 5GB

### Önerilen (Fine-Tuning ile)
- GPU: NVIDIA RTX 3060+ (8GB VRAM)
- RAM: 16GB
- Disk: 20GB

### Desteklenen GPU'lar
- ✅ NVIDIA (CUDA) - En hızlı
- ✅ AMD (ROCm) - Deneysel
- ✅ Apple Silicon (MPS) - M1/M2/M3
- ✅ CPU - Yavaş ama çalışır

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun
3. Değişikliklerinizi commit edin
4. Pull request gönderin

## 📝 Lisans

MIT License

## 🔗 Kaynaklar

- [Ollama](https://ollama.com) - Yerel LLM çalıştırma
- [LangChain](https://langchain.com) - LLM framework
- [Unsloth](https://github.com/unslothai/unsloth) - Hızlı fine-tuning
- [ChromaDB](https://www.trychroma.com) - Vektör veritabanı

## ❓ Sık Sorulan Sorular

**Q: GPU olmadan kullanabilir miyim?**
A: Evet! RAG ve Ollama Modelfile GPU gerektirmez. Fine-tuning için GPU önerilir ama CPU ile de çalışır (yavaş).

**Q: Hangi dosya formatları destekleniyor?**
A: PDF, DOCX, DOC, TXT, XLSX, XLS

**Q: Ollama nedir?**
A: Yerel bilgisayarınızda LLM çalıştırmanızı sağlayan ücretsiz bir araç.

**Q: API anahtarı gerekli mi?**
A: Ollama için hayır (ücretsiz). OpenAI/Google/Anthropic için evet.

**Q: Fine-tuning ne kadar sürer?**
A: GPU ile 5-10 dakika, CPU ile 2-6 saat (veri boyutuna bağlı).

---

💡 **İpucu**: İlk başta RAG (Bilgi Bankası) ile başlayın. En hızlı ve kolay yöntemdir!
