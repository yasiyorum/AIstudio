import os
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import datetime
from backend.model_manager import ModelManager
from backend.chat_engine import ChatEngine, SimpleMemory
from backend.config_manager import ConfigManager
from backend.logger import logger
from ui.theme import *
from ui.widgets import ChatBubble, TypingIndicator, LoadingOverlay, TrainingLogPanel, InfoTooltip


class App(ctk.CTk):
    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def __init__(self):
        super().__init__()

        self.title("AI Stüdyosu")
        self.geometry("1400x850")
        self.minsize(1000, 650)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=BG_PRIMARY)

        # Backend
        self.config_manager = ConfigManager()
        self.model_manager = ModelManager()
        self.chat_engine = ChatEngine(self.model_manager)
        
        # State
        self.files_to_train = []
        self.history_visible = False
        self._loading_overlay = None
        self._typing_indicator = None
        self._pending_history_filepath = None  # Geçmiş sohbet yükleme için
        self._is_generating = False

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_pages()
        self.show_page("chat")
        
        threading.Thread(target=self._check_ollama, daemon=True).start()

    def _check_ollama(self):
        try:
            import ollama
            result = ollama.list()
            if 'models' in result:
                count = len(result['models'])
                self.after(0, lambda: self.ollama_indicator.configure(
                    text=f"● Ollama: aktif ({count} model)", text_color=ACCENT_SUCCESS
                ))
            else:
                self.after(0, lambda: self.ollama_indicator.configure(
                    text="○ Ollama: model yok", text_color=ACCENT_WARNING
                ))
        except:
            self.after(0, lambda: self.ollama_indicator.configure(
                text="○ Ollama: kapalı", text_color=ACCENT_DANGER
            ))

    # ═══════════════════════════════════════════════════════════
    #  SIDEBAR
    # ═══════════════════════════════════════════════════════════

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=SIDEBAR_BG,
                                      border_width=1, border_color=BORDER_SUBTLE)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)
        self.sidebar.grid_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(30, 25))
        
        ctk.CTkLabel(logo_frame, text="🤖", font=ctk.CTkFont(size=36)).pack()
        ctk.CTkLabel(logo_frame, text="AI Stüdyosu",
                     font=ctk.CTkFont(size=17, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(pady=(4, 0))
        ctk.CTkLabel(logo_frame, text="v2.0 Modern",
                     font=ctk.CTkFont(size=10),
                     text_color=TEXT_MUTED).pack()

        # Sidebar butonları
        btn_cfg = {"height": 44, "corner_radius": 10, "anchor": "w",
                   "font": ctk.CTkFont(size=13), "fg_color": "transparent",
                   "hover_color": BG_HOVER, "text_color": TEXT_SECONDARY}
        
        self.sidebar_btns = {}
        btns = [
            ("chat", "  💬  Sohbet", 1),
            ("models", "  🎓  Modellerim", 2),
            ("settings", "  ⚙️  Ayarlar", 3),
        ]
        for key, text, row in btns:
            btn = ctk.CTkButton(self.sidebar, text=text,
                                command=lambda k=key: self.show_page(k), **btn_cfg)
            btn.grid(row=row, column=0, padx=12, pady=4, sticky="ew")
            self.sidebar_btns[key] = btn

        # Ollama durumu
        self.ollama_indicator = ctk.CTkLabel(
            self.sidebar, text="○ Ollama: kontrol ediliyor...",
            font=ctk.CTkFont(size=FONT_TINY), text_color=TEXT_MUTED
        )
        self.ollama_indicator.grid(row=6, column=0, padx=15, pady=20, sticky="s")

    # ═══════════════════════════════════════════════════════════
    #  SAYFA YÖNETİMİ
    # ═══════════════════════════════════════════════════════════

    def _create_pages(self):
        self._create_chat_page()
        self._create_models_page()
        self._create_settings_page()

    def show_page(self, page_name):
        for key, btn in self.sidebar_btns.items():
            if key == page_name:
                btn.configure(fg_color=ACCENT_PRIMARY, text_color=TEXT_WHITE)
            else:
                btn.configure(fg_color="transparent", text_color=TEXT_SECONDARY)
        
        for page in [self.page_chat, self.page_models, self.page_settings]:
            page.grid_forget()
        
        if page_name == "chat":
            self.page_chat.grid(row=0, column=1, sticky="nsew")
            self.refresh_model_list()
        elif page_name == "models":
            self.page_models.grid(row=0, column=1, sticky="nsew")
        elif page_name == "settings":
            self.page_settings.grid(row=0, column=1, sticky="nsew")

    # ═══════════════════════════════════════════════════════════
    #  SOHBET SAYFASI
    # ═══════════════════════════════════════════════════════════

    def _create_chat_page(self):
        self.page_chat = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_PRIMARY)
        self.page_chat.grid_columnconfigure(1, weight=1)
        self.page_chat.grid_rowconfigure(0, weight=1)
        
        # Geçmiş sidebar (gizli)
        self.history_sidebar = ctk.CTkFrame(self.page_chat, width=280, corner_radius=12,
                                             fg_color=BG_SECONDARY, border_width=1,
                                             border_color=BORDER_COLOR)
        ctk.CTkLabel(self.history_sidebar, text="📜 Geçmiş Sohbetler",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(pady=15)
        self.history_list_frame = ctk.CTkScrollableFrame(self.history_sidebar,
                                                          fg_color="transparent")
        self.history_list_frame.pack(fill="both", expand=True, padx=8, pady=5)
        ctk.CTkButton(self.history_sidebar, text="🔄 Yenile",
                      command=self.refresh_history_list, height=32,
                      corner_radius=8, fg_color=BTN_SECONDARY,
                      hover_color=BTN_SECONDARY_HOVER).pack(fill="x", padx=8, pady=8)

        # Ana sohbet alanı
        chat_main = ctk.CTkFrame(self.page_chat, fg_color="transparent")
        chat_main.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        chat_main.grid_rowconfigure(1, weight=1)
        chat_main.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkFrame(chat_main, height=60, corner_radius=12,
                               fg_color=BG_SECONDARY, border_width=1,
                               border_color=BORDER_SUBTLE)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        
        self.history_toggle_btn = ctk.CTkButton(
            header, text="☰", width=42, height=42,
            command=self.toggle_history_sidebar,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            corner_radius=10, font=ctk.CTkFont(size=16)
        )
        self.history_toggle_btn.pack(side="left", padx=12, pady=9)
        
        ctk.CTkButton(
            header, text="✨ Yeni Sohbet", width=110, height=36,
            command=self.new_chat, fg_color=ACCENT_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER, corner_radius=8,
            font=ctk.CTkFont(size=12)
        ).pack(side="left", padx=(0, 10))
        
        sep = ctk.CTkFrame(header, width=1, height=30, fg_color=BORDER_COLOR)
        sep.pack(side="left", padx=8, pady=15)
        
        ctk.CTkLabel(header, text="Model:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=TEXT_SECONDARY).pack(side="left", padx=(8, 4))
        
        self.model_selector_var = ctk.StringVar(value="Model Seçiniz")
        self.model_dropdown = ctk.CTkOptionMenu(
            header, variable=self.model_selector_var, command=self.on_model_select,
            width=250, height=36, corner_radius=8,
            fg_color=BG_INPUT, button_color=ACCENT_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER,
            dropdown_fg_color=BG_CARD, dropdown_hover_color=BG_HOVER,
            font=ctk.CTkFont(size=12)
        )
        self.model_dropdown.pack(side="left", padx=4)
        
        ctk.CTkButton(header, text="🔄", width=36, height=36,
                      command=self.refresh_model_list,
                      fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
                      corner_radius=8).pack(side="left", padx=4)

        # Chat display (scrollable frame for bubbles)
        self.chat_scroll = ctk.CTkScrollableFrame(
            chat_main, fg_color=BG_PRIMARY, corner_radius=12,
            border_width=1, border_color=BORDER_SUBTLE,
            scrollbar_button_color=BORDER_COLOR,
            scrollbar_button_hover_color=ACCENT_PRIMARY
        )
        self.chat_scroll.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        self.chat_scroll.grid_columnconfigure(0, weight=1)

        # Karşılama mesajı
        self._show_welcome()

        # Input bar
        input_frame = ctk.CTkFrame(chat_main, height=60, corner_radius=12,
                                    fg_color=BG_SECONDARY, border_width=1,
                                    border_color=BORDER_SUBTLE)
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_entry = ctk.CTkEntry(
            input_frame, placeholder_text="Mesajınızı yazın...",
            height=44, corner_radius=10, fg_color=BG_INPUT,
            border_color=BORDER_COLOR, text_color=TEXT_PRIMARY,
            font=ctk.CTkFont(size=13)
        )
        self.chat_entry.grid(row=0, column=0, sticky="ew", padx=12, pady=8)
        self.chat_entry.bind("<Return>", lambda e: self.send_message())
        
        self.send_btn = ctk.CTkButton(
            input_frame, text="Gönder ➤", width=110, height=44,
            command=self.send_message, corner_radius=10,
            fg_color=ACCENT_PRIMARY, hover_color=BTN_PRIMARY_HOVER,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.send_btn.grid(row=0, column=1, padx=(0, 12), pady=8)

    def _show_welcome(self):
        welcome = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        welcome.pack(fill="x", pady=40)
        ctk.CTkLabel(welcome, text="🤖", font=ctk.CTkFont(size=48)).pack()
        ctk.CTkLabel(welcome, text="AI Stüdyosuna Hoş Geldiniz",
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(pady=(8, 4))
        ctk.CTkLabel(welcome, text="Yukarıdan bir model seçin ve sohbete başlayın",
                     font=ctk.CTkFont(size=13),
                     text_color=TEXT_MUTED).pack()

    # ═══════════════════════════════════════════════════════════
    #  SOHBET FONKSİYONLARI
    # ═══════════════════════════════════════════════════════════

    def new_chat(self):
        """Yeni bir sohbet oturumu başlat."""
        for w in self.chat_scroll.winfo_children():
            w.destroy()
        self._show_welcome()
        # Yeni benzersiz oturum başlat
        self.chat_engine.new_session(
            model_name=self.chat_engine.model_name or "genel"
        )

    def toggle_history_sidebar(self):
        if self.history_visible:
            self.history_sidebar.grid_forget()
            self.history_visible = False
        else:
            self.history_sidebar.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=10)
            self.refresh_history_list()
            self.history_visible = True

    def on_model_select(self, choice):
        if choice in ["Model Yok", "Model Seçiniz"]:
            return
        
        api_key = self.api_key_entry.get()
        provider_name = self.provider_var.get()
        provider_map = {"Ollama (Local)": "ollama", "OpenAI": "openai",
                        "Google AI": "google", "Anthropic": "anthropic"}
        provider = provider_map.get(provider_name, "ollama")
        preferred_rag = self.rag_base_model_var.get()
        
        # Yeni model seçildiğinde yeni oturum başlat (geçmiş yüklenmiyorsa)
        if not self._pending_history_filepath:
            self.chat_engine.new_session(model_name=choice)
        
        # Loading overlay göster
        self._show_loading("Model yükleniyor...", choice)
        
        def on_status(msg):
            if self._loading_overlay:
                self.after(0, lambda: self._loading_overlay.update_status(msg))
        
        def on_done(success, msg):
            self.after(0, lambda: self._hide_loading())
            if success:
                # Bekleyen geçmiş sohbet varsa onu göster, yoksa "model yüklendi" göster
                if self._pending_history_filepath is not None:
                    filepath = self._pending_history_filepath
                    self._pending_history_filepath = None
                    self.after(0, lambda: self._load_and_show_history(filepath, choice))
                else:
                    self.after(0, lambda: self._clear_and_show_ready(choice))
            else:
                self._pending_history_filepath = None
                self.after(0, lambda: messagebox.showwarning("Uyarı", msg))
        
        self.chat_engine.load_model_async(
            choice, api_key=api_key, provider=provider,
            status_callback=on_status, done_callback=on_done,
            preferred_rag_model=preferred_rag
        )

    def _show_loading(self, message, model_name=""):
        self._hide_loading()
        self._loading_overlay = LoadingOverlay(self.page_chat, message=message)
        self._loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._loading_overlay.cancel_btn.configure(command=self._cancel_loading)
        self._loading_overlay.lift()
    
    def _cancel_loading(self):
        self.chat_engine.cancel_loading()
        self._hide_loading()
    
    def _hide_loading(self):
        if self._loading_overlay:
            self._loading_overlay.stop()
            self._loading_overlay.destroy()
            self._loading_overlay = None

    def _clear_and_show_ready(self, model_name):
        for w in self.chat_scroll.winfo_children():
            w.destroy()
        bubble = ChatBubble(self.chat_scroll, 
                           f"✓ '{model_name}' modeli yüklendi. Sohbete başlayabilirsiniz!",
                           role="ai",
                           timestamp=datetime.datetime.now().strftime("%H:%M"))
        bubble.pack(fill="x")

    def _load_and_show_history(self, filepath, model_name):
        """Dosyadan geçmiş sohbet yükle ve göster (model yüklendikten sonra)"""
        success = self.chat_engine.load_session(filepath)
        if not success:
            messagebox.showwarning("Uyarı", "Sohbet geçmişi yüklenemedi!")
            return
        
        messages = self.chat_engine.memory.chat_memory
        
        for w in self.chat_scroll.winfo_children():
            w.destroy()
        
        # Başlık
        msg_count = len(messages)
        bubble = ChatBubble(self.chat_scroll,
                           f"📜 '{model_name}' sohbet geçmişi yüklendi ({msg_count} mesaj).",
                           role="ai",
                           timestamp=datetime.datetime.now().strftime("%H:%M"))
        bubble.pack(fill="x")
        
        # Geçmiş mesajlar
        for msg in messages:
            role = "user" if msg.get('role') == 'human' else "ai"
            content = msg.get('content', '')
            time_str = msg.get('time', '')
            b = ChatBubble(self.chat_scroll, content, role=role, timestamp=time_str)
            b.pack(fill="x")
        
        self.chat_scroll._parent_canvas.yview_moveto(1.0)

    def send_message(self):
        if self._is_generating:
            return

        msg = self.chat_entry.get().strip()
        if not msg:
            return
        
        timestamp = datetime.datetime.now().strftime("%H:%M")
        
        # Kullanıcı mesajı
        user_bubble = ChatBubble(self.chat_scroll, msg, role="user", timestamp=timestamp)
        user_bubble.pack(fill="x")
        self.chat_entry.delete(0, "end")
        
        # Typing indicator (ilk token gelene kadar)
        self._typing_indicator = TypingIndicator(self.chat_scroll)
        self._typing_indicator.pack(fill="x")
        self.chat_scroll._parent_canvas.yview_moveto(1.0)
        
        # AI mesaj balonu
        ai_bubble = ChatBubble(self.chat_scroll, "", role="ai", timestamp=timestamp)
        
        # Gönder butonunu "⏹ Durdur" butonuna çevir
        self._is_generating = True
        self.send_btn.configure(
            state="normal", text="⏹ Durdur", fg_color=BTN_DANGER,
            hover_color=BTN_DANGER_HOVER, command=self._stop_generating
        )
        self.chat_entry.configure(state="disabled")

        first_token_received = [False]

        def on_token(token):
            if not first_token_received[0]:
                first_token_received[0] = True
                if self._typing_indicator:
                    self._typing_indicator.stop()
                    self._typing_indicator.destroy()
                    self._typing_indicator = None
                ai_bubble.pack(fill="x")
            
            ai_bubble.append_chunk(token)
            self.chat_scroll._parent_canvas.yview_moveto(1.0)

        def on_done():
            if self._typing_indicator:
                self._typing_indicator.stop()
                self._typing_indicator.destroy()
                self._typing_indicator = None
            if not first_token_received[0]:
                ai_bubble.pack(fill="x")
            
            ai_bubble.finalize()
            self._is_generating = False
            self.send_btn.configure(
                state="normal", text="Gönder ➤", fg_color=ACCENT_PRIMARY,
                hover_color=BTN_PRIMARY_HOVER, command=self.send_message
            )
            self.chat_entry.configure(state="normal")
            self.chat_entry.focus()
            self.chat_scroll._parent_canvas.yview_moveto(1.0)

        def worker():
            try:
                self.chat_engine.chat_stream(
                    msg,
                    chunk_callback=lambda tok, done=False: self.after(0, on_done if done else lambda: on_token(tok))
                )
            except Exception as e:
                logger.error(f"Streaming sohbet hatası: {e}")
                self.after(0, lambda: on_token(f"\n❌ Hata oluştu: {e}"))
                self.after(0, on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _stop_generating(self):
        """Devam eden yapay zeka yanıtını durdurur."""
        if self._is_generating:
            self.chat_engine.stop_stream()
            self.send_btn.configure(state="disabled", text="Durduruluyor...")

    # ═══════════════════════════════════════════════════════════
    #  MODEL LİSTELEME & GEÇMİŞ
    # ═══════════════════════════════════════════════════════════

    def refresh_model_list(self):
        rag_models = self.model_manager.list_local_models()
        ollama_models = self.model_manager.list_ollama_models()
        all_models = sorted(list(set(rag_models + ollama_models)))
        
        if not all_models:
            self.model_dropdown.configure(values=["Model Yok"])
            self.model_selector_var.set("Model Yok")
        else:
            self.model_dropdown.configure(values=all_models)
            if self.model_selector_var.get() in ["Model Seçiniz", "Model Yok"]:
                self.model_selector_var.set(all_models[0])
        
        if hasattr(self, "rag_manage_dropdown"):
            self._refresh_rag_manage_dropdown()

    def refresh_history_list(self):
        """Tüm sohbet oturumlarını listele."""
        for w in self.history_list_frame.winfo_children():
            w.destroy()
        
        sessions = SimpleMemory.list_all_sessions()
        
        if not sessions:
            ctk.CTkLabel(self.history_list_frame, text="Henüz sohbet yok",
                         text_color=TEXT_MUTED).pack(pady=20)
            return
        
        for session in sessions:
            model_name = session["model_name"]
            preview = session["preview"]
            created = session.get("created_at", "")
            msg_count = session.get("message_count", 0)
            filepath = session["filepath"]
            
            # Tarih kısmını kısalt
            date_short = ""
            if created:
                try:
                    dt = datetime.datetime.strptime(created, "%Y-%m-%d %H:%M:%S")
                    date_short = dt.strftime("%d/%m %H:%M")
                except:
                    date_short = created[:16]
            
            display_text = f"💬 {model_name}\n📅 {date_short}  •  {msg_count} mesaj\n{preview}"
            
            row = ctk.CTkFrame(self.history_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            ctk.CTkButton(
                row, text=display_text,
                command=lambda fp=filepath, mn=model_name: self.load_history_conversation(fp, mn),
                anchor="w", height=65, corner_radius=8,
                fg_color=BG_CARD, hover_color=BG_HOVER,
                text_color=TEXT_PRIMARY, font=ctk.CTkFont(size=10)
            ).pack(side="left", fill="x", expand=True, padx=(0, 2))
            
            ctk.CTkButton(
                row, text="✖", width=32, height=65,
                command=lambda fp=filepath: self.delete_history(fp),
                fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER,
                corner_radius=8
            ).pack(side="right")

    def delete_history(self, filepath):
        """Sohbet dosyasını sil."""
        if messagebox.askyesno("Onay", "Bu sohbeti silmek istediğinize emin misiniz?"):
            try:
                os.remove(filepath)
                self.refresh_history_list()
            except Exception as e:
                messagebox.showerror("Hata", f"Silinemedi: {e}")

    def load_history_conversation(self, filepath, model_name):
        """Geçmiş sohbet oturumunu yükle."""
        if not os.path.exists(filepath):
            messagebox.showwarning("Uyarı", "Sohbet dosyası bulunamadı!")
            return
        
        # Filepath'i beklet — model yüklendikten sonra gösterilecek
        self._pending_history_filepath = filepath
        
        # Mevcut model zaten yüklü mü kontrol et
        if self.chat_engine.model_name == model_name and self.chat_engine.llm:
            # Model zaten yüklü, direkt göster
            self._pending_history_filepath = None
            self._load_and_show_history(filepath, model_name)
        else:
            # Model yüklenmeli
            self.model_selector_var.set(model_name)
            self.on_model_select(model_name)

    # ═══════════════════════════════════════════════════════════
    #  MODELLER SAYFASI
    # ═══════════════════════════════════════════════════════════

    def _create_models_page(self):
        self.page_models = ctk.CTkFrame(self, corner_radius=0, fg_color=BG_PRIMARY)
        self.page_models.grid_rowconfigure(1, weight=1)
        self.page_models.grid_columnconfigure(0, weight=1)
        
        # Başlık
        title_frame = ctk.CTkFrame(self.page_models, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 8))
        ctk.CTkLabel(title_frame, text="🎓 Yeni AI Modeli Oluştur",
                     font=ctk.CTkFont(size=FONT_TITLE, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Verilerinizle özelleştirilmiş yapay zeka modeli eğitin",
                     font=ctk.CTkFont(size=FONT_BODY), text_color=TEXT_MUTED).pack(anchor="w", pady=(2, 0))

        # Ana scroll
        content = ctk.CTkScrollableFrame(self.page_models, corner_radius=0, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=25, pady=(0, 20))
        content.grid_columnconfigure(0, weight=1)
        
        # Strateji seçimi
        strat_card = ctk.CTkFrame(content, corner_radius=12, fg_color=BG_SECONDARY,
                                   border_width=1, border_color=BORDER_SUBTLE)
        strat_card.pack(fill="x", pady=(0, 12))
        
        ctk.CTkLabel(strat_card, text="1️⃣ Eğitim Yöntemi Seçin:",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(15, 10))

        self.strategy_var = ctk.StringVar(value="RAG")
        self.strategy_var.trace_add("write", self._on_strategy_change)
        
        strategies_grid = ctk.CTkFrame(strat_card, fg_color="transparent")
        strategies_grid.pack(fill="x", padx=20, pady=(0, 15))
        
        strategies = [
            ("RAG", "📚 Bilgi Bankası", "Hızlı • Büyük dosyalar • GPU gerektirmez"),
            ("Ollama", "🚀 Taşınabilir Model", "Orta boyut • Başka PC'de çalışır"),
            ("FineTune", "🔬 Gerçek Eğitim", "Uzman • GPU gerekir • Ağırlık değiştirir"),
            ("Brain", "🧠 Beyin Model", "Talimat tabanlı • Dosyasız • Özel kişilik"),
            ("Scratch", "🧪 Sıfırdan Eğitim", "Deneysel • Çok veri gerekir • Yavaş")
        ]
        
        # 3 sütun layout
        strategies_grid.grid_columnconfigure(0, weight=1)
        strategies_grid.grid_columnconfigure(1, weight=1)
        strategies_grid.grid_columnconfigure(2, weight=1)
        
        for i, (val, title, desc) in enumerate(strategies):
            card = ctk.CTkFrame(strategies_grid, corner_radius=10, fg_color=BG_CARD,
                                border_width=1, border_color=BORDER_SUBTLE)
            row_idx = i // 3
            col_idx = i % 3
            card.grid(row=row_idx, column=col_idx, padx=6, pady=4, sticky="nsew")
            
            ctk.CTkRadioButton(card, text="", variable=self.strategy_var,
                               value=val, width=20, radiobutton_width=18,
                               radiobutton_height=18, fg_color=ACCENT_PRIMARY,
                               border_color=TEXT_MUTED).pack(side="left", padx=12, pady=15)
            
            tf = ctk.CTkFrame(card, fg_color="transparent")
            tf.pack(side="left", fill="both", expand=True, pady=15, padx=(0, 12))
            ctk.CTkLabel(tf, text=title, font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=TEXT_PRIMARY, anchor="w").pack(fill="x")
            ctk.CTkLabel(tf, text=desc, font=ctk.CTkFont(size=FONT_SMALL),
                         text_color=TEXT_MUTED, anchor="w").pack(fill="x")

        # Dinamik form container
        self.dynamic_form = ctk.CTkFrame(content, corner_radius=12, fg_color=BG_SECONDARY,
                                          border_width=1, border_color=BORDER_SUBTLE)
        self.dynamic_form.pack(fill="x", pady=(0, 12))
        
        # Eğitim log paneli
        self.training_panel = TrainingLogPanel(content)
        self.training_panel.pack(fill="x", pady=(0, 12))
        self.training_panel.pack_forget()  # başlangıçta gizli
        
        # RAG Doküman Yönetim Kartı
        self.rag_mgmt_card = ctk.CTkFrame(content, corner_radius=12, fg_color=BG_SECONDARY,
                                          border_width=1, border_color=BORDER_SUBTLE)
        self.rag_mgmt_card.pack(fill="x", pady=(0, 15))
        self._build_rag_manager_ui(self.rag_mgmt_card)
        
        self._render_model_form()

    def _build_rag_manager_ui(self, parent):
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkLabel(
            header, text="📚 Bilgi Bankası (RAG) Doküman Yöneticisi",
            font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXT_PRIMARY
        ).pack(side="left")

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkLabel(row, text="Model:", text_color=TEXT_SECONDARY).pack(side="left", padx=(0, 6))

        self.rag_manage_var = ctk.StringVar(value="Seçiniz")
        self.rag_manage_dropdown = ctk.CTkOptionMenu(
            row, variable=self.rag_manage_var, values=["Seçiniz"],
            width=200, height=36, corner_radius=8,
            fg_color=BG_INPUT, button_color=ACCENT_PRIMARY
        )
        self.rag_manage_dropdown.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            row, text="🔄", width=36, height=36, corner_radius=8,
            fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
            command=self._refresh_rag_manage_dropdown
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            row, text="Dokümanları Listele", height=36, corner_radius=8,
            fg_color=ACCENT_PRIMARY, hover_color=BTN_PRIMARY_HOVER,
            command=self._show_rag_docs
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            row, text="🗑️ Modeli Tamamen Sil", height=36, corner_radius=8,
            fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER,
            command=self._delete_entire_rag_model
        ).pack(side="right")

        self.rag_docs_frame = ctk.CTkScrollableFrame(parent, height=130, fg_color=BG_PRIMARY, corner_radius=8)
        self.rag_docs_frame.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(self.rag_docs_frame, text="Bir model seçip 'Dokümanları Listele' butonuna tıklayın.", text_color=TEXT_MUTED).pack(pady=20)

        self._refresh_rag_manage_dropdown()

    def _refresh_rag_manage_dropdown(self):
        models = self.model_manager.list_local_models()
        if models:
            self.rag_manage_dropdown.configure(values=models)
            if self.rag_manage_var.get() not in models:
                self.rag_manage_var.set(models[0])
        else:
            self.rag_manage_dropdown.configure(values=["Model Yok"])
            self.rag_manage_var.set("Model Yok")

    def _show_rag_docs(self):
        model_name = self.rag_manage_var.get()
        if not model_name or model_name in ["Model Yok", "Seçiniz"]:
            return

        for w in self.rag_docs_frame.winfo_children():
            w.destroy()

        docs = self.model_manager.list_rag_documents(model_name)
        if not docs:
            ctk.CTkLabel(self.rag_docs_frame, text=f"'{model_name}' içinde doküman bulunamadı veya model boş.", text_color=TEXT_MUTED).pack(pady=15)
            return

        for doc in docs:
            fname = doc["filename"]
            chunks = doc["chunk_count"]

            item_row = ctk.CTkFrame(self.rag_docs_frame, fg_color=BG_CARD, corner_radius=6)
            item_row.pack(fill="x", pady=2, padx=4)

            ctk.CTkLabel(
                item_row, text=f"📄 {fname}  ({chunks} parça)",
                font=ctk.CTkFont(size=12), text_color=TEXT_PRIMARY, anchor="w"
            ).pack(side="left", padx=10, pady=6)

            ctk.CTkButton(
                item_row, text="🗑️ Çıkar", width=70, height=26, corner_radius=6,
                fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER, font=ctk.CTkFont(size=11),
                command=lambda fn=fname: self._delete_rag_doc_item(model_name, fn)
            ).pack(side="right", padx=8, pady=6)

    def _delete_rag_doc_item(self, model_name, filename):
        if messagebox.askyesno("Onay", f"'{filename}' dosyasını '{model_name}' bilgi bankasından çıkarmak istediğinize emin misiniz?"):
            success, msg = self.model_manager.delete_rag_document(model_name, filename)
            if success:
                messagebox.showinfo("Başarılı", msg)
                self._show_rag_docs()
            else:
                messagebox.showerror("Hata", msg)

    def _delete_entire_rag_model(self):
        model_name = self.rag_manage_var.get()
        if not model_name or model_name in ["Model Yok", "Seçiniz"]:
            return
        if messagebox.askyesno("Onay", f"'{model_name}' bilgi bankasını tamamen silmek istediğinize emin misiniz?\nBu işlem geri alınamaz!"):
            if self.model_manager.delete_model(model_name):
                messagebox.showinfo("Başarılı", f"'{model_name}' başarıyla silindi.")
                self.refresh_model_list()
                self._refresh_rag_manage_dropdown()
                for w in self.rag_docs_frame.winfo_children():
                    w.destroy()
                ctk.CTkLabel(self.rag_docs_frame, text="Model silindi.", text_color=TEXT_MUTED).pack(pady=20)
            else:
                messagebox.showerror("Hata", "Model silinemedi.")

    def _on_strategy_change(self, *args):
        self._render_model_form()

    def _render_model_form(self):
        for w in self.dynamic_form.winfo_children():
            w.destroy()
        
        strategy = self.strategy_var.get()
        
        # Model ismi
        ctk.CTkLabel(self.dynamic_form, text="2️⃣ Model Bilgileri",
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(15, 10))
        
        name_row = ctk.CTkFrame(self.dynamic_form, fg_color="transparent")
        name_row.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(name_row, text="Model İsmi:", width=130, anchor="w",
                     text_color=TEXT_SECONDARY).pack(side="left")
        self.model_name_entry = ctk.CTkEntry(name_row, placeholder_text="örn: kitap_asistani",
                                              height=38, corner_radius=8, fg_color=BG_INPUT,
                                              border_color=BORDER_COLOR)
        self.model_name_entry.pack(side="left", fill="x", expand=True, padx=(8, 0))
        
        # Baz model
        if strategy in ["Ollama", "FineTune", "Brain"]:
            base_row = ctk.CTkFrame(self.dynamic_form, fg_color="transparent")
            base_row.pack(fill="x", padx=20, pady=8)
            ctk.CTkLabel(base_row, text="Baz Model:", width=130, anchor="w",
                         text_color=TEXT_SECONDARY).pack(side="left")
            self.base_model_var = ctk.StringVar(value="Yükleniyor...")
            self.base_model_dropdown = ctk.CTkOptionMenu(
                base_row, variable=self.base_model_var, values=["Yükleniyor..."],
                height=38, corner_radius=8, width=220,
                fg_color=BG_INPUT, button_color=ACCENT_PRIMARY,
                dropdown_fg_color=BG_CARD
            )
            self.base_model_dropdown.pack(side="left", padx=(8, 4))
            ctk.CTkButton(base_row, text="🔄", width=38, height=38,
                          command=self._refresh_base_models, corner_radius=8,
                          fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER
                          ).pack(side="left")
            self._refresh_base_models()
        
        # RAG ayarları
        if strategy == "RAG":
            chunk_header = ctk.CTkFrame(self.dynamic_form, fg_color="transparent")
            chunk_header.pack(fill="x", padx=20, pady=(15, 5))
            ctk.CTkLabel(chunk_header, text="⚙️ Chunk Ayarları",
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=TEXT_PRIMARY).pack(side="left")
            
            chunk_row = ctk.CTkFrame(self.dynamic_form, fg_color="transparent")
            chunk_row.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(chunk_row, text="Chunk Size:", width=130, anchor="w",
                         text_color=TEXT_SECONDARY).pack(side="left")
            self.chunk_size_var = ctk.IntVar(value=1000)
            ctk.CTkSlider(chunk_row, from_=200, to=4000, variable=self.chunk_size_var,
                          width=200, progress_color=ACCENT_PRIMARY,
                          button_color=ACCENT_PRIMARY).pack(side="left", padx=8)
            self.chunk_size_label = ctk.CTkLabel(chunk_row, text="1000",
                                                  text_color=TEXT_PRIMARY, width=50)
            self.chunk_size_label.pack(side="left")
            InfoTooltip(chunk_row,
                "Chunk Size: Dokümanın kaç karakterlik parçalara bölüneceği.\n\n"
                "• Düşük (200-500): Daha hassas arama, küçük bilgi parçaları.\n"
                "  Kısa cevaplar için iyi, ama bağlam kaybı olabilir.\n\n"
                "• Yüksek (1500-4000): Büyük bilgi blokları, daha fazla bağlam.\n"
                "  Uzun cevaplar için iyi, ama arama hassasiyeti düşer.\n\n"
                "• Önerilen: 800-1200"
            ).pack(side="left", padx=4)
            self.chunk_size_var.trace_add("write", lambda *a: self.chunk_size_label.configure(
                text=str(self.chunk_size_var.get())))
            
            overlap_row = ctk.CTkFrame(self.dynamic_form, fg_color="transparent")
            overlap_row.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(overlap_row, text="Overlap:", width=130, anchor="w",
                         text_color=TEXT_SECONDARY).pack(side="left")
            self.chunk_overlap_var = ctk.IntVar(value=200)
            ctk.CTkSlider(overlap_row, from_=0, to=1000, variable=self.chunk_overlap_var,
                          width=200, progress_color=ACCENT_PRIMARY,
                          button_color=ACCENT_PRIMARY).pack(side="left", padx=8)
            self.overlap_label = ctk.CTkLabel(overlap_row, text="200",
                                               text_color=TEXT_PRIMARY, width=50)
            self.overlap_label.pack(side="left")
            InfoTooltip(overlap_row,
                "Overlap: Parçalar arası örtüşme miktarı (karakter).\n\n"
                "• 0: Parçalar tamamen bağımsız. Bilgi kaybı riski var.\n\n"
                "• 100-300: Parçalar arası geçiş yumuşak. Bilgi kaybı az.\n"
                "  Cümlelerin ortasında kesilmesini engeller.\n\n"
                "• 500+: Çok fazla tekrar, veritabanı büyür.\n\n"
                "• Önerilen: Chunk Size'ın %10-20'si"
            ).pack(side="left", padx=4)
            self.chunk_overlap_var.trace_add("write", lambda *a: self.overlap_label.configure(
                text=str(self.chunk_overlap_var.get())))
        
        # Fine-Tune parametreleri
        if strategy == "FineTune":
            ctk.CTkLabel(self.dynamic_form, text="⚙️ Eğitim Parametreleri",
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(15, 5))
            
            ft_tooltips = {
                "ft_lr": (
                    "Learning Rate: Modelin her adımda ne kadar öğreneceği.\n\n"
                    "• Çok düşük (0.00001): Yavaş öğrenir, eğitim uzun sürer.\n"
                    "  Ama daha stabil, overfitting riski az.\n\n"
                    "• Çok yüksek (0.01): Hızlı öğrenir ama kararsız.\n"
                    "  Model 'unutabilir' veya kötü sonuç verebilir.\n\n"
                    "• Önerilen: 0.0001 - 0.0003"
                ),
                "ft_steps": (
                    "Max Steps: Toplam eğitim adım sayısı.\n\n"
                    "• Az (10-20): Hızlı ama az öğrenir. Test için iyi.\n\n"
                    "• Orta (50-100): İyi denge. Çoğu kullanım için yeterli.\n\n"
                    "• Çok (200-500): Derin öğrenme ama overfitting riski.\n"
                    "  Eğitim süresi artar (GPU'ya bağlı).\n\n"
                    "• Önerilen: Veri az ise 30-50, çok ise 100-200"
                ),
                "ft_batch": (
                    "Batch Size: Her adımda kaç örnek işleneceği.\n\n"
                    "• 1: Az GPU belleği kullanır ama yavaş ve gürültülü.\n\n"
                    "• 2-4: İyi denge. Çoğu GPU için uygun.\n\n"
                    "• 8+: Daha stabil ama çok GPU belleği gerekir.\n"
                    "  Yetersiz bellek hatası alabilirsiniz.\n\n"
                    "• Önerilen: GPU 8GB → 1-2, GPU 16GB+ → 2-4"
                ),
            }
            
            for label, var_name, default, min_v, max_v in [
                ("Learning Rate:", "ft_lr", 0.0002, 0.00001, 0.01),
                ("Max Steps:", "ft_steps", 50, 5, 500),
                ("Batch Size:", "ft_batch", 2, 1, 8),
            ]:
                row = ctk.CTkFrame(self.dynamic_form, fg_color="transparent")
                row.pack(fill="x", padx=20, pady=3)
                ctk.CTkLabel(row, text=label, width=130, anchor="w",
                             text_color=TEXT_SECONDARY).pack(side="left")
                entry = ctk.CTkEntry(row, width=100, height=34, corner_radius=8,
                                     fg_color=BG_INPUT, border_color=BORDER_COLOR)
                entry.insert(0, str(default))
                entry.pack(side="left", padx=8)
                setattr(self, f"{var_name}_entry", entry)
                InfoTooltip(row, ft_tooltips[var_name]).pack(side="left", padx=4)
        
        # Sıfırdan Eğitim parametreleri
        if strategy == "Scratch":
            # Uyarı
            warn_frame = ctk.CTkFrame(self.dynamic_form, fg_color="#3b1f1f",
                                      corner_radius=8, border_width=1,
                                      border_color=ACCENT_WARNING)
            warn_frame.pack(fill="x", padx=20, pady=(15, 5))
            ctk.CTkLabel(warn_frame,
                text="⚠️ DENEYSEL: Sıfırdan eğitim çok veri ve zaman gerektirir.\n"
                     "Sonuç modeli sadece verdiğiniz metinlerdeki kalıpları öğrenir.",
                font=ctk.CTkFont(size=FONT_SMALL),
                text_color=ACCENT_WARNING, wraplength=500, justify="left"
            ).pack(padx=12, pady=8)
            
            ctk.CTkLabel(self.dynamic_form, text="🏗️ Model Mimarisi",
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(15, 5))
            
            scratch_tooltips = {
                "sc_layers": (
                    "Katman Sayısı: Modelin derinliği.\n\n"
                    "• 2-4: Küçük model, hızlı eğitim, sınırlı kapasite.\n\n"
                    "• 6-8: Orta model, daha fazla öğrenme kapasitesi.\n"
                    "  Daha çok veri ve zaman gerekir.\n\n"
                    "• 12+: Büyük model, çok GPU/veri gerekir.\n\n"
                    "• Önerilen: Başlangıç için 4"
                ),
                "sc_hidden": (
                    "Gizli Boyut: Her katmandaki nöron sayısı.\n\n"
                    "• 128: Çok küçük, hızlı ama sınırlı.\n\n"
                    "• 256: Küçük ama makul. Başlangıç için iyi.\n\n"
                    "• 512+: Daha güçlü ama çok daha fazla parametre.\n\n"
                    "• NOT: Boyut, head sayısına bölünebilmeli!\n"
                    "• Önerilen: 256"
                ),
                "sc_vocab": (
                    "Vocab Boyutu: Token sözlük büyüklüğü.\n\n"
                    "• 2000: Küçük, kendi verinizdeki kelimeler.\n\n"
                    "• 5000: Orta, iyi denge.\n\n"
                    "• 10000+: Büyük, daha fazla kelime tanır.\n"
                    "  Ama daha çok veri gerektirir.\n\n"
                    "• Önerilen: Veri az ise 3000, çok ise 8000"
                ),
                "sc_steps": (
                    "Eğitim Adımı: Sıfırdan eğitimde daha çok step gerekir.\n\n"
                    "• 100-200: Hızlı test.\n\n"
                    "• 500-1000: Makul eğitim.\n\n"
                    "• 2000+: Derin eğitim (uzun sürer).\n\n"
                    "• Önerilen: Başlangıç için 200-500"
                ),
                "sc_lr": (
                    "Learning Rate: Sıfırdan eğitimde daha yüksek LR kullanılır.\n\n"
                    "• 0.0001: Yavaş ama stabil.\n\n"
                    "• 0.0005: İyi denge.\n\n"
                    "• 0.001+: Hızlı ama kararsız olabilir.\n\n"
                    "• Önerilen: 0.0005"
                ),
            }
            
            for label, var_name, default in [
                ("Katman Sayısı:", "sc_layers", 4),
                ("Gizli Boyut:", "sc_hidden", 256),
                ("Vocab Boyutu:", "sc_vocab", 5000),
                ("Max Steps:", "sc_steps", 200),
                ("Learning Rate:", "sc_lr", 0.0005),
            ]:
                row = ctk.CTkFrame(self.dynamic_form, fg_color="transparent")
                row.pack(fill="x", padx=20, pady=3)
                ctk.CTkLabel(row, text=label, width=130, anchor="w",
                             text_color=TEXT_SECONDARY).pack(side="left")
                entry = ctk.CTkEntry(row, width=100, height=34, corner_radius=8,
                                     fg_color=BG_INPUT, border_color=BORDER_COLOR)
                entry.insert(0, str(default))
                entry.pack(side="left", padx=8)
                setattr(self, f"{var_name}_entry", entry)
                InfoTooltip(row, scratch_tooltips[var_name]).pack(side="left", padx=4)
        
        # Ollama / Brain system prompt
        if strategy in ["Ollama", "Brain"]:
            prompt_title = "📝 System Prompt" if strategy == "Ollama" else "🧠 Beyin Talimatları"
            ctk.CTkLabel(self.dynamic_form, text=prompt_title,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(15, 5))
            
            if strategy == "Brain":
                ctk.CTkLabel(self.dynamic_form,
                    text="AI'nın kişiliğini, uzmanlık alanını ve davranış kurallarını tanımlayın.",
                    font=ctk.CTkFont(size=FONT_SMALL), text_color=TEXT_MUTED
                ).pack(anchor="w", padx=20, pady=(0, 5))
            
            self.system_prompt_text = ctk.CTkTextbox(
                self.dynamic_form, height=150 if strategy == "Brain" else 100,
                corner_radius=8, fg_color=BG_INPUT, text_color=TEXT_PRIMARY,
                font=ctk.CTkFont(size=12), border_width=1,
                border_color=BORDER_COLOR
            )
            self.system_prompt_text.pack(fill="x", padx=20, pady=4)
            
            if strategy == "Brain":
                self.system_prompt_text.insert("1.0",
                    "Sen [uzmanlık alanı] konusunda uzman bir asistansın.\n\n"
                    "Görevlerin:\n"
                    "- [görev 1]\n"
                    "- [görev 2]\n\n"
                    "Kuralların:\n"
                    "- Her zaman Türkçe cevap ver\n"
                    "- Kısa ve net ol\n"
                    "- Emin olmadığın konularda belirt")
            else:
                self.system_prompt_text.insert("1.0", 
                    "Varsayılan prompt kullanılacak. Özelleştirmek için buraya yazın.\n"
                    "{CONTENT} etiketi dosya içeriğiyle değiştirilir.")
        
        # Dosya seçimi (Brain için opsiyonel)
        file_title = "3️⃣ Ek Dosyalar (opsiyonel)" if strategy == "Brain" else "3️⃣ Eğitim Dosyaları"
        ctk.CTkLabel(self.dynamic_form, text=file_title,
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(20, 8))
        
        if strategy == "Brain":
            ctk.CTkLabel(self.dynamic_form,
                text="İsterseniz bilgi dosyaları ekleyerek AI'nın bilgi tabanını zenginleştirebilirsiniz.",
                font=ctk.CTkFont(size=FONT_SMALL), text_color=TEXT_MUTED
            ).pack(anchor="w", padx=20, pady=(0, 4))
        
        ctk.CTkButton(self.dynamic_form, text="📁 Dosya Seç (PDF, TXT, Excel, Word...)",
                      command=self._select_files, height=42, corner_radius=8,
                      fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER,
                      font=ctk.CTkFont(size=13)).pack(fill="x", padx=20, pady=4)
        
        self.file_label = ctk.CTkLabel(self.dynamic_form, text="Henüz dosya seçilmedi" if strategy != "Brain" else "Dosya opsiyonel — sadece talimatlarla da oluşturulabilir",
                                        text_color=TEXT_MUTED, font=ctk.CTkFont(size=12))
        self.file_label.pack(padx=20, pady=4)
        
        # Oluştur butonu
        btn_row = ctk.CTkFrame(self.dynamic_form, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(20, 15))
        
        self.create_btn = ctk.CTkButton(
            btn_row, text="🚀 MODELİ OLUŞTUR",
            command=self._create_model,
            fg_color=ACCENT_SUCCESS, hover_color=BTN_SUCCESS_HOVER,
            height=50, corner_radius=10,
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.create_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        
        self.cancel_train_btn = ctk.CTkButton(
            btn_row, text="⏹ İptal", width=80,
            command=self._cancel_training,
            fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER,
            height=50, corner_radius=10
        )
        # İptal butonu başlangıçta gizli
        
        # Progress
        self.progress = ctk.CTkProgressBar(self.dynamic_form, corner_radius=6,
                                            progress_color=ACCENT_PRIMARY,
                                            fg_color=BG_PRIMARY, height=6)
        self.progress.pack(fill="x", padx=20, pady=(0, 15))
        self.progress.set(0)

    def _refresh_base_models(self):
        models = self.model_manager.list_ollama_models()
        if models:
            self.base_model_dropdown.configure(values=models)
            self.base_model_var.set(models[0])
        else:
            self.base_model_dropdown.configure(values=["Model Yok"])
            self.base_model_var.set("Model Yok")

    def _select_files(self):
        files = filedialog.askopenfilenames(
            title="Eğitim Dosyalarını Seçin",
            filetypes=[("Desteklenen Dosyalar", "*.txt;*.pdf;*.docx;*.doc;*.xlsx;*.xls;*.csv;*.json;*.jsonl"),
                       ("Tüm Dosyalar", "*.*")]
        )
        if files:
            self.files_to_train = list(files)
            self.file_label.configure(text=f"✓ {len(files)} dosya seçildi",
                                       text_color=ACCENT_SUCCESS)
        else:
            self.files_to_train = []
            self.file_label.configure(text="Henüz dosya seçilmedi",
                                       text_color=TEXT_MUTED)

    def _cancel_training(self):
        self.model_manager.cancel_training()
        self.cancel_train_btn.pack_forget()

    def _create_model(self):
        name = self.model_name_entry.get().strip()
        strategy = self.strategy_var.get()
        
        if not name:
            messagebox.showerror("Hata", "Lütfen bir model ismi girin!")
            return
        
        # Brain için dosya zorunlu değil, diğerleri için zorunlu
        if strategy != "Brain" and not self.files_to_train:
            messagebox.showerror("Hata", "Lütfen en az bir dosya seçin!")
            return
        
        base_model = None
        if strategy in ["Ollama", "FineTune", "Brain"]:
            base_model = self.base_model_var.get()
            if not base_model or base_model == "Model Yok":
                messagebox.showerror("Hata", "Lütfen baz model seçin!")
                return
        
        # Brain için system prompt zorunlu
        if strategy == "Brain":
            sp_text = self.system_prompt_text.get("1.0", "end").strip()
            if not sp_text or len(sp_text) < 10:
                messagebox.showerror("Hata", "Lütfen beyin talimatlarını yazın! (en az 10 karakter)")
                return
        
        # UI'ı hazırla
        self.create_btn.configure(state="disabled", text="⏳ Oluşturuluyor...")
        self.cancel_train_btn.pack(side="left", padx=(6, 0))
        self.training_panel.pack(fill="x", pady=(0, 12))
        self.training_panel.set_status("▶ Çalışıyor", ACCENT_SUCCESS)
        self.progress.set(0)
        
        def progress_cb(msg, pct):
            self.after(0, lambda: self.training_panel.add_log(msg))
            if pct is not None:
                self.after(0, lambda: self.progress.set(pct))
                self.after(0, lambda: self.training_panel.set_progress(pct))
        
        def worker():
            try:
                if strategy == "RAG":
                    chunk_s = self.chunk_size_var.get()
                    chunk_o = self.chunk_overlap_var.get()
                    msg = self.model_manager.create_rag_model(
                        name, self.files_to_train,
                        chunk_size=chunk_s, chunk_overlap=chunk_o,
                        progress_callback=progress_cb
                    )
                elif strategy == "Ollama":
                    sp_text = self.system_prompt_text.get("1.0", "end").strip()
                    sys_prompt = None if "Varsayılan prompt" in sp_text else sp_text
                    msg = self.model_manager.create_ollama_model(
                        name, base_model, self.files_to_train,
                        system_prompt=sys_prompt,
                        progress_callback=progress_cb
                    )
                elif strategy == "FineTune":
                    lr = float(self.ft_lr_entry.get())
                    steps = int(self.ft_steps_entry.get())
                    batch = int(self.ft_batch_entry.get())
                    msg = self.model_manager.create_finetune_model(
                        name, base_model, self.files_to_train,
                        learning_rate=lr, max_steps=steps, batch_size=batch,
                        progress_callback=progress_cb
                    )
                elif strategy == "Brain":
                    sp_text = self.system_prompt_text.get("1.0", "end").strip()
                    msg = self.model_manager.create_brain_model(
                        name, base_model, sp_text,
                        files=self.files_to_train if self.files_to_train else None,
                        progress_callback=progress_cb
                    )
                elif strategy == "Scratch":
                    layers = int(self.sc_layers_entry.get())
                    hidden = int(self.sc_hidden_entry.get())
                    vocab = int(self.sc_vocab_entry.get())
                    steps = int(self.sc_steps_entry.get())
                    lr = float(self.sc_lr_entry.get())
                    msg = self.model_manager.create_scratch_model(
                        name, self.files_to_train,
                        vocab_size=vocab, n_layers=layers,
                        n_heads=max(1, hidden // 64),
                        hidden_size=hidden, max_steps=steps,
                        learning_rate=lr,
                        progress_callback=progress_cb
                    )
                
                self.after(0, lambda: self._on_create_done(True, msg))
            except Exception as e:
                self.after(0, lambda: self._on_create_done(False, str(e)))
        
        threading.Thread(target=worker, daemon=True).start()

    def _on_create_done(self, success, msg):
        self.create_btn.configure(state="normal", text="🚀 MODELİ OLUŞTUR")
        self.cancel_train_btn.pack_forget()
        
        if success:
            self.progress.set(1.0)
            self.training_panel.set_status("✅ Tamamlandı", ACCENT_SUCCESS)
            self.training_panel.add_log(f"\n{msg}")
            messagebox.showinfo("Başarılı!", msg)
            self.refresh_model_list()
            self.files_to_train = []
            self.file_label.configure(text="Dosya seçilmedi", text_color=TEXT_MUTED)
            self.after(3000, lambda: self.progress.set(0))
        else:
            self.progress.set(0)
            self.training_panel.set_status("❌ Hata", ACCENT_DANGER)
            self.training_panel.add_log(f"\n❌ HATA: {msg}")
            messagebox.showerror("Hata", msg)

    # ═══════════════════════════════════════════════════════════
    #  AYARLAR SAYFASI
    # ═══════════════════════════════════════════════════════════

    def _create_settings_page(self):
        self.page_settings = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color=BG_PRIMARY)
        
        ctk.CTkLabel(self.page_settings, text="⚙️ Ayarlar",
                     font=ctk.CTkFont(size=FONT_TITLE, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=30, pady=(25, 8))

        # Provider
        s1 = ctk.CTkFrame(self.page_settings, corner_radius=12, fg_color=BG_SECONDARY,
                           border_width=1, border_color=BORDER_SUBTLE)
        s1.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(s1, text="🤖 Yapay Zeka Motoru",
                     font=ctk.CTkFont(size=FONT_HEADING, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(18, 12))
        
        self.provider_var = ctk.StringVar(value=self.config_manager.get("provider", "Ollama (Local)"))
        for val, label in [
            ("Ollama (Local)", "🏠 Yerel • Ücretsiz • Hızlı"),
            ("OpenAI", "☁️ GPT-4 • Cloud • Ücretli"),
            ("Google AI", "🔍 Gemini • Cloud • Ücretli"),
            ("Anthropic", "🧠 Claude • Cloud • Ücretli"),
        ]:
            ctk.CTkRadioButton(s1, text=label, variable=self.provider_var, value=val,
                               font=ctk.CTkFont(size=FONT_BODY),
                               fg_color=ACCENT_PRIMARY, border_color=TEXT_MUTED
                               ).pack(anchor="w", padx=40, pady=4)
        
        ctk.CTkLabel(s1, text="🔑 API Anahtarı (Cloud servisler için)",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(16, 4))
        self.api_key_entry = ctk.CTkEntry(s1, placeholder_text="API anahtarınız...",
                                           height=38, corner_radius=8,
                                           fg_color=BG_INPUT, border_color=BORDER_COLOR,
                                           show="•")
        saved_key = self.config_manager.get("api_key", "")
        if saved_key:
            self.api_key_entry.insert(0, saved_key)
        self.api_key_entry.pack(fill="x", padx=20, pady=4)
        ctk.CTkLabel(s1, text="💡 Ollama için API anahtarı gerekmez",
                     text_color=TEXT_MUTED, font=ctk.CTkFont(size=FONT_SMALL)
                     ).pack(anchor="w", padx=20, pady=(2, 18))

        # RAG Model
        s2 = ctk.CTkFrame(self.page_settings, corner_radius=12, fg_color=BG_SECONDARY,
                           border_width=1, border_color=BORDER_SUBTLE)
        s2.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(s2, text="📚 RAG için Model",
                     font=ctk.CTkFont(size=FONT_HEADING, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(18, 12))
        
        rag_row = ctk.CTkFrame(s2, fg_color="transparent")
        rag_row.pack(fill="x", padx=20, pady=8)
        self.rag_base_model_var = ctk.StringVar(value=self.config_manager.get("rag_base_model", "Otomatik (En iyi model)"))
        self.rag_model_dropdown = ctk.CTkOptionMenu(
            rag_row, variable=self.rag_base_model_var,
            values=["Otomatik (En iyi model)"],
            height=38, corner_radius=8, width=300,
            fg_color=BG_INPUT, button_color=ACCENT_PRIMARY,
            dropdown_fg_color=BG_CARD
        )
        self.rag_model_dropdown.pack(side="left", padx=(0, 8))
        ctk.CTkButton(rag_row, text="🔄 Yenile", width=90, height=38,
                      command=self._refresh_rag_models, corner_radius=8,
                      fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER
                      ).pack(side="left")
        ctk.CTkLabel(s2, text="ℹ️ Otomatik: deepseek-r1 > llama3 > phi3 > ilk model",
                     text_color=TEXT_MUTED, font=ctk.CTkFont(size=FONT_SMALL)
                     ).pack(anchor="w", padx=20, pady=(2, 18))

        # Kaydet Butonu
        save_card = ctk.CTkFrame(self.page_settings, fg_color="transparent")
        save_card.pack(fill="x", padx=30, pady=10)
        ctk.CTkButton(
            save_card, text="💾 Ayarları Kaydet", height=44, corner_radius=10,
            fg_color=ACCENT_SUCCESS, hover_color=BTN_SUCCESS_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._save_settings
        ).pack(fill="x")

        # Sohbet geçmişi
        s3 = ctk.CTkFrame(self.page_settings, corner_radius=12, fg_color=BG_SECONDARY,
                           border_width=1, border_color=BORDER_SUBTLE)
        s3.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(s3, text="💾 Sohbet Geçmişi",
                     font=ctk.CTkFont(size=FONT_HEADING, weight="bold"),
                     text_color=TEXT_PRIMARY).pack(anchor="w", padx=20, pady=(18, 12))
        
        btn_row = ctk.CTkFrame(s3, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 18))
        ctk.CTkButton(btn_row, text="📂 Klasörü Aç", command=self._open_history_folder,
                      width=160, height=40, corner_radius=8,
                      fg_color=BTN_SECONDARY, hover_color=BTN_SECONDARY_HOVER
                      ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="🗑️ Aktif Sohbeti Sil", command=self._clear_history,
                      fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER,
                      width=160, height=40, corner_radius=8
                      ).pack(side="left")

        self._refresh_rag_models()

    def _save_settings(self):
        """Kullanıcının girdiği ayarları diske kalıcı olarak kaydeder."""
        prov = self.provider_var.get()
        key = self.api_key_entry.get().strip()
        rag_mod = self.rag_base_model_var.get()
        
        self.config_manager.set("provider", prov, auto_save=False)
        self.config_manager.set("api_key", key, auto_save=False)
        self.config_manager.set("rag_base_model", rag_mod, auto_save=True)
        messagebox.showinfo("Başarılı", "✓ Ayarlar başarıyla kaydedildi!")

    def _refresh_rag_models(self):
        models = self.model_manager.list_ollama_models()
        self.rag_model_dropdown.configure(values=["Otomatik (En iyi model)"] + models)

    def _open_history_folder(self):
        folder = os.path.join(self._BASE_DIR, "chat_history")
        os.makedirs(folder, exist_ok=True)
        try:
            if os.name == 'nt':
                os.startfile(folder)
            else:
                import subprocess
                subprocess.Popen(['xdg-open', folder])
        except Exception as e:
            logger.error(f"Klasör açma hatası: {e}")
            messagebox.showinfo("Konum", f"Sohbet geçmişi:\n{folder}")

    def _clear_history(self):
        if messagebox.askyesno("Onay", "Mevcut modelin sohbet geçmişi silinecek. Emin misiniz?"):
            result = self.chat_engine.clear_history()
            messagebox.showinfo("Sonuç", result)


if __name__ == "__main__":
    app = App()
    app.mainloop()
