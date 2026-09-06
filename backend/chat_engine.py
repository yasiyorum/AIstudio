import os
import json
import datetime
import threading
import uuid
from backend.logger import logger


class SimpleMemory:
    """
    Sohbet geçmişini yönetir ve JSON dosyasına kaydeder.
    Her sohbet oturumu için benzersiz dosya tutar.
    """
    # Proje kök dizini (script konumuna göre)
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def __init__(self, model_name="genel", session_id=None):
        self.history_dir = os.path.join(self._BASE_DIR, "chat_history")
        os.makedirs(self.history_dir, exist_ok=True)
        
        self.model_name = model_name
        safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in model_name)
        
        # Her sohbet oturumu benzersiz bir ID alır
        if session_id:
            self.session_id = session_id
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            short_id = uuid.uuid4().hex[:6]
            self.session_id = f"{timestamp}_{short_id}"
        
        self.file_path = os.path.join(self.history_dir, f"{safe_name}_{self.session_id}.json")
        self.chat_memory = self._load_from_file()

    def _load_from_file(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data.get("messages", [])
                    return data
            except:
                return []
        return []

    def save_context(self, inputs, outputs):
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
        
        self._save_to_file()

    def _save_to_file(self):
        """Sohbeti JSON dosyasına kaydet (metadata ile birlikte)."""
        try:
            data = {
                "model_name": self.model_name,
                "session_id": self.session_id,
                "created_at": self.chat_memory[0]["time"] if self.chat_memory else "",
                "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message_count": len(self.chat_memory),
                "messages": self.chat_memory
            }
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Sohbet geçmişi kaydedilemedi: {e}")

    def load_memory_variables(self, inputs):
        return {"chat_history": self.chat_memory}

    def clear(self):
        self.chat_memory = []
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

    @classmethod
    def list_all_sessions(cls):
        """Tüm sohbet oturumlarını listele, en yenisi en üstte."""
        history_dir = os.path.join(cls._BASE_DIR, "chat_history")
        if not os.path.exists(history_dir):
            return []
        
        sessions = []
        for filename in os.listdir(history_dir):
            if not filename.endswith('.json'):
                continue
            filepath = os.path.join(history_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Yeni format (dict with metadata)
                if isinstance(data, dict):
                    model_name = data.get("model_name", "bilinmeyen")
                    session_id = data.get("session_id", "")
                    created_at = data.get("created_at", "")
                    updated_at = data.get("updated_at", created_at)
                    messages = data.get("messages", [])
                    msg_count = data.get("message_count", len(messages))
                # Eski format (sadece liste) — geriye uyumluluk
                elif isinstance(data, list):
                    messages = data
                    msg_count = len(messages)
                    # Dosya adından model adını çıkar
                    base = filename.replace('.json', '')
                    model_name = base
                    session_id = ""
                    created_at = messages[0].get("time", "") if messages else ""
                    updated_at = messages[-1].get("time", "") if messages else ""
                else:
                    continue
                
                if not messages:
                    continue
                
                # İlk mesajdan önizleme al
                preview = messages[0].get('content', '')[:50]
                if len(messages[0].get('content', '')) > 50:
                    preview += "..."
                
                sessions.append({
                    "filename": filename,
                    "filepath": filepath,
                    "model_name": model_name,
                    "session_id": session_id,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "message_count": msg_count,
                    "preview": preview,
                    "messages": messages
                })
            except Exception as e:
                print(f"Sohbet dosyası okunamadı ({filename}): {e}")
                continue
        
        # En yeni güncellenen en üstte
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return sessions

    @classmethod
    def load_session(cls, filepath):
        """Belirli bir sohbet dosyasını yükle, SimpleMemory nesnesi döndür."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                model_name = data.get("model_name", "genel")
                session_id = data.get("session_id", "")
                messages = data.get("messages", [])
            elif isinstance(data, list):
                messages = data
                base = os.path.basename(filepath).replace('.json', '')
                model_name = base
                session_id = ""
            else:
                return None
            
            memory = cls.__new__(cls)
            memory.history_dir = os.path.join(cls._BASE_DIR, "chat_history")
            memory.model_name = model_name
            memory.session_id = session_id
            memory.file_path = filepath
            memory.chat_memory = messages
            return memory
        except Exception as e:
            print(f"Sohbet yüklenemedi: {e}")
            return None


class ChatEngine:
    """
    Sohbet motoru - RAG veya direkt Ollama modelleri ile konuşur.
    Streaming desteği ve threading-safe tasarım.
    """
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.retriever = None
        self.llm = None
        self.model_name = None
        self.memory = SimpleMemory("genel")
        self.is_rag = False
        self._loading = False
        self._cancel_requested = False
        self._cancel_stream = False

    @property
    def is_loading(self):
        return self._loading

    def cancel_loading(self):
        self._cancel_requested = True

    def stop_stream(self):
        """Devam eden streaming yanıtını durdur."""
        self._cancel_stream = True
        logger.info("Streaming yanıtı durdurma talebi alındı.")

    def new_session(self, model_name=None):
        """Yeni bir sohbet oturumu başlat (mevcut model korunur)."""
        name = model_name or self.model_name or "genel"
        self.memory = SimpleMemory(model_name=name)
        return self.memory.session_id

    def load_session(self, filepath):
        """Var olan bir sohbet oturumunu yükle."""
        loaded = SimpleMemory.load_session(filepath)
        if loaded:
            self.memory = loaded
            return True
        return False

    def load_model_async(self, model_name, api_key=None, provider="ollama", 
                          status_callback=None, done_callback=None, preferred_rag_model=None):
        """
        Model yüklemeyi arka planda başlat. UI donmaz.
        done_callback(success: bool, message: str) — tamamlandığında çağrılır
        """
        self._loading = True
        self._cancel_requested = False

        def worker():
            try:
                success, msg = self.load_model(
                    model_name, api_key=api_key, provider=provider,
                    status_callback=status_callback,
                    preferred_rag_model=preferred_rag_model
                )
                if done_callback:
                    done_callback(success, msg)
            except Exception as e:
                if done_callback:
                    done_callback(False, f"❌ Beklenmeyen hata: {str(e)}")
            finally:
                self._loading = False

        threading.Thread(target=worker, daemon=True).start()

    def load_model(self, model_name, api_key=None, provider="ollama", 
                   status_callback=None, preferred_rag_model=None):
        """
        Model yükle (RAG veya Native Ollama).
        """
        from langchain_community.vectorstores import Chroma
        from langchain_community.chat_models import ChatOpenAI, ChatOllama
        
        def update_status(msg):
            if status_callback:
                status_callback(msg)
            print(msg)
        
        self.model_name = model_name
        # Yeni oturum başlat (eğer mevcut memory farklı modele aitse)
        if not self.memory or self.memory.model_name != model_name:
            self.memory = SimpleMemory(model_name=model_name)
        
        model_path = os.path.join(self._BASE_DIR, "models_db", model_name)
        self.is_rag = os.path.exists(model_path)
        
        if self._cancel_requested:
            return False, "⚠️ Yükleme iptal edildi."
        
        # RAG ise vektör veritabanını yükle
        if self.is_rag:
            update_status("📂 Bilgi bankası yükleniyor...")
            try:
                vectordb = Chroma(
                    persist_directory=model_path,
                    embedding_function=self.model_manager.embedding_function
                )
                self.retriever = vectordb.as_retriever(search_kwargs={"k": 3})
                update_status("✓ Bilgi bankası hazır")
            except Exception as e:
                return False, f"Bilgi bankası yüklenemedi: {str(e)}"
        else:
            self.retriever = None
        
        if self._cancel_requested:
            return False, "⚠️ Yükleme iptal edildi."
        
        # LLM yükle
        is_cloud = provider in ["openai", "google", "anthropic"]
        target_model = model_name

        if not is_cloud:
            provider = "ollama"
            if self.is_rag:
                target_model = preferred_rag_model or "deepseek-r1:1.5b"
            else:
                target_model = model_name

        try:
            if provider == "openai":
                if not api_key:
                    return False, "❌ OpenAI için API anahtarı gerekli! (Ayarlar sayfasından girin)"
                update_status("☁️ OpenAI'ya bağlanılıyor...")
                openai_model = model_name if (model_name and model_name.startswith("gpt-")) else "gpt-4o-mini"
                self.llm = ChatOpenAI(
                    openai_api_key=api_key, 
                    temperature=0.7,
                    model=openai_model
                )
                update_status(f"✓ OpenAI bağlantısı kuruldu ({openai_model})")
                
            elif provider == "google":
                if not api_key:
                    return False, "❌ Google AI için API anahtarı gerekli! (Ayarlar sayfasından girin)"
                update_status("☁️ Google AI'ya bağlanılıyor...")
                try:
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    google_model = model_name if (model_name and "gemini" in model_name.lower()) else "gemini-1.5-flash"
                    self.llm = ChatGoogleGenerativeAI(
                        model=google_model,
                        google_api_key=api_key,
                        temperature=0.7
                    )
                    update_status(f"✓ Google AI bağlantısı kuruldu ({google_model})")
                except ImportError:
                    return False, "❌ Google AI kütüphanesi kurulu değil!\npip install langchain-google-genai"
                    
            elif provider == "anthropic":
                if not api_key:
                    return False, "❌ Anthropic için API anahtarı gerekli! (Ayarlar sayfasından girin)"
                update_status("☁️ Anthropic'e bağlanılıyor...")
                try:
                    from langchain_anthropic import ChatAnthropic
                    claude_model = model_name if (model_name and "claude" in model_name.lower()) else "claude-3-haiku-20240307"
                    self.llm = ChatAnthropic(
                        model=claude_model,
                        anthropic_api_key=api_key,
                        temperature=0.7
                    )
                    update_status(f"✓ Anthropic bağlantısı kuruldu ({claude_model})")
                except ImportError:
                    return False, "❌ Anthropic kütüphanesi kurulu değil!\npip install langchain-anthropic"
                
            elif provider == "ollama":
                import ollama
                
                if self.is_rag:
                    if preferred_rag_model and preferred_rag_model != "Otomatik (En iyi model)":
                        update_status(f"🎯 Seçilen model: {preferred_rag_model}")
                        target_model = preferred_rag_model
                    else:
                        update_status("🔍 Uygun Ollama modeli aranıyor...")
                        try:
                            model_list = ollama.list()
                            available_models = [m.model for m in model_list.get('models', [])]
                        except Exception as e:
                            return False, f"❌ Ollama'ya bağlanılamadı!\n\nollama serve komutuyla başlatın.\n\nHata: {e}"
                        
                        preferred_models = [
                            "deepseek-r1:1.5b", "deepseek-r1", "llama3.2",
                            "llama3", "phi3", "mistral"
                        ]
                        
                        selected_model = None
                        for pref in preferred_models:
                            for avail in available_models:
                                if pref in avail.lower():
                                    selected_model = avail
                                    break
                            if selected_model:
                                break
                        
                        if not selected_model:
                            if available_models:
                                selected_model = available_models[0]
                                update_status(f"ℹ️ Varsayılan model: {selected_model}")
                            else:
                                update_status("📥 Model bulunamadı, llama3 indiriliyor...")
                                try:
                                    ollama.pull("llama3")
                                    selected_model = "llama3"
                                    update_status("✓ llama3 indirildi!")
                                except Exception as e:
                                    return False, f"❌ Model indirilemedi!\n\nManuel: ollama pull llama3\n\nHata: {e}"
                        
                        target_model = selected_model
                        update_status(f"✓ Model bulundu: {target_model}")
                else:
                    update_status(f"🔄 Model yükleniyor: {target_model}")
                
                if self._cancel_requested:
                    return False, "⚠️ Yükleme iptal edildi."
                
                try:
                    self.llm = ChatOllama(model=target_model, temperature=0.7)
                    update_status(f"✓ Model hazır: {target_model}")
                except Exception as e:
                    return False, f"❌ Model başlatılamadı: {target_model}\n\nHata: {e}\n\nOllama serve çalışıyor mu?"
            
            else:
                from langchain_community.llms import FakeListLLM
                self.llm = FakeListLLM(responses=[
                    "🤖 [DEMO MODU]\n\nBir AI motoru seçmelisiniz:\n• Ayarlar → 'Ollama'\n• veya API anahtarı girin"
                ])
                update_status("⚠️ Demo modunda çalışıyor")
        
        except Exception as e:
            return False, f"❌ Beklenmeyen hata:\n{str(e)}\n\nOllama kurulu ve çalışıyor mu?"
        
        return True, f"✓ '{model_name}' yüklendi ve kullanıma hazır"

    # Proje kök dizini (model_path için)
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def chat(self, user_input):
        """Kullanıcı mesajına cevap ver."""
        if not self.llm:
            return "❌ Önce bir model yükleyin!"
        
        answer = None
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            
            context_text = ""
            docs = []
            
            if self.retriever:
                try:
                    docs = self.retriever.invoke(user_input)
                except:
                    docs = self.retriever.get_relevant_documents(user_input)
                context_text = "\n\n".join([d.page_content for d in docs])
            
            if self.is_rag and context_text:
                system_prompt = f"""Sen bir asistansın. Aşağıdaki bilgilere dayanarak cevap ver:

{context_text}

Eğer soruyu bu bilgilerle cevaplayamazsan, bunu söyle."""
            else:
                system_prompt = "Sen yardımcı bir asistansın."
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ]
            
            try:
                response_msg = self.llm.invoke(messages)
                answer = response_msg.content if hasattr(response_msg, 'content') else str(response_msg)
            except AttributeError:
                response_msg = self.llm(messages)
                answer = str(response_msg)
            
            if docs and self.is_rag:
                sources = list(set([
                    os.path.basename(doc.metadata.get('source', '?')) 
                    for doc in docs
                ]))
                if sources:
                    answer += f"\n\n📚 Kaynaklar: {', '.join(sources)}"
            
            return answer
        
        except Exception as e:
            answer = f"❌ Hata: {str(e)}"
            print(f"Chat error: {e}")
            import traceback
            traceback.print_exc()
            return answer
        finally:
            # Her durumda sohbeti kaydet
            if answer:
                try:
                    self.memory.save_context(
                        {"input": user_input}, 
                        {"output": answer}
                    )
                except Exception as save_err:
                    print(f"⚠️ Sohbet kaydedilemedi: {save_err}")

    def chat_stream(self, user_input, chunk_callback=None):
        """
        Streaming sohbet — her token geldiğinde chunk_callback çağrılır.
        Fallback: streaming yoksa normal chat kullan.
        """
        if not self.llm:
            if chunk_callback:
                chunk_callback("❌ Önce bir model yükleyin!", done=True)
            return "❌ Önce bir model yükleyin!"
        
        try:
            from langchain_core.messages import SystemMessage, HumanMessage
            
            context_text = ""
            docs = []
            
            if self.retriever:
                try:
                    docs = self.retriever.invoke(user_input)
                except:
                    docs = self.retriever.get_relevant_documents(user_input)
                context_text = "\n\n".join([d.page_content for d in docs])
            
            if self.is_rag and context_text:
                system_prompt = f"""Sen bir asistansın. Aşağıdaki bilgilere dayanarak cevap ver:

{context_text}

Eğer soruyu bu bilgilerle cevaplayamazsan, bunu söyle."""
            else:
                system_prompt = "Sen yardımcı bir asistansın."
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_input)
            ]
            
            # Try streaming first
            self._cancel_stream = False
            full_answer = ""
            try:
                for chunk in self.llm.stream(messages):
                    if self._cancel_stream:
                        logger.info("Streaming kullanıcı tarafından durduruldu.")
                        stop_notice = "\n\n⏹ *[Yanıt durduruldu]*"
                        full_answer += stop_notice
                        if chunk_callback:
                            chunk_callback(stop_notice, done=True)
                        break
                    token = chunk.content if hasattr(chunk, 'content') else str(chunk)
                    full_answer += token
                    if chunk_callback:
                        chunk_callback(token, done=False)
            except (AttributeError, NotImplementedError):
                # Fallback to non-streaming
                full_answer = self.chat(user_input)
                if chunk_callback:
                    chunk_callback(full_answer, done=True)
                return full_answer
            
            # Add sources
            if docs and self.is_rag:
                sources = list(set([
                    os.path.basename(doc.metadata.get('source', '?')) 
                    for doc in docs
                ]))
                if sources:
                    source_text = f"\n\n📚 Kaynaklar: {', '.join(sources)}"
                    full_answer += source_text
                    if chunk_callback:
                        chunk_callback(source_text, done=False)
            
            if chunk_callback:
                chunk_callback("", done=True)
            
            self.memory.save_context(
                {"input": user_input},
                {"output": full_answer}
            )
            
            return full_answer
        
        except Exception as e:
            error_msg = f"❌ Hata: {str(e)}"
            if chunk_callback:
                chunk_callback(error_msg, done=True)
            return error_msg

    def get_history_file(self):
        return self.memory.file_path if self.memory else None

    def clear_history(self):
        if self.memory:
            self.memory.clear()
            return "✓ Sohbet geçmişi temizlendi"
        return "❌ Aktif model yok"
