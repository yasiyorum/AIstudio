import os
import json
import datetime

class SimpleMemory:
    """
    Sohbet geçmişini yönetir ve JSON dosyasına kaydeder.
    Her model için ayrı dosya tutar.
    """
    def __init__(self, model_name="genel"):
        self.history_dir = "chat_history"
        os.makedirs(self.history_dir, exist_ok=True)
        
        # Dosya adını temizle (güvenli hale getir)
        safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in model_name)
        self.file_path = os.path.join(self.history_dir, f"{safe_name}.json")
        self.chat_memory = self._load_from_file()

    def _load_from_file(self):
        """Dosyadan geçmişi yükle"""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def save_context(self, inputs, outputs):
        """Sohbet kaydet ve dosyaya yaz"""
        input_text = inputs.get("input") or inputs.get("question")
        output_text = outputs.get("output") or outputs.get("answer")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if input_text:
            self.chat_memory.append({
                "role": "human", 
                "content": input_text, 
                "time": timestamp
            })
        
        if output_text:
            self.chat_memory.append({
                "role": "ai", 
                "content": output_text, 
                "time": timestamp
            })
        
        # Dosyaya kaydet
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.chat_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Sohbet geçmişi kaydedilemedi: {e}")

    def load_memory_variables(self, inputs):
        """LangChain uyumluluğu için"""
        return {"chat_history": self.chat_memory}

    def clear(self):
        """Geçmişi temizle"""
        self.chat_memory = []
        if os.path.exists(self.file_path):
            os.remove(self.file_path)


class ChatEngine:
    """
    Sohbet motoru - RAG veya direkt Ollama modelleri ile konuşur.
    """
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.retriever = None
        self.llm = None
        self.model_name = None
        self.memory = SimpleMemory("genel")
        self.is_rag = False

    def load_model(self, model_name, api_key=None, provider="ollama", status_callback=None, preferred_rag_model=None):
        """
        Model yükle (RAG veya Native Ollama).
        status_callback: İlerleme mesajları göstermek için fonksiyon
        preferred_rag_model: RAG için tercih edilen model (None = otomatik)
        """
        # Lazy imports
        from langchain_community.vectorstores import Chroma
        from langchain_community.chat_models import ChatOpenAI, ChatOllama
        
        def update_status(msg):
            if status_callback:
                status_callback(msg)
            print(msg)
        
        self.model_name = model_name
        self.memory = SimpleMemory(model_name=model_name)
        
        # RAG modeli mi kontrol et
        model_path = os.path.join("models_db", model_name)
        self.is_rag = os.path.exists(model_path)
        
        # RAG ise vektör veritabanını yükle
        if self.is_rag:
            try:
                vectordb = Chroma(
                    persist_directory=model_path,
                    embedding_function=self.model_manager.embedding_function
                )
                self.retriever = vectordb.as_retriever(search_kwargs={"k": 3})
            except Exception as e:
                return False, f"Bilgi bankası yüklenemedi: {str(e)}"
        else:
            self.retriever = None
        
        # LLM yükle
        target_model = "deepseek-r1:1.5b"  # RAG için varsayılan
        
        if not self.is_rag:
            # Native model - modelin kendisi LLM
            target_model = model_name
            provider = "ollama"  # Zorla ollama
        
        try:
            if provider == "openai" and api_key:
                self.llm = ChatOpenAI(
                    openai_api_key=api_key, 
                    temperature=0.7,
                    model="gpt-3.5-turbo"
                )
                update_status("✓ OpenAI bağlantısı kuruldu")
                
            elif provider == "ollama":
                import ollama
                
                # RAG için akıllı model seçimi
                if self.is_rag:
                    # Kullanıcı tercihini kontrol et
                    if preferred_rag_model and preferred_rag_model != "Otomatik (En iyi model)":
                        update_status(f"🎯 Seçilen model: {preferred_rag_model}")
                        target_model = preferred_rag_model
                    else:
                        # Otomatik mod
                        update_status("🔍 Uygun Ollama modeli aranıyor...")
                        print("DEBUG: Starting RAG model selection...")
                        
                        try:
                            model_list = ollama.list()
                            print(f"DEBUG: Model list response: {model_list}")
                            # Ollama kütüphanesi Model objesi döndürüyor, dict değil
                            available_models = [m.model for m in model_list.get('models', [])]
                            print(f"DEBUG: Available models: {available_models}")
                        except Exception as e:
                            print(f"DEBUG ERROR: Failed to list models: {e}")
                            import traceback
                            traceback.print_exc()
                            return False, f"❌ Ollama'ya bağlanılamadı!\n\nOllama çalışıyor mu kontrol edin:\n- Terminal: ollama serve\n\nHata: {e}"
                        
                        # Tercih sırası
                        preferred_models = [
                            "deepseek-r1:1.5b",
                            "deepseek-r1",
                            "llama3.2",
                            "llama3",
                            "phi3",
                            "mistral"
                        ]
                        
                        selected_model = None
                        
                        # Önce mevcut modellerde ara
                        for pref in preferred_models:
                            for avail in available_models:
                                if pref in avail.lower():
                                    selected_model = avail
                                    update_status(f"✓ Mevcut model bulundu: {selected_model}")
                                    print(f"DEBUG: Selected model: {selected_model}")
                                    break
                            if selected_model:
                                break
                        
                        # Hiç uygun model yok - ilk modeli kullan
                        if not selected_model:
                            if available_models:
                                selected_model = available_models[0]
                                update_status(f"ℹ️ Varsayılan model kullanılıyor: {selected_model}")
                                print(f"DEBUG: Using first available: {selected_model}")
                            else:
                                update_status("📥 Hiç model bulunamadı, llama3 indiriliyor...")
                                try:
                                    ollama.pull("llama3")
                                    selected_model = "llama3"
                                    update_status("✓ llama3 başarıyla indirildi!")
                                except Exception as e:
                                    print(f"DEBUG ERROR: Pull failed: {e}")
                                    return False, f"❌ Model indirilemedi!\n\nManuel: ollama pull llama3\n\nHata: {e}"
                        
                        target_model = selected_model
                
                # Native model için direkt kullan
                else:
                    update_status(f"ℹ️ Native model kullanılıyor: {target_model}")
                    print(f"DEBUG: Using native model: {target_model}")
                
                # LLM'i başlat
                print(f"DEBUG: Attempting to start ChatOllama with model: {target_model}")
                try:
                    self.llm = ChatOllama(model=target_model, temperature=0.7)
                    update_status(f"✓ Model yüklendi: {target_model}")
                    print(f"DEBUG: ChatOllama started successfully")
                except Exception as e:
                    print(f"DEBUG ERROR: ChatOllama init failed: {e}")
                    import traceback
                    traceback.print_exc()
                    return False, f"❌ Model başlatılamadı: {target_model}\n\nHata detayı:\n{e}\n\nOllama serve çalışıyor mu?"
            
            else:
                # Fallback: Demo modu
                from langchain_community.llms import FakeListLLM
                self.llm = FakeListLLM(responses=[
                    "🤖 [DEMO MODU]\n\nBir AI motoru seçmelisiniz:\n• Ayarlar → 'Local AI (Ollama)'\n• Ayarlar → 'OpenAI' → API anahtarı girin"
                ])
                update_status("⚠️ Demo modunda çalışıyor")
        
        except Exception as e:
            return False, f"❌ Beklenmeyen hata:\n{str(e)}\n\nOllama kurulu ve çalışıyor mu?\nKontrol: ollama list"
        
        return True, f"✓ '{model_name}' yüklendi"

    def chat(self, user_input):
        """
        Kullanıcı mesajına cevap ver.
        """
        if not self.llm:
            return "❌ Önce bir model yükleyin!"
        
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            
            # 1. Bilgi al (sadece RAG ise)
            context_text = ""
            docs = []
            
            if self.retriever:
                try:
                    docs = self.retriever.invoke(user_input)
                except:
                    docs = self.retriever.get_relevant_documents(user_input)
                
                context_text = "\n\n".join([d.page_content for d in docs])
            
            # 2. Prompt hazırla
            if self.is_rag and context_text:
                system_prompt = f"""Sen bir asistansın. Aşağıdaki bilgilere dayanarak cevap ver:

{context_text}

Eğer soruyu bu bilgilerle cevaplayamazsan, bunu söyle."""
            else:
                # Native model - kendi system prompt'u var
                system_prompt = "Sen yardımcı bir asistansın."
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ]
            
            # 3. Cevap al
            try:
                response_msg = self.llm.invoke(messages)
                answer = response_msg.content if hasattr(response_msg, 'content') else str(response_msg)
            except AttributeError:
                # Eski API
                response_msg = self.llm(messages)
                answer = str(response_msg)
            
            # 4. Kaynakları ekle (RAG ise)
            if docs and self.is_rag:
                sources = list(set([
                    os.path.basename(doc.metadata.get('source', '?')) 
                    for doc in docs
                ]))
                if sources:
                    answer += f"\n\n📚 Kaynaklar: {', '.join(sources)}"
            
            # 5. Geçmişe kaydet
            self.memory.save_context(
                {"input": user_input}, 
                {"output": answer}
            )
            
            return answer
        
        except Exception as e:
            error_msg = f"❌ Hata: {str(e)}"
            print(f"Chat error: {e}")
            import traceback
            traceback.print_exc()
            return error_msg

    def get_history_file(self):
        """Geçmiş dosyasının yolunu döndür"""
        return self.memory.file_path if self.memory else None

    def clear_history(self):
        """Mevcut modelin geçmişini temizle"""
        if self.memory:
            self.memory.clear()
            return "✓ Sohbet geçmişi temizlendi"
        return "❌ Aktif model yok"
