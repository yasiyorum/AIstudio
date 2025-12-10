import os
import shutil

class ModelManager:
    """
    3 farklı AI modeli oluşturma stratejisini yöneten merkezi sınıf.
    Lazy loading kullanarak hızlı açılış sağlar.
    """
    def __init__(self):
        self.db_dir = "models_db"
        os.makedirs(self.db_dir, exist_ok=True)
        self._embedding_function = None

    @property
    def embedding_function(self):
        """Embedding modelini sadece gerektiğinde yükle (lazy load)"""
        if self._embedding_function is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            self._embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return self._embedding_function

    # === MODEL LİSTELEME ===
    
    def list_local_models(self):
        """Yerel RAG modellerini listele"""
        if not os.path.exists(self.db_dir):
            return []
        return [d for d in os.listdir(self.db_dir) if os.path.isdir(os.path.join(self.db_dir, d))]

    def list_ollama_models(self):
        """Ollama'dan modelleri listele"""
        try:
            import ollama
            result = ollama.list()
            if 'models' in result:
                # Model objesi, dict değil
                return [m.model for m in result['models']]
            return []
        except ImportError:
            return []
        except Exception as e:
            print(f"Ollama hatası: {e}")
            return []

    # === STRATEJİ A: BİLGİ BANKASI (RAG) ===
    
    def create_model(self, model_name, files):
        """Geriye uyumluluk için - varsayılan RAG oluştur"""
        return self.create_rag_model(model_name, files)

    def create_rag_model(self, model_name, files):
        """
        Bilgi Bankası oluşturur (RAG).
        Dosyaları okur, parçalar ve vektör veritabanına kaydeder.
        """
        from langchain_community.vectorstores import Chroma
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:
            from langchain_text_splitters import RecursiveCharacterTextSplitter

        model_path = os.path.join(self.db_dir, model_name)
        if os.path.exists(model_path):
            raise ValueError(f"'{model_name}' adında bir bilgi bankası zaten var!")

        documents = self._load_files(files)
        if not documents:
            raise ValueError("Dosyalardan hiç metin okunamadı. Lütfen geçerli dosyalar seçin.")

        # Metni parçalara ayır
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200
        )
        chunks = text_splitter.split_documents(documents)

        # Vektör veritabanı oluştur
        Chroma.from_documents(
            documents=chunks,
            embedding=self.embedding_function,
            persist_directory=model_path
        )
        
        return f"✓ Bilgi Bankası '{model_name}' başarıyla oluşturuldu!\n({len(documents)} belge, {len(chunks)} parça işlendi)"

    def train_model(self, model_name, new_files):
        """Mevcut RAG modeline yeni dosyalar ekle"""
        from langchain_community.vectorstores import Chroma
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:
            from langchain_text_splitters import RecursiveCharacterTextSplitter

        model_path = os.path.join(self.db_dir, model_name)
        if not os.path.exists(model_path):
            raise ValueError(f"'{model_name}' adında bir model bulunamadı!")

        documents = self._load_files(new_files)
        if not documents:
            raise ValueError("Yeni dosyalardan metin okunamadı.")

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)

        vectordb = Chroma(
            persist_directory=model_path, 
            embedding_function=self.embedding_function
        )
        vectordb.add_documents(chunks)
        
        return f"✓ '{model_name}' modeline {len(documents)} yeni belge eklendi!"

    # === STRATEJİ B: TAŞINABİLİR MODEL (OLLAMA MODELFILE) ===
    
    def create_ollama_model(self, new_model_name, base_model, files):
        """
        Ollama Modelfile oluşturur.
        Dosyaları SYSTEM prompt'a gömer - taşınabilir model yaratır.
        """
        import ollama
        
        documents = self._load_files(files)
        if not documents:
            raise ValueError("Dosyalardan metin okunamadı.")
        
        full_text = "\n\n".join([d.page_content for d in documents])
        
        # Context boyutu limiti (modelfile için)
        max_context = 100000
        if len(full_text) > max_context:
            full_text = full_text[:max_context]
            full_text += "\n\n[NOT: Metin çok uzun olduğu için kısaltıldı]"

        modelfile_content = f"""FROM {base_model}
SYSTEM \"\"\"
Sen özelleştirilmiş bir yapay zeka asistanısın.
Aşağıdaki bilgiler senin temel bilgi kaynağındır:

{full_text}

Kullanıcı sorularını bu bilgilere dayanarak cevapla.
Eğer bilgi dışında bir şey sorulursa, genel bilgini kullan ama bunu belirt.
\"\"\"
"""
        
        
        # Modelfile'ı geçici dosyaya yaz
        import tempfile
        import subprocess
        
        temp_dir = tempfile.mkdtemp()
        modelfile_path = os.path.join(temp_dir, "Modelfile")
        
        try:
            # Modelfile dosyasını oluştur
            with open(modelfile_path, "w", encoding="utf-8") as f:
                f.write(modelfile_content)
            
            print(f"Creating Ollama model: {new_model_name}")
            print(f"Base model: {base_model}")
            print(f"Modelfile path: {modelfile_path}")
            
            # Ollama CLI komutunu direkt çalıştır (en güvenilir yöntem)
            cmd = ["ollama", "create", new_model_name, "-f", modelfile_path]
            print(f"Running: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            
            # Çıktıyı göster
            for line in process.stdout:
                print(f"Ollama: {line.strip()}")
            
            process.wait()
            
            # Geçici dosyayı temizle
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            if process.returncode == 0:
                return f"✓ Ollama Modeli '{new_model_name}' oluşturuldu!\n\nTerminalden test et: ollama run {new_model_name}\nListe görmek için: ollama list"
            else:
                stderr = process.stderr.read()
                raise RuntimeError(f"Ollama komut hatası:\n{stderr}")
        
        except FileNotFoundError:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("❌ 'ollama' komutu bulunamadı!\n\nOllama kurulu mu? Kontrol edin:\n  Windows: ollama.com/download\n  Terminal test: ollama --version")
        
        except Exception as e:
            # Geçici dosyayı temizle
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            import traceback
            print(f"Ollama creation error: {e}")
            traceback.print_exc()
            
            error_msg = str(e)
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                raise RuntimeError(f"❌ Ollama'ya bağlanılamadı!\n\nOllama çalışıyor mu kontrol edin:\n  Terminal: ollama serve\n\nHata: {error_msg}")
            elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                raise RuntimeError(f"❌ Baz model '{base_model}' bulunamadı!\n\nÖnce modeli indirin:\n  Terminal: ollama pull {base_model}\n\nHata: {error_msg}")
            else:
                raise RuntimeError(f"❌ Ollama model oluşturma hatası:\n{error_msg}")

    # === STRATEJİ C: GERÇEK EĞİTİM (FINE-TUNING) ===
    
    def create_finetune_model(self, new_model_name, base_model, files):
        """
        GERÇEK Fine-Tuning yapar (Unsloth ile).
        GPU gerektirir!
        """
        print("=" * 60)
        print("🔬 GERÇEK FINE-TUNING BAŞLIYOR")
        print("=" * 60)
        
        # 1. Donanım Kontrolü (GPU/CPU)
        device_type = "cpu"
        device_name = "CPU"
        use_4bit = False
        
        try:
            import torch
            
            # CUDA (NVIDIA) kontrolü
            if torch.cuda.is_available():
                device_type = "cuda"
                device_name = f"NVIDIA {torch.cuda.get_device_name(0)}"
                use_4bit = True
                print(f"✓ GPU bulundu: {device_name}")
            
            # ROCm (AMD) kontrolü
            elif hasattr(torch, 'hip') and torch.hip.is_available():
                device_type = "hip"
                device_name = "AMD GPU (ROCm)"
                use_4bit = False  # ROCm için 4-bit desteği sınırlı
                print(f"✓ AMD GPU bulundu: {device_name}")
                print("⚠️ AMD GPU desteği deneyseldir. NVIDIA GPU önerilir.")
            
            # Apple Silicon (MPS) kontrolü
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device_type = "mps"
                device_name = "Apple Silicon (M1/M2/M3)"
                use_4bit = False
                print(f"✓ Apple GPU bulundu: {device_name}")
                print("⚠️ Apple Silicon ile eğitim yavaş olabilir.")
            
            # CPU fallback
            else:
                device_type = "cpu"
                device_name = "CPU (İşlemci)"
                use_4bit = False
                print(f"⚠️ GPU bulunamadı, CPU kullanılacak: {device_name}")
                print("⚠️ UYARI: CPU ile eğitim çok yavaş olacak (saatler/günler sürebilir)")
                print("⚠️ Küçük modeller ve az veri ile deneyin!")
                
                # Kullanıcıya sor
                import tkinter.messagebox as mb
                response = mb.askyesno(
                    "Yavaş Eğitim Uyarısı",
                    "GPU bulunamadı. CPU ile eğitim çok yavaş olacak!\n\n"
                    "Alternatifler:\n"
                    "• RAG (Bilgi Bankası) - Anında, GPU gerektirmez\n"
                    "• Taşınabilir Model - Hızlı, GPU gerektirmez\n"
                    "• Google Colab - Ücretsiz NVIDIA GPU\n\n"
                    "Yine de CPU ile devam etmek istiyor musunuz?"
                )
                if not response:
                    raise RuntimeError("Kullanıcı eğitimi iptal etti.")
        
        except ImportError:
            raise RuntimeError("❌ PyTorch kurulu değil!\n\nKurulum: pip install torch")
        
        # 2. Unsloth ve Fine-Tuning Kütüphaneleri Kontrolü
        try:
            from unsloth import FastLanguageModel
            from trl import SFTTrainer
            from transformers import TrainingArguments
            from datasets import Dataset
            print("✓ Fine-tuning kütüphaneleri hazır")
        except ImportError as e:
            missing = str(e).split("'")[1] if "'" in str(e) else "bilinmeyen"
            
            print(f"\n⚠️ Fine-Tuning için gerekli kütüphaneler eksik!")
            print(f"   Eksik: {missing}")
            print("\n" + "="*60)
            
            # Kullanıcıya sor
            import tkinter.messagebox as mb
            response = mb.askyesno(
                "Fine-Tuning Kurulumu",
                "Fine-Tuning için ek kütüphaneler gerekli:\n\n"
                "• torch (PyTorch)\n"
                "• transformers\n"
                "• datasets\n"
                "• trl\n"
                "• unsloth\n\n"
                f"Donanım: {device_name}\n\n"
                "Bu paketler otomatik kurulsun mu?\n"
                "(İndirme ~2-5GB, kurulum 5-10 dakika sürebilir)"
            )
            
            if not response:
                raise RuntimeError(
                    "❌ Fine-tuning iptal edildi.\n\n"
                    "Alternatifler:\n"
                    "  • RAG (Bilgi Bankası) - Kurulum gerektirmez\n"
                    "  • Taşınabr Model (Ollama) - Kurulum gerektirmez"
                )
            
            # Kurulum başlat
            print("\n📦 Fine-Tuning kütüphaneleri kuruluyor...")
            print("⏳ Bu işlem birkaç dakika sürebilir, lütfen bekleyin...\n")
            
            import subprocess
            import sys
            
            # PyTorch kurulumu (donanıma göre)
            print("1/5 PyTorch kuruluyor...")
            if device_type == "cuda":
                cmd = [sys.executable, "-m", "pip", "install", "torch", "--index-url", "https://download.pytorch.org/whl/cu121"]
            elif device_type == "hip":
                cmd = [sys.executable, "-m", "pip", "install", "torch", "--index-url", "https://download.pytorch.org/whl/rocm5.7"]
            else:
                cmd = [sys.executable, "-m", "pip", "install", "torch"]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"PyTorch kurulumu başarısız:\n{result.stderr}")
            print("✓ PyTorch kuruldu\n")
            
            # Transformers
            print("2/5 Transformers kuruluyor...")
            subprocess.run([sys.executable, "-m", "pip", "install", "transformers"], check=True)
            print("✓ Transformers kuruldu\n")
            
            # Datasets
            print("3/5 Datasets kuruluyor...")
            subprocess.run([sys.executable, "-m", "pip", "install", "datasets"], check=True)
            print("✓ Datasets kuruldu\n")
            
            # TRL
            print("4/5 TRL kuruluyor...")
            subprocess.run([sys.executable, "-m", "pip", "install", "trl"], check=True)
            print("✓ TRL kuruldu\n")
            
            # Unsloth
            print("5/5 Unsloth kuruluyor...")
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install",
                    "unsloth @ git+https://github.com/unslothai/unsloth.git"
                ], check=True, timeout=600)
                print("✓ Unsloth kuruldu\n")
            except subprocess.TimeoutExpired:
                print("⚠️ Unsloth kurulumu zaman aşımına uğradı, basit versiyon deneniyor...")
                subprocess.run([sys.executable, "-m", "pip", "install", "unsloth"], check=True)
                print("✓ Unsloth kuruldu\n")
            
            print("="*60)
            print("✅ Tüm fine-tuning kütüphaneleri başarıyla kuruldu!")
            print("="*60)
            print("\n🔄 Kütüphaneler yükleniyor...\n")
            
            # Tekrar import et
            try:
                from unsloth import FastLanguageModel
                from trl import SFTTrainer
                from transformers import TrainingArguments
                from datasets import Dataset
            except Exception as e:
                raise RuntimeError(
                    f"❌ Kurulum tamamlandı ama import hatası:\n{e}\n\n"
                    "Uygulamayı yeniden başlatıp tekrar deneyin."
                )
        
        # 3. Dosyaları okuma ve dataset hazırlama
        print("\n📚 Eğitim verisi hazırlanıyor...")
        documents = self._load_files(files)
        if not documents:
            raise ValueError("Dosyalardan metin okunamadı.")
        
        # Dokümanları Q&A formatına çevir
        training_data = []
        for doc in documents:
            content = doc.page_content
            # Basit formatla: her paragraf bir eğitim örneği
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            for i, para in enumerate(paragraphs):
                if len(para) > 50:  # Çok kısa paragrafları atla
                    training_data.append({
                        "instruction": "Aşağıdaki bilgiyi özetle veya açıkla:",
                        "input": para[:500],  # İlk 500 karakter
                        "output": para  # Tam metin
                    })
        
        if len(training_data) < 5:
            raise ValueError(
                f"Yetersiz eğitim verisi! En az 5 örnek gerekli, {len(training_data)} bulundu.\n"
                "Daha fazla ve daha uzun dosya ekleyin."
            )
        
        print(f"✓ {len(training_data)} eğitim örneği hazırlandı")
        
        # 4. Model yükleme
        print(f"\n🤖 Baz model yükleniyor: {base_model}")
        print(f"   Donanım: {device_name}")
        max_seq_length = 2048
        
        try:
            if use_4bit:
                # 4-bit quantization (NVIDIA GPU için)
                model, tokenizer = FastLanguageModel.from_pretrained(
                    model_name=base_model,
                    max_seq_length=max_seq_length,
                    dtype=None,
                    load_in_4bit=True,
                )
            else:
                # Normal loading (CPU, AMD, Apple için)
                model, tokenizer = FastLanguageModel.from_pretrained(
                    model_name=base_model,
                    max_seq_length=max_seq_length,
                    dtype=torch.float32 if device_type == "cpu" else None,
                    load_in_4bit=False,
                )
            
            print("✓ Model yüklendi")
        except Exception as e:
            raise RuntimeError(f"Model yüklenemedi: {e}\n\nModel adı doğru mu? Örnek: 'unsloth/llama-3-8b-bnb-4bit'")
        
        # 5. LoRA adaptörleri ekle
        print("\n🔧 LoRA adaptörleri ekleniyor...")
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,  # LoRA rank
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                           "gate_proj", "up_proj", "down_proj"],
            lora_alpha=16,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=3407,
        )
        print("✓ LoRA adaptörleri hazır")
        
        # 6. Dataset formatı
        print("\n📝 Dataset formatlanıyor...")
        from datasets import Dataset
        
        dataset = Dataset.from_list(training_data)
        
        def formatting_func(examples):
            texts = []
            for instruction, input_text, output in zip(
                examples["instruction"], 
                examples["input"], 
                examples["output"]
            ):
                text = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
                texts.append(text)
            return {"text": texts}
        
        dataset = dataset.map(formatting_func, batched=True)
        print(f"✓ Dataset hazır: {len(dataset)} örnek")
        
        # 7. Eğitim parametreleri (donanıma göre optimize edilmiş)
        print("\n⚙️ Eğitim parametreleri ayarlanıyor...")
        from trl import SFTTrainer
        from transformers import TrainingArguments
        
        output_dir = f"./finetune_output/{new_model_name}"
        
        # Donanıma göre batch size ve steps
        if device_type == "cpu":
            batch_size = 1
            max_steps = 20  # CPU için çok az
            print("   CPU modu: Çok küçük batch size ve az step")
        elif device_type in ["hip", "mps"]:
            batch_size = 1
            max_steps = 30
            print("   AMD/Apple modu: Küçük batch size")
        else:
            batch_size = 2
            max_steps = 50
        
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            dataset_text_field="text",
            max_seq_length=max_seq_length,
            args=TrainingArguments(
                per_device_train_batch_size=batch_size,
                gradient_accumulation_steps=4,
                warmup_steps=5,
                max_steps=max_steps,
                learning_rate=2e-4,
                fp16=False if device_type == "cpu" else (not torch.cuda.is_bf16_supported()),
                bf16=False if device_type in ["cpu", "mps"] else torch.cuda.is_bf16_supported(),
                logging_steps=10,
                optim="adamw_8bit" if device_type == "cuda" else "adamw_torch",
                weight_decay=0.01,
                lr_scheduler_type="linear",
                seed=3407,
                output_dir=output_dir,
                save_strategy="steps",
                save_steps=max_steps // 2,
            ),
        )
        
        print("✓ Eğitici hazır")
        
        # 8. EĞİTİMİ BAŞLAT!
        print("\n" + "="*60)
        print("🚀 EĞİTİM BAŞLIYOR - Bu biraz zaman alabilir...")
        print("="*60 + "\n")
        
        try:
            trainer.train()
            print("\n✓ Eğitim tamamlandı!")
        except Exception as e:
            raise RuntimeError(f"Eğitim sırasında hata:\n{e}")
        
        # 9. Modeli kaydet
        print("\n💾 Model kaydediliyor...")
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        
        # 10. Ollama formatına çevir (opsiyonel)
        print("\n🔄 Ollama formatına çevriliyor...")
        try:
            # GGUF formatına çevir
            model.save_pretrained_gguf(
                output_dir,
                tokenizer,
                quantization_method="q4_k_m"
            )
            gguf_file = f"{output_dir}/{new_model_name}.gguf"
            
            # Ollama Modelfile oluştur
            modelfile_content = f"""FROM {gguf_file}
PARAMETER temperature 0.7
PARAMETER top_p 0.9
"""
            modelfile_path = f"{output_dir}/Modelfile"
            with open(modelfile_path, "w") as f:
                f.write(modelfile_content)
            
            # Ollama'ya ekle
            import subprocess
            cmd = ["ollama", "create", new_model_name, "-f", modelfile_path]
            subprocess.run(cmd, check=True)
            
            print(f"✓ Ollama'ya eklendi: {new_model_name}")
        except Exception as e:
            print(f"⚠️ Ollama'ya eklenemedi (manuel ekleyebilirsiniz): {e}")
        
        return (
            f"✅ Fine-Tuning BAŞARILI!\n\n"
            f"Model: {new_model_name}\n"
            f"Konum: {output_dir}\n"
            f"Eğitim örnekleri: {len(training_data)}\n\n"
            f"Kullanım:\n"
            f"  Terminal: ollama run {new_model_name}\n"
            f"  veya bu uygulamadan seçin"
        )

    # === YARDIMCI FONKSİYONLAR ===
    
    def _load_files(self, file_paths):
        """Çeşitli dosya formatlarını yükle"""
        from langchain_community.document_loaders import (
            TextLoader, PyPDFLoader, Docx2txtLoader, UnstructuredExcelLoader
        )
        
        documents = []
        for file_path in file_paths:
            ext = os.path.splitext(file_path)[1].lower()
            loader = None
            
            try:
                if ext == ".txt":
                    loader = TextLoader(file_path, encoding="utf-8")
                elif ext == ".pdf":
                    loader = PyPDFLoader(file_path)
                elif ext in [".docx", ".doc"]:
                    loader = Docx2txtLoader(file_path)
                elif ext in [".xlsx", ".xls"]:
                    loader = UnstructuredExcelLoader(file_path)
                
                if loader:
                    documents.extend(loader.load())
                else:
                    print(f"Desteklenmeyen dosya formatı: {file_path}")
            
            except Exception as e:
                print(f"HATA - '{os.path.basename(file_path)}' okunamadı: {e}")
        
        return documents

    def delete_model(self, model_name):
        """RAG modelini sil"""
        model_path = os.path.join(self.db_dir, model_name)
        if os.path.exists(model_path):
            shutil.rmtree(model_path)
            return True
        return False
