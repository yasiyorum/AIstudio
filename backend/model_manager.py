import os
import shutil
import threading
from backend.logger import logger

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class ModelManager:
    """
    3 farklı AI modeli oluşturma stratejisini yöneten merkezi sınıf.
    Lazy loading, progress callbacks, ve iptal desteği.
    """
    def __init__(self):
        self.db_dir = os.path.join(_BASE_DIR, "models_db")
        os.makedirs(self.db_dir, exist_ok=True)
        self._embedding_function = None
        self._cancel_training = False
        self._training_active = False

    @property
    def embedding_function(self):
        if self._embedding_function is None:
            from langchain_huggingface import HuggingFaceEmbeddings
            self._embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        return self._embedding_function

    def cancel_training(self):
        self._cancel_training = True

    @property
    def is_training(self):
        return self._training_active

    # === MODEL LİSTELEME ===
    
    def list_local_models(self):
        if not os.path.exists(self.db_dir):
            return []
        return [d for d in os.listdir(self.db_dir) if os.path.isdir(os.path.join(self.db_dir, d))]

    def list_ollama_models(self):
        try:
            import ollama
            result = ollama.list()
            if 'models' in result:
                return [m.model for m in result['models']]
            return []
        except ImportError:
            return []
        except Exception as e:
            print(f"Ollama hatası: {e}")
            return []

    def get_model_info(self, model_name):
        """Model hakkında detaylı bilgi döndür"""
        info = {"name": model_name, "type": "unknown", "size": "N/A", "date": "N/A"}
        
        # RAG model mi?
        model_path = os.path.join(self.db_dir, model_name)
        if os.path.exists(model_path):
            info["type"] = "RAG (Bilgi Bankası)"
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(model_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
            info["size"] = self._format_size(total_size)
            info["date"] = self._get_dir_date(model_path)
        else:
            info["type"] = "Ollama Model"
        
        return info

    def _format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _get_dir_date(self, path):
        import datetime
        try:
            mtime = os.path.getmtime(path)
            return datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        except:
            return "N/A"

    # === STRATEJİ A: BİLGİ BANKASI (RAG) ===
    
    def create_model(self, model_name, files, progress_callback=None):
        return self.create_rag_model(model_name, files, progress_callback=progress_callback)

    def create_rag_model(self, model_name, files, chunk_size=1000, chunk_overlap=200, progress_callback=None):
        """
        Bilgi Bankası oluşturur (RAG).
        progress_callback(message, progress_pct) - ilerleme bilgisi
        """
        from langchain_community.vectorstores import Chroma
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:
            from langchain_text_splitters import RecursiveCharacterTextSplitter

        def update(msg, pct=None):
            if progress_callback:
                progress_callback(msg, pct)
            print(msg)

        model_path = os.path.join(self.db_dir, model_name)
        if os.path.exists(model_path):
            raise ValueError(f"'{model_name}' adında bir bilgi bankası zaten var!")

        update(f"📂 {len(files)} dosya okunuyor...", 0.1)
        documents = self._load_files(files, progress_callback=progress_callback)
        if not documents:
            raise ValueError("Dosyalardan hiç metin okunamadı.")

        update(f"✂️ Metin parçalara ayrılıyor (chunk: {chunk_size}, overlap: {chunk_overlap})...", 0.4)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap
        )
        chunks = text_splitter.split_documents(documents)
        update(f"✓ {len(chunks)} parça oluşturuldu", 0.6)

        update("🧠 Vektör veritabanı oluşturuluyor (embedding)...", 0.7)
        Chroma.from_documents(
            documents=chunks,
            embedding=self.embedding_function,
            persist_directory=model_path
        )
        update("✅ Bilgi bankası hazır!", 1.0)
        
        return f"✓ Bilgi Bankası '{model_name}' başarıyla oluşturuldu!\n({len(documents)} belge, {len(chunks)} parça işlendi)"

    def train_model(self, model_name, new_files, progress_callback=None):
        from langchain_community.vectorstores import Chroma
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:
            from langchain_text_splitters import RecursiveCharacterTextSplitter

        def update(msg, pct=None):
            if progress_callback:
                progress_callback(msg, pct)

        model_path = os.path.join(self.db_dir, model_name)
        if not os.path.exists(model_path):
            raise ValueError(f"'{model_name}' adında bir model bulunamadı!")

        update("📂 Yeni dosyalar okunuyor...", 0.2)
        documents = self._load_files(new_files, progress_callback=progress_callback)
        if not documents:
            raise ValueError("Yeni dosyalardan metin okunamadı.")

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)

        update("🧠 Veritabanına ekleniyor...", 0.7)
        vectordb = Chroma(
            persist_directory=model_path, 
            embedding_function=self.embedding_function
        )
        vectordb.add_documents(chunks)
        update("✅ Tamamlandı!", 1.0)
        
        return f"✓ '{model_name}' modeline {len(documents)} yeni belge eklendi!"

    # === STRATEJİ B: TAŞINABİLİR MODEL (OLLAMA MODELFILE) ===
    
    def create_ollama_model(self, new_model_name, base_model, files, 
                             system_prompt=None, progress_callback=None):
        """
        Ollama Modelfile oluşturur.
        system_prompt: Özel system prompt (None ise varsayılan kullanılır)
        """
        import ollama
        
        def update(msg, pct=None):
            if progress_callback:
                progress_callback(msg, pct)
            print(msg)

        update("📂 Dosyalar okunuyor...", 0.1)
        documents = self._load_files(files, progress_callback=progress_callback)
        if not documents:
            raise ValueError("Dosyalardan metin okunamadı.")
        
        full_text = "\n\n".join([d.page_content for d in documents])
        
        max_context = 100000
        if len(full_text) > max_context:
            full_text = full_text[:max_context]
            full_text += "\n\n[NOT: Metin çok uzun olduğu için kısaltıldı]"
            update(f"⚠️ Metin {max_context} karaktere kısaltıldı", 0.3)

        # System prompt
        if system_prompt is None:
            system_prompt = f"""Sen özelleştirilmiş bir yapay zeka asistanısın.
Aşağıdaki bilgiler senin temel bilgi kaynağındır:

{full_text}

Kullanıcı sorularını bu bilgilere dayanarak cevapla.
Eğer bilgi dışında bir şey sorulursa, genel bilgini kullan ama bunu belirt."""
        else:
            # Kullanıcı özel prompt verdiyse, bilgi metnini ekle
            system_prompt = system_prompt.replace("{CONTENT}", full_text)

        modelfile_content = f'FROM {base_model}\nSYSTEM """\n{system_prompt}\n"""\n'
        
        import tempfile
        import subprocess
        
        temp_dir = tempfile.mkdtemp()
        modelfile_path = os.path.join(temp_dir, "Modelfile")
        
        try:
            with open(modelfile_path, "w", encoding="utf-8") as f:
                f.write(modelfile_content)
            
            update(f"🔨 Ollama modeli oluşturuluyor: {new_model_name}...", 0.5)
            
            cmd = ["ollama", "create", new_model_name, "-f", modelfile_path]
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8'
            )
            
            for line in process.stdout:
                stripped = line.strip()
                if stripped:
                    update(f"  {stripped}", None)
            
            process.wait()
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            if process.returncode == 0:
                update("✅ Model oluşturuldu!", 1.0)
                return f"✓ Ollama Modeli '{new_model_name}' oluşturuldu!\n\nTerminalden test: ollama run {new_model_name}"
            else:
                stderr = process.stderr.read()
                raise RuntimeError(f"Ollama komut hatası:\n{stderr}")
        
        except FileNotFoundError:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("❌ 'ollama' komutu bulunamadı!\n\nollama.com/download adresinden kurun.")
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            error_msg = str(e)
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                raise RuntimeError(f"❌ Ollama'ya bağlanılamadı!\n\nTerminal: ollama serve\n\nHata: {error_msg}")
            raise RuntimeError(f"❌ Ollama model hatası:\n{error_msg}")

    # === STRATEJİ D: BEYİN MODEL (SIFIRDAN) ===
    
    def create_brain_model(self, new_model_name, base_model, system_instructions,
                            files=None, progress_callback=None):
        """
        Sıfırdan beyin model oluşturur — sadece talimatlarla, dosya opsiyonel.
        """
        import ollama
        
        def update(msg, pct=None):
            if progress_callback:
                progress_callback(msg, pct)
            print(msg)

        update("🧠 Beyin modeli hazırlanıyor...", 0.1)
        
        # Opsiyonel dosya içeriği ekle
        file_content = ""
        if files:
            update(f"📂 {len(files)} dosya okunuyor...", 0.2)
            documents = self._load_files(files, progress_callback=progress_callback)
            if documents:
                file_content = "\n\n".join([d.page_content for d in documents])
                # Boyut limiti
                if len(file_content) > 80000:
                    file_content = file_content[:80000]
                    update("⚠️ Dosya içeriği kısaltıldı (80K karakter limiti)", 0.35)
                update(f"✓ {len(documents)} dosya okundu", 0.4)
        
        # System prompt oluştur
        final_prompt = system_instructions
        if file_content:
            final_prompt += f"\n\n--- EK BİLGİ KAYNAĞI ---\n\n{file_content}"
        
        update(f"📝 System prompt hazır ({len(final_prompt)} karakter)", 0.5)
        
        # Modelfile oluştur
        modelfile_content = f'FROM {base_model}\nSYSTEM """\n{final_prompt}\n"""\nPARAMETER temperature 0.7\n'
        
        import tempfile
        import subprocess
        
        temp_dir = tempfile.mkdtemp()
        modelfile_path = os.path.join(temp_dir, "Modelfile")
        
        try:
            with open(modelfile_path, "w", encoding="utf-8") as f:
                f.write(modelfile_content)
            
            update(f"🔨 Ollama modeli oluşturuluyor: {new_model_name}...", 0.6)
            
            cmd = ["ollama", "create", new_model_name, "-f", modelfile_path]
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8'
            )
            
            for line in process.stdout:
                stripped = line.strip()
                if stripped:
                    update(f"  {stripped}", None)
            
            process.wait()
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            if process.returncode == 0:
                update("✅ Beyin modeli oluşturuldu!", 1.0)
                extra = ""
                if files:
                    extra = f"\nEk bilgi: {len(files)} dosyadan bilgi eklendi"
                return (
                    f"✓ Beyin Modeli '{new_model_name}' oluşturuldu!\n"
                    f"Baz: {base_model}\n"
                    f"Talimat: {len(system_instructions)} karakter{extra}\n\n"
                    f"Test: ollama run {new_model_name}"
                )
            else:
                stderr = process.stderr.read()
                raise RuntimeError(f"Ollama komut hatası:\n{stderr}")
        
        except FileNotFoundError:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("❌ 'ollama' komutu bulunamadı!\n\nollama.com/download adresinden kurun.")
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError(f"❌ Beyin model hatası:\n{str(e)}")

    # === STRATEJİ E: SIFIRDAN EĞİTİM (FROM SCRATCH) ===

    def create_scratch_model(self, new_model_name, files,
                              vocab_size=5000, n_layers=4, n_heads=4,
                              hidden_size=256, max_steps=200,
                              learning_rate=5e-4, batch_size=2,
                              progress_callback=None):
        """
        Sıfırdan model eğitir — hiçbir baz model kullanmadan.
        GPT-2 mimarisinde küçük bir model oluşturur ve kullanıcı verileriyle eğitir.
        """
        self._training_active = True
        self._cancel_training = False

        def update(msg, pct=None):
            if progress_callback:
                progress_callback(msg, pct)
            print(msg)

        try:
            return self._do_scratch_train(
                new_model_name, files, vocab_size, n_layers, n_heads,
                hidden_size, max_steps, learning_rate, batch_size, update
            )
        finally:
            self._training_active = False

    def _do_scratch_train(self, new_model_name, files,
                           vocab_size, n_layers, n_heads,
                           hidden_size, max_steps, learning_rate,
                           batch_size, update):
        
        update("🔍 Kütüphaneler kontrol ediliyor...", 0.02)
        
        try:
            import torch
            from transformers import (
                GPT2Config, GPT2LMHeadModel, GPT2TokenizerFast,
                TrainingArguments, Trainer, TrainerCallback,
                DataCollatorForLanguageModeling
            )
            from tokenizers import Tokenizer, models, trainers, pre_tokenizers
            from datasets import Dataset
            update("✓ Kütüphaneler hazır", 0.05)
        except ImportError as e:
            missing = str(e)
            raise RuntimeError(
                f"❌ Gerekli kütüphaneler eksik:\n{missing}\n\n"
                "Kurulum:\n"
                "  pip install torch transformers datasets tokenizers"
            )

        if self._cancel_training:
            raise RuntimeError("⚠️ Eğitim iptal edildi.")

        # 1. Donanım
        device = "cpu"
        if torch.cuda.is_available():
            device = "cuda"
            update(f"✓ GPU: {torch.cuda.get_device_name(0)}", 0.06)
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            device = "mps"
            update("✓ GPU: Apple Silicon", 0.06)
        else:
            update("⚠️ GPU yok — CPU kullanılacak (yavaş olabilir)", 0.06)

        # 2. Dosyaları oku
        update("📚 Eğitim verisi okunuyor...", 0.08)
        documents = self._load_files(files, progress_callback=lambda m, p: update(m, None))
        if not documents:
            raise ValueError("Dosyalardan metin okunamadı!")
        
        full_text = "\n\n".join([d.page_content for d in documents])
        if len(full_text) < 500:
            raise ValueError(
                f"Yetersiz veri! Sadece {len(full_text)} karakter var.\n"
                "Sıfırdan eğitim için en az birkaç sayfa metin gerekir."
            )
        update(f"✓ {len(full_text):,} karakter okundu ({len(documents)} dosya)", 0.12)

        if self._cancel_training:
            raise RuntimeError("⚠️ Eğitim iptal edildi.")

        # 3. Tokenizer eğit (BPE) — sıfırdan!
        update("🔤 Tokenizer eğitiliyor (BPE)...", 0.15)
        
        import tempfile
        temp_dir = tempfile.mkdtemp()
        corpus_path = os.path.join(temp_dir, "corpus.txt")
        with open(corpus_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        
        tokenizer_model = Tokenizer(models.BPE(unk_token="<unk>"))
        tokenizer_model.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
        
        bpe_trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            special_tokens=["<pad>", "<unk>", "<bos>", "<eos>"],
            min_frequency=2
        )
        tokenizer_model.train([corpus_path], trainer=bpe_trainer)
        
        tokenizer_path = os.path.join(temp_dir, "tokenizer.json")
        tokenizer_model.save(tokenizer_path)
        
        tokenizer = GPT2TokenizerFast(tokenizer_file=tokenizer_path)
        tokenizer.pad_token = "<pad>"
        tokenizer.bos_token = "<bos>"
        tokenizer.eos_token = "<eos>"
        tokenizer.unk_token = "<unk>"
        
        actual_vocab = tokenizer.vocab_size
        update(f"✓ Tokenizer hazır: {actual_vocab} token", 0.22)

        if self._cancel_training:
            raise RuntimeError("⚠️ Eğitim iptal edildi.")

        # 4. Model mimarisini sıfırdan oluştur
        update(f"🏗️ Model mimarisi oluşturuluyor ({n_layers} katman, {hidden_size} boyut)...", 0.25)
        
        config = GPT2Config(
            vocab_size=actual_vocab,
            n_positions=512,
            n_embd=hidden_size,
            n_layer=n_layers,
            n_head=n_heads,
            bos_token_id=tokenizer.bos_token_id,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
        
        model = GPT2LMHeadModel(config)
        param_count = sum(p.numel() for p in model.parameters())
        update(f"✓ Model oluşturuldu: {param_count:,} parametre (rastgele ağırlıklar)", 0.30)

        # 5. Dataset hazırla
        update("📝 Dataset hazırlanıyor...", 0.35)
        
        # Metni bloklara böl
        block_size = 128
        encodings = tokenizer(full_text, return_attention_mask=False)
        input_ids = encodings["input_ids"]
        
        examples = []
        for i in range(0, len(input_ids) - block_size, block_size // 2):
            chunk = input_ids[i:i + block_size]
            if len(chunk) == block_size:
                examples.append({"input_ids": chunk, "labels": chunk.copy()})
        
        if len(examples) < 5:
            raise ValueError(
                f"Yetersiz eğitim verisi! Sadece {len(examples)} blok oluşturuldu.\n"
                "Daha fazla metin ekleyin."
            )
        
        dataset = Dataset.from_list(examples)
        update(f"✓ {len(examples)} eğitim bloğu hazır", 0.40)

        if self._cancel_training:
            raise RuntimeError("⚠️ Eğitim iptal edildi.")

        # 6. Eğitim
        output_dir = os.path.join(temp_dir, "output")
        manager_ref = self

        class ScratchMetricsCallback(TrainerCallback):
            def on_log(self, args, state, control, logs=None, **kwargs):
                if logs and state:
                    step = state.global_step
                    total = state.max_steps
                    loss = logs.get("loss", "?")
                    pct = 0.45 + (0.45 * step / total) if total > 0 else 0.45
                    update(f"📊 Step {step}/{total} | Loss: {loss}", pct)
            
            def on_step_end(self, args, state, control, **kwargs):
                if manager_ref._cancel_training:
                    control.should_training_stop = True
                    update("⚠️ Eğitim iptal ediliyor...", None)
                return control

        data_collator = DataCollatorForLanguageModeling(
            tokenizer=tokenizer, mlm=False
        )

        training_args = TrainingArguments(
            output_dir=output_dir,
            overwrite_output_dir=True,
            num_train_epochs=1,
            max_steps=max_steps,
            per_device_train_batch_size=batch_size,
            learning_rate=learning_rate,
            weight_decay=0.01,
            warmup_steps=max(1, max_steps // 10),
            logging_steps=max(1, max_steps // 20),
            save_strategy="no",
            fp16=(device == "cuda" and torch.cuda.is_available()),
            dataloader_pin_memory=False,
            report_to="none",
        )

        update(f"🚀 Sıfırdan eğitim başlıyor (steps={max_steps}, lr={learning_rate})...", 0.45)
        
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=dataset,
            data_collator=data_collator,
            callbacks=[ScratchMetricsCallback()],
        )

        try:
            trainer.train()
            if self._cancel_training:
                raise RuntimeError("Eğitim iptal edildi.")
            update("✓ Eğitim tamamlandı!", 0.90)
        except RuntimeError as e:
            if "iptal" in str(e).lower():
                raise
            raise RuntimeError(f"Eğitim hatası: {e}")

        # 7. Kaydet
        update("💾 Model kaydediliyor...", 0.92)
        save_dir = os.path.join(".", "scratch_models", new_model_name)
        os.makedirs(save_dir, exist_ok=True)
        model.save_pretrained(save_dir)
        tokenizer.save_pretrained(save_dir)

        # 8. GGUF + Ollama dene
        update("🔄 Ollama'ya eklenmeye çalışılıyor...", 0.95)
        ollama_ok = False
        try:
            from transformers import AutoModelForCausalLM
            # llama.cpp convert denenir
            import subprocess
            
            # Basit modelfile ile dene
            modelfile_content = (
                f'FROM {save_dir}\n'
                f'PARAMETER temperature 0.8\n'
                f'PARAMETER top_p 0.9\n'
            )
            mf_path = os.path.join(save_dir, "Modelfile")
            with open(mf_path, "w") as f:
                f.write(modelfile_content)
            
            result = subprocess.run(
                ["ollama", "create", new_model_name, "-f", mf_path],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                ollama_ok = True
                update("✓ Ollama'ya eklendi!", 1.0)
        except Exception as e:
            update(f"⚠️ Ollama'ya eklenemedi: {e}", 0.98)

        update("✅ Sıfırdan eğitim tamamlandı!", 1.0)

        # Temizle
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

        ollama_note = ""
        if ollama_ok:
            ollama_note = f"\n\n🎯 Kulllanım: ollama run {new_model_name}"
        else:
            ollama_note = (
                f"\n\n⚠️ Bu model Ollama'ya otomatik eklenemedi.\n"
                f"Model konumu: {save_dir}\n"
                f"HuggingFace ile kullanabilirsiniz."
            )

        return (
            f"✅ Sıfırdan Eğitim Tamamlandı!\n\n"
            f"Model: {new_model_name}\n"
            f"Parametreler: {param_count:,}\n"
            f"Katmanlar: {n_layers} | Boyut: {hidden_size}\n"
            f"Vocab: {actual_vocab} token\n"
            f"Eğitim: {len(examples)} blok, {max_steps} step\n"
            f"Konum: {save_dir}"
            f"{ollama_note}"
        )

    # === STRATEJİ C: GERÇEK EĞİTİM (FINE-TUNING) ===
    
    def create_finetune_model(self, new_model_name, base_model, files,
                               learning_rate=2e-4, max_steps=50, batch_size=2,
                               progress_callback=None):
        """
        GERÇEK Fine-Tuning (Unsloth ile).
        İptal desteği ve canlı metrikler.
        """
        self._training_active = True
        self._cancel_training = False

        def update(msg, pct=None):
            if progress_callback:
                progress_callback(msg, pct)
            print(msg)

        try:
            return self._do_finetune(
                new_model_name, base_model, files,
                learning_rate, max_steps, batch_size, update
            )
        finally:
            self._training_active = False

    def _do_finetune(self, new_model_name, base_model, files,
                      learning_rate, max_steps, batch_size, update):
        
        update("🔍 Donanım kontrol ediliyor...", 0.02)
        
        # 1. Donanım Kontrolü
        device_type = "cpu"
        device_name = "CPU"
        use_4bit = False
        
        try:
            import torch
            
            if torch.cuda.is_available():
                device_type = "cuda"
                device_name = f"NVIDIA {torch.cuda.get_device_name(0)}"
                use_4bit = True
                update(f"✓ GPU: {device_name}", 0.05)
            elif hasattr(torch, 'hip') and torch.hip.is_available():
                device_type = "hip"
                device_name = "AMD GPU (ROCm)"
                update(f"✓ GPU: {device_name} (deneysel)", 0.05)
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device_type = "mps"
                device_name = "Apple Silicon"
                update(f"✓ GPU: {device_name}", 0.05)
            else:
                device_type = "cpu"
                device_name = "CPU"
                logger.warning("Fine-Tuning için GPU bulunamadı, CPU kullanılacak.")
                update("⚠️ GPU bulunamadı, CPU kullanılacak (Eğitim belirgin biçimde yavaş olabilir)...", 0.05)
        except ImportError:
            raise RuntimeError("❌ PyTorch kurulu değil!\n\nKurulum: pip install torch")
        
        if self._cancel_training:
            raise RuntimeError("⚠️ Eğitim iptal edildi.")

        # 2. Kütüphaneler
        update("📦 Kütüphaneler kontrol ediliyor...", 0.08)
        try:
            from unsloth import FastLanguageModel
            from trl import SFTTrainer
            from transformers import TrainingArguments, TrainerCallback
            from datasets import Dataset
            update("✓ Kütüphaneler hazır", 0.1)
        except ImportError as e:
            missing = str(e).split("'")[1] if "'" in str(e) else "bilinmeyen"
            raise RuntimeError(
                f"❌ Fine-Tuning kütüphaneleri eksik: {missing}\n\n"
                "Kurulum:\n"
                "  pip install torch transformers datasets trl\n"
                '  pip install "unsloth @ git+https://github.com/unslothai/unsloth.git"'
            )
        
        if self._cancel_training:
            raise RuntimeError("⚠️ Eğitim iptal edildi.")

        # 3. Dosyaları oku
        update("📚 Eğitim verisi hazırlanıyor...", 0.15)
        documents = self._load_files(files, progress_callback=lambda msg, pct: update(msg, None))
        if not documents:
            raise ValueError("Dosyalardan metin okunamadı.")
        
        # Daha akıllı dataset hazırlama
        training_data = []
        for doc in documents:
            content = doc.page_content
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            for para in paragraphs:
                if len(para) > 50:
                    # Soru-cevap formatı
                    training_data.append({
                        "instruction": "Aşağıdaki bilgiyi özetle ve açıkla:",
                        "input": para[:500],
                        "output": para
                    })
                    
                    # Ek: bilgi sorusu formatı
                    if len(para) > 100:
                        sentences = [s.strip() for s in para.replace('!', '.').replace('?', '.').split('.') if len(s.strip()) > 20]
                        if len(sentences) >= 2:
                            training_data.append({
                                "instruction": f"Bu konuda bilgi ver: {sentences[0][:100]}",
                                "input": "",
                                "output": para
                            })
        
        if len(training_data) < 5:
            raise ValueError(
                f"Yetersiz eğitim verisi! En az 5 örnek gerekli, {len(training_data)} bulundu.\n"
                "Daha fazla ve daha uzun dosya ekleyin."
            )
        
        update(f"✓ {len(training_data)} eğitim örneği hazırlandı", 0.2)
        
        if self._cancel_training:
            raise RuntimeError("⚠️ Eğitim iptal edildi.")

        # 4. Model yükle
        update(f"🤖 Baz model yükleniyor: {base_model}...", 0.25)
        max_seq_length = 2048
        
        try:
            if use_4bit:
                model, tokenizer = FastLanguageModel.from_pretrained(
                    model_name=base_model,
                    max_seq_length=max_seq_length,
                    dtype=None,
                    load_in_4bit=True,
                )
            else:
                import torch
                model, tokenizer = FastLanguageModel.from_pretrained(
                    model_name=base_model,
                    max_seq_length=max_seq_length,
                    dtype=torch.float32 if device_type == "cpu" else None,
                    load_in_4bit=False,
                )
            update("✓ Baz model yüklendi", 0.35)
        except Exception as e:
            raise RuntimeError(f"Model yüklenemedi: {e}\n\nModel adı doğru mu?")
        
        # 5. LoRA
        update("🔧 LoRA adaptörleri ekleniyor...", 0.4)
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                           "gate_proj", "up_proj", "down_proj"],
            lora_alpha=16,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=3407,
        )
        update("✓ LoRA hazır", 0.45)
        
        # 6. Dataset
        update("📝 Dataset formatlanıyor...", 0.5)
        dataset = Dataset.from_list(training_data)
        
        def formatting_func(examples):
            texts = []
            for instruction, input_text, output in zip(
                examples["instruction"], examples["input"], examples["output"]
            ):
                text = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
                texts.append(text)
            return {"text": texts}
        
        dataset = dataset.map(formatting_func, batched=True)
        update(f"✓ Dataset hazır: {len(dataset)} örnek", 0.55)
        
        # 7. Donanıma göre parametreleri ayarla
        if device_type == "cpu":
            batch_size = min(batch_size, 1)
            max_steps = min(max_steps, 20)
        elif device_type in ["hip", "mps"]:
            batch_size = min(batch_size, 1)
            max_steps = min(max_steps, 30)
        
        import torch
        output_dir = f"./finetune_output/{new_model_name}"

        # Custom callback for real-time metrics
        manager_ref = self
        
        class LiveMetricsCallback(TrainerCallback):
            def on_log(self, args, state, control, logs=None, **kwargs):
                if logs and state:
                    step = state.global_step
                    total = state.max_steps
                    loss = logs.get("loss", "?")
                    lr_val = logs.get("learning_rate", "?")
                    pct = 0.6 + (0.35 * step / total) if total > 0 else 0.6
                    update(f"📊 Step {step}/{total} | Loss: {loss} | LR: {lr_val}", pct)
            
            def on_step_end(self, args, state, control, **kwargs):
                if manager_ref._cancel_training:
                    control.should_training_stop = True
                    update("⚠️ Eğitim iptal ediliyor...", None)
                return control
        
        update(f"⚙️ Eğitim başlatılıyor (lr={learning_rate}, steps={max_steps}, batch={batch_size})...", 0.6)
        
        trainer = SFTTrainer(
            model=model,
            tokenizer=tokenizer,
            train_dataset=dataset,
            dataset_text_field="text",
            max_seq_length=max_seq_length,
            callbacks=[LiveMetricsCallback()],
            args=TrainingArguments(
                per_device_train_batch_size=batch_size,
                gradient_accumulation_steps=4,
                warmup_steps=5,
                max_steps=max_steps,
                learning_rate=learning_rate,
                fp16=False if device_type == "cpu" else (not torch.cuda.is_bf16_supported()),
                bf16=False if device_type in ["cpu", "mps"] else torch.cuda.is_bf16_supported(),
                logging_steps=max(1, max_steps // 10),
                optim="adamw_8bit" if device_type == "cuda" else "adamw_torch",
                weight_decay=0.01,
                lr_scheduler_type="linear",
                seed=3407,
                output_dir=output_dir,
                save_strategy="steps",
                save_steps=max(1, max_steps // 2),
            ),
        )
        
        # 8. Eğitim
        try:
            trainer.train()
            if self._cancel_training:
                update("⚠️ Eğitim iptal edildi.", None)
                raise RuntimeError("Eğitim kullanıcı tarafından iptal edildi.")
            update("✓ Eğitim tamamlandı!", 0.95)
        except RuntimeError as e:
            if "iptal" in str(e).lower():
                raise
            raise RuntimeError(f"Eğitim sırasında hata:\n{e}")
        
        # 9. Kaydet
        update("💾 Model kaydediliyor...", 0.96)
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        
        # 10. Ollama'ya ekle
        update("🔄 Ollama formatına çevriliyor...", 0.98)
        try:
            model.save_pretrained_gguf(output_dir, tokenizer, quantization_method="q4_k_m")
            gguf_file = f"{output_dir}/{new_model_name}.gguf"
            
            modelfile_content = f"FROM {gguf_file}\nPARAMETER temperature 0.7\nPARAMETER top_p 0.9\n"
            modelfile_path = f"{output_dir}/Modelfile"
            with open(modelfile_path, "w") as f:
                f.write(modelfile_content)
            
            import subprocess
            subprocess.run(["ollama", "create", new_model_name, "-f", modelfile_path], check=True)
            update(f"✓ Ollama'ya eklendi: {new_model_name}", 1.0)
        except Exception as e:
            update(f"⚠️ Ollama'ya eklenemedi (manuel ekleyebilirsiniz): {e}", 1.0)
        
        return (
            f"✅ Fine-Tuning BAŞARILI!\n\n"
            f"Model: {new_model_name}\n"
            f"Konum: {output_dir}\n"
            f"Eğitim örnekleri: {len(training_data)}\n"
            f"Steps: {max_steps} | LR: {learning_rate}\n\n"
            f"Kullanım: ollama run {new_model_name}"
        )

    # === YARDIMCI FONKSİYONLAR ===
    
    def _load_files(self, file_paths, progress_callback=None):
        from langchain_community.document_loaders import (
            TextLoader, PyPDFLoader, Docx2txtLoader, UnstructuredExcelLoader
        )
        
        documents = []
        total = len(file_paths)
        
        for i, file_path in enumerate(file_paths):
            ext = os.path.splitext(file_path)[1].lower()
            fname = os.path.basename(file_path)
            loader = None
            
            if progress_callback:
                pct = (i / total) * 0.3 + 0.1  # 10%-40% arası
                progress_callback(f"📄 [{i+1}/{total}] {fname} okunuyor...", pct)
            
            try:
                if ext == ".txt":
                    loader = TextLoader(file_path, encoding="utf-8")
                elif ext == ".pdf":
                    loader = PyPDFLoader(file_path)
                elif ext in [".docx", ".doc"]:
                    loader = Docx2txtLoader(file_path)
                elif ext in [".xlsx", ".xls"]:
                    loader = UnstructuredExcelLoader(file_path)
                elif ext == ".csv":
                    try:
                        from langchain_community.document_loaders import CSVLoader
                        loader = CSVLoader(file_path, encoding="utf-8")
                    except:
                        loader = TextLoader(file_path, encoding="utf-8")
                elif ext in [".json", ".jsonl"]:
                    # JSON / JSONL doğrudan okunur
                    from langchain_core.documents import Document
                    import json
                    with open(file_path, "r", encoding="utf-8") as jf:
                        try:
                            jdata = json.load(jf)
                            if isinstance(jdata, list):
                                for item in jdata:
                                    content = json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item)
                                    documents.append(Document(page_content=content, metadata={"source": file_path}))
                            elif isinstance(jdata, dict):
                                documents.append(Document(page_content=json.dumps(jdata, ensure_ascii=False), metadata={"source": file_path}))
                        except:
                            # JSONL olarak dene
                            jf.seek(0)
                            for line in jf:
                                line = line.strip()
                                if line:
                                    documents.append(Document(page_content=line, metadata={"source": file_path}))
                
                if loader:
                    documents.extend(loader.load())
                elif ext not in [".json", ".jsonl"]:
                    if progress_callback:
                        progress_callback(f"⚠️ Desteklenmeyen format: {fname}", None)
            
            except Exception as e:
                if progress_callback:
                    progress_callback(f"❌ '{fname}' okunamadı: {e}", None)
                logger.error(f"HATA - '{fname}' okunamadı: {e}")
        
        return documents

    def delete_model(self, model_name):
        model_path = os.path.join(self.db_dir, model_name)
        if os.path.exists(model_path):
            shutil.rmtree(model_path)
            logger.info(f"Model silindi: {model_name}")
            return True
        return False

    # === RAG DOKÜMAN YÖNETİMİ ===

    def list_rag_documents(self, model_name):
        """Bir RAG modelinin içindeki doküman kaynaklarını ve parça sayılarını listeler."""
        from langchain_community.vectorstores import Chroma
        model_path = os.path.join(self.db_dir, model_name)
        if not os.path.exists(model_path):
            return []
        try:
            vectordb = Chroma(
                persist_directory=model_path,
                embedding_function=self.embedding_function
            )
            data = vectordb.get()
            metadatas = data.get("metadatas", []) or []
            sources = {}
            for meta in metadatas:
                if meta and "source" in meta:
                    src = os.path.basename(meta["source"])
                    sources[src] = sources.get(src, 0) + 1
            
            doc_list = [{"filename": k, "chunk_count": v} for k, v in sources.items()]
            doc_list.sort(key=lambda x: x["filename"].lower())
            return doc_list
        except Exception as e:
            logger.error(f"RAG doküman listeleme hatası ({model_name}): {e}")
            return []

    def delete_rag_document(self, model_name, document_name):
        """Belirli bir dosyanın chunk'larını RAG bilgi bankasından çıkarır."""
        from langchain_community.vectorstores import Chroma
        model_path = os.path.join(self.db_dir, model_name)
        if not os.path.exists(model_path):
            return False, "Model bulunamadı"
        try:
            vectordb = Chroma(
                persist_directory=model_path,
                embedding_function=self.embedding_function
            )
            data = vectordb.get()
            ids = data.get("ids", []) or []
            metadatas = data.get("metadatas", []) or []
            
            ids_to_delete = []
            for doc_id, meta in zip(ids, metadatas):
                if meta and "source" in meta:
                    if os.path.basename(meta["source"]) == document_name or meta["source"] == document_name:
                        ids_to_delete.append(doc_id)
            
            if ids_to_delete:
                vectordb.delete(ids=ids_to_delete)
                logger.info(f"'{document_name}' dosyasına ait {len(ids_to_delete)} parça '{model_name}' modelinden silindi.")
                return True, f"'{document_name}' dosyasına ait {len(ids_to_delete)} parça silindi."
            return False, "Eşleşen doküman bulunamadı."
        except Exception as e:
            logger.error(f"RAG doküman silme hatası ({model_name}, {document_name}): {e}")
            return False, str(e)
