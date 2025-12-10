import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
from backend.model_manager import ModelManager
from backend.chat_engine import ChatEngine

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # === TEMEL AYARLAR ===
        self.title("🤖 Yapay Zeka Stüdyosu")
        self.geometry("1300x800")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # === BACKEND ===
        self.model_manager = ModelManager()
        self.chat_engine = ChatEngine(self.model_manager)
        
        # === DURUM DEĞİŞKENLERİ ===
        self.files_to_train = []
        self.ollama_status = "bilinmiyor"
        self.history_visible = False

        # === LAYOUT (Responsive) ===
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._create_sidebar()
        self._create_pages()
        
        # Varsayılan sayfa
        self.show_page("chat")
        
        # Ollama kontrolü (arka planda)
        threading.Thread(target=self._check_ollama, daemon=True).start()

    def _check_ollama(self):
        """Ollama durumunu kontrol et"""
        try:
            import ollama
            result = ollama.list()
            if 'models' in result:
                count = len(result['models'])
                self.ollama_status = f"aktif ({count} model)"
                self.after(0, lambda: self.ollama_indicator.configure(
                    text=f"● Ollama: {self.ollama_status}", 
                    text_color="#4ade80"
                ))
            else:
                self.ollama_status = "çalışıyor (model yok)"
                self.after(0, lambda: self.ollama_indicator.configure(
                    text="○ Ollama: Model yok",
                    text_color="#fbbf24"
                ))
        except:
            self.ollama_status = "kapalı"
            self.after(0, lambda: self.ollama_indicator.configure(
                text="○ Ollama: Kapalı",
                text_color="#f87171"
            ))

    # === SIDEBAR ===
    
    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#1a1a1a")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)
        self.sidebar.grid_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(30, 20))
        
        ctk.CTkLabel(
            logo_frame, 
            text="🤖", 
            font=ctk.CTkFont(size=40)
        ).pack()
        
        ctk.CTkLabel(
            logo_frame, 
            text="AI Stüdyosu", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack()

        # Menü butonları
        btn_style = {
            "height": 45,
            "corner_radius": 10,
            "font": ctk.CTkFont(size=13),
            "anchor": "w"
        }
        
        self.btn_chat = ctk.CTkButton(
            self.sidebar, 
            text="  💬  Sohbet", 
            command=lambda: self.show_page("chat"),
            **btn_style
        )
        self.btn_chat.grid(row=1, column=0, padx=15, pady=8, sticky="ew")

        self.btn_models = ctk.CTkButton(
            self.sidebar, 
            text="  🎓  Modellerim", 
            command=lambda: self.show_page("models"),
            **btn_style
        )
        self.btn_models.grid(row=2, column=0, padx=15, pady=8, sticky="ew")

        self.btn_settings = ctk.CTkButton(
            self.sidebar, 
            text="  ⚙️  Ayarlar", 
            command=lambda: self.show_page("settings"),
            **btn_style
        )
        self.btn_settings.grid(row=3, column=0, padx=15, pady=8, sticky="ew")

        # Ollama durumu (altta)
        self.ollama_indicator = ctk.CTkLabel(
            self.sidebar, 
            text="○ Ollama: Kontrol ediliyor...", 
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.ollama_indicator.grid(row=6, column=0, padx=15, pady=20, sticky="s")

    # === SAYFALAR ===
    
    def _create_pages(self):
        """Tüm sayfaları oluştur"""
        self._create_chat_page()
        self._create_models_page()
        self._create_settings_page()

    def _create_chat_page(self):
        """Sohbet sayfası"""
        self.page_chat = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        
        # Responsive layout
        self.page_chat.grid_columnconfigure(1, weight=1)
        self.page_chat.grid_rowconfigure(0, weight=1)
        
        # === SOL: SOHBET GEÇMİŞİ (başlangıçta gizli) ===
        self.history_sidebar = ctk.CTkFrame(self.page_chat, width=280, corner_radius=10)
        
        ctk.CTkLabel(
            self.history_sidebar, 
            text="📜 Geçmiş Sohbetler", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=15)
        
        self.history_list_frame = ctk.CTkScrollableFrame(self.history_sidebar)
        self.history_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ctk.CTkButton(
            self.history_sidebar,
            text="🔄 Yenile",
            command=self.refresh_history_list,
            height=35,
            corner_radius=8
        ).pack(fill="x", padx=10, pady=10)
        
        # === SAĞ: ANA SOHBET ===
        chat_main = ctk.CTkFrame(self.page_chat, fg_color="transparent")
        chat_main.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        chat_main.grid_rowconfigure(1, weight=1)
        chat_main.grid_columnconfigure(0, weight=1)
        
        # Üst kısım
        header = ctk.CTkFrame(chat_main, height=70, corner_radius=10)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.history_toggle_btn = ctk.CTkButton(
            header, 
            text="☰", 
            width=50,
            height=50,
            command=self.toggle_history_sidebar,
            fg_color="#2d2d2d",
            hover_color="#3d3d3d",
            corner_radius=10
        )
        self.history_toggle_btn.pack(side="left", padx=15, pady=10)
        
        ctk.CTkLabel(header, text="Model:", font=ctk.CTkFont(weight="bold", size=13)).pack(side="left", padx=5)
        
        self.model_selector_var = ctk.StringVar(value="Model Seçiniz")
        self.model_dropdown = ctk.CTkOptionMenu(
            header, 
            variable=self.model_selector_var, 
            command=self.on_model_select,
            width=280,
            height=40,
            corner_radius=8
        )
        self.model_dropdown.pack(side="left", padx=5)
        
        ctk.CTkButton(
            header, 
            text="🔄", 
            width=50,
            height=40,
            command=self.refresh_model_list,
            fg_color="#2d2d2d",
            corner_radius=8
        ).pack(side="left", padx=5)

        # Sohbet kutusu
        self.chat_display = ctk.CTkTextbox(
            chat_main, 
            font=ctk.CTkFont(size=13),
            wrap="word",
            corner_radius=10
        )
        self.chat_display.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.chat_display.configure(state="disabled")

        # Alt kısım
        input_frame = ctk.CTkFrame(chat_main, height=80, corner_radius=10)
        input_frame.grid(row=2, column=0, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_entry = ctk.CTkEntry(
            input_frame, 
            placeholder_text="Mesajınızı buraya yazın...",
            height=50,
            corner_radius=10,
            font=ctk.CTkFont(size=13)
        )
        self.chat_entry.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        self.chat_entry.bind("<Return>", lambda e: self.send_message())
        
        ctk.CTkButton(
            input_frame, 
            text="Gönder ➤", 
            width=120, 
            height=50,
            command=self.send_message,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=1, padx=(0, 15), pady=15)

    def toggle_history_sidebar(self):
        """Geçmiş panelini aç/kapa"""
        if self.history_visible:
            self.history_sidebar.grid_forget()
            self.history_visible = False
        else:
            self.history_sidebar.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
            self.refresh_history_list()
            self.history_visible = True

    def _create_models_page(self):
        """Model oluşturma sayfası - DİNAMİK"""
        self.page_models = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.page_models.grid_rowconfigure(1, weight=1)
        self.page_models.grid_columnconfigure(0, weight=1)
        
        # Başlık
        title_frame = ctk.CTkFrame(self.page_models, height=80, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(
            title_frame, 
            text="🎓 Yeni AI Modeli Oluştur", 
            font=ctk.CTkFont(size=26, weight="bold")
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame, 
            text="Verilerinizle özelleştirilmiş yapay zeka modeli eğitin", 
            font=ctk.CTkFont(size=13),
            text_color="gray"
        ).pack(anchor="w", pady=(5, 0))

        # Ana içerik
        content_frame = ctk.CTkFrame(self.page_models, corner_radius=0, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(1, weight=1)
        
        # === STRATEJİ SEÇİMİ (ÜST - SABİT) ===
        strategy_container = ctk.CTkFrame(content_frame, corner_radius=10)
        strategy_container.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        
        ctk.CTkLabel(
            strategy_container, 
            text="1️⃣ Eğitim Yöntemi Seçin:", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 10))

        self.strategy_var = ctk.StringVar(value="RAG")
        self.strategy_var.trace_add("write", self.on_strategy_change)
        
        strategies_grid = ctk.CTkFrame(strategy_container, fg_color="transparent")
        strategies_grid.pack(fill="x", padx=20, pady=(0, 15))
        
        strategies = [
            ("RAG", "📚 Bilgi Bankası", "Hızlı • Büyük dosyalar • Sadece bu PC"),
            ("Ollama", "🚀 Taşınabilir Model", "Orta boyut • Başka PC'de çalışır"),
            ("FineTune", "🔬 Gerçek Eğitim", "Uzman • GPU gerekir • Ağırlık değiştirir")
        ]
        
        for i, (value, title, desc) in enumerate(strategies):
            card = ctk.CTkFrame(strategies_grid, corner_radius=10)
            card.grid(row=0, column=i, padx=8, pady=5, sticky="ew")
            strategies_grid.grid_columnconfigure(i, weight=1)
            
            ctk.CTkRadioButton(
                card, 
                text="", 
                variable=self.strategy_var, 
                value=value,
                width=20
            ).pack(side="left", padx=15, pady=15)
            
            text_frame = ctk.CTkFrame(card, fg_color="transparent")
            text_frame.pack(side="left", fill="both", expand=True, pady=15, padx=(0, 15))
            
            ctk.CTkLabel(
                text_frame, 
                text=title, 
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w"
            ).pack(fill="x")
            
            ctk.CTkLabel(
                text_frame, 
                text=desc, 
                font=ctk.CTkFont(size=11),
                text_color="gray",
                anchor="w"
            ).pack(fill="x")
        
        # === DİNAMİK FORM ALANI (ALT - DEĞİŞKEN) ===
        self.dynamic_form_container = ctk.CTkScrollableFrame(content_frame, corner_radius=10)
        self.dynamic_form_container.grid(row=1, column=0, sticky="nsew")
        self.dynamic_form_container.grid_columnconfigure(0, weight=1)
        
        # İlk yükleme
        self.render_dynamic_form()

    def on_strategy_change(self, *args):
        """Strateji değiştiğinde formu yeniden çiz"""
        self.render_dynamic_form()

    def render_dynamic_form(self):
        """Seçilen stratejiye göre formu oluştur"""
        # Önceki widget'ları temizle
        for widget in self.dynamic_form_container.winfo_children():
            widget.destroy()
        
        strategy = self.strategy_var.get()
        
        # Ortak: Model İsmi
        ctk.CTkLabel(
            self.dynamic_form_container, 
            text="2️⃣ Model Bilgileri", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 15))
        
        name_frame = ctk.CTkFrame(self.dynamic_form_container, fg_color="transparent")
        name_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(name_frame, text="Model İsmi:", width=150, anchor="w").pack(side="left")
        self.model_name_entry = ctk.CTkEntry(
            name_frame, 
            placeholder_text="örn: kitap_asistani",
            height=40,
            corner_radius=8
        )
        self.model_name_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        # Baz Model (Ollama ve FineTune için)
        if strategy in ["Ollama", "FineTune"]:
            base_frame = ctk.CTkFrame(self.dynamic_form_container, fg_color="transparent")
            base_frame.pack(fill="x", padx=20, pady=10)
            
            ctk.CTkLabel(base_frame, text="Baz Model:", width=150, anchor="w").pack(side="left")
            
            self.base_model_var = ctk.StringVar(value="Yükleniyor...")
            self.base_model_dropdown = ctk.CTkOptionMenu(
                base_frame,
                variable=self.base_model_var,
                values=["Yükleniyor..."],
                height=40,
                corner_radius=8,
                width=250
            )
            self.base_model_dropdown.pack(side="left", padx=(10, 5))
            
            ctk.CTkButton(
                base_frame,
                text="🔄",
                width=40,
                height=40,
                command=self.refresh_base_models,
                corner_radius=8
            ).pack(side="left")
            
            # Modelleri yükle
            self.refresh_base_models()
        
        # Dosya seçimi
        ctk.CTkLabel(
            self.dynamic_form_container, 
            text="3️⃣ Eğitim Dosyaları", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=20, pady=(25, 15))
        
        ctk.CTkButton(
            self.dynamic_form_container, 
            text="📁 Dosya Seç (PDF, TXT, Excel, Word...)", 
            command=self.select_files,
            height=45,
            corner_radius=8,
            font=ctk.CTkFont(size=13)
        ).pack(fill="x", padx=20, pady=5)
        
        self.file_label = ctk.CTkLabel(
            self.dynamic_form_container, 
            text="Henüz dosya seçilmedi", 
            text_color="gray",
            font=ctk.CTkFont(size=12)
        )
        self.file_label.pack(padx=20, pady=5)
        
        # Oluştur butonu
        ctk.CTkButton(
            self.dynamic_form_container, 
            text="🚀 MODELİ OLUŞTUR", 
            command=self.create_model,
            fg_color="#10b981",
            hover_color="#059669",
            height=55,
            corner_radius=10,
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(fill="x", padx=20, pady=(30, 15))
        
        # İlerleme
        self.progress = ctk.CTkProgressBar(self.dynamic_form_container, corner_radius=10)
        self.progress.pack(fill="x", padx=20, pady=(0, 20))
        self.progress.set(0)

    def refresh_base_models(self):
        """Ollama modellerini base model dropdown'a yükle"""
        models = self.model_manager.list_ollama_models()
        
        if models:
            self.base_model_dropdown.configure(values=models)
            self.base_model_var.set(models[0])
        else:
            self.base_model_dropdown.configure(values=["Model Yok - Ollama'yı başlatın"])
            self.base_model_var.set("Model Yok")

    def _create_settings_page(self):
        """Ayarlar sayfası"""
        self.page_settings = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        
        # Başlık
        ctk.CTkLabel(
            self.page_settings, 
            text="⚙️ Ayarlar", 
            font=ctk.CTkFont(size=26, weight="bold")
        ).pack(anchor="w", padx=30, pady=(30, 10))
        
        # === AI PROVIDER ===
        provider_section = ctk.CTkFrame(self.page_settings, corner_radius=10)
        provider_section.pack(fill="x", padx=30, pady=15)
        
        ctk.CTkLabel(
            provider_section, 
            text="🤖 Yapay Zeka Motoru", 
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 15))
        
        self.provider_var = ctk.StringVar(value="Ollama (Local)")
        
        providers = [
            ("Ollama (Local)", "🏠 Yerel • Ücretsiz • Hızlı"),
            ("OpenAI", "☁️ Cloud • GPT-4 • Ücretli"),
            ("Google AI", "🔍 Gemini • Cloud • Ücretli"),
            ("Anthropic", "🧠 Claude • Cloud • Ücretli"),
        ]
        
        for value, label in providers:
            ctk.CTkRadioButton(
                provider_section,
                text=label,
                variable=self.provider_var,
                value=value,
                font=ctk.CTkFont(size=13)  
            ).pack(anchor="w", padx=40, pady=5)
        
        # API Key
        ctk.CTkLabel(
            provider_section, 
            text="🔑 API Anahtarı (Cloud servisler için)", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 5))
        
        self.api_key_entry = ctk.CTkEntry(
            provider_section, 
            placeholder_text="API anahtarınızı buraya girin...",
            height=40,
            corner_radius=8
        )
        self.api_key_entry.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(
            provider_section, 
            text="💡 Ollama (Yerel) için API anahtarı gerekmez",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=20, pady=(5, 20))
        
        # === RAG MODEL ===
        rag_section = ctk.CTkFrame(self.page_settings, corner_radius=10)
        rag_section.pack(fill="x", padx=30, pady=15)
        
        ctk.CTkLabel(
            rag_section, 
            text="📚 RAG (Bilgi Bankası) için Model", 
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 15))
        
        rag_model_frame = ctk.CTkFrame(rag_section, fg_color="transparent")
        rag_model_frame.pack(fill="x", padx=20, pady=10)
        
        self.rag_base_model_var = ctk.StringVar(value="Otomatik (En iyi model)")
        self.rag_model_dropdown = ctk.CTkOptionMenu(
            rag_model_frame,
            variable=self.rag_base_model_var,
            values=["Otomatik (En iyi model)"],
            height=40,
            corner_radius=8,
            width=320
        )
        self.rag_model_dropdown.pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            rag_model_frame,
            text="🔄 Yenile",
            width=100,
            height=40,
            command=self.refresh_rag_models,
            corner_radius=8
        ).pack(side="left")
        
        ctk.CTkLabel(
            rag_section, 
            text="ℹ️ Otomatik modda tercih sırası: deepseek-r1 > llama3 > phi3 > ilk model",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).pack(anchor="w", padx=20, pady=(5, 20))
        
        # === SOHBET GEÇMİŞİ ===
        history_section = ctk.CTkFrame(self.page_settings, corner_radius=10)
        history_section.pack(fill="x", padx=30, pady=15)
        
        ctk.CTkLabel(
            history_section, 
            text="💾 Sohbet Geçmişi", 
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(anchor="w", padx=20, pady=(20, 15))
        
        hist_btn_frame = ctk.CTkFrame(history_section, fg_color="transparent")
        hist_btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        ctk.CTkButton(
            hist_btn_frame, 
            text="📂 Klasörü Aç", 
            command=self.open_history_folder,
            width=180,
            height=45,
            corner_radius=8
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            hist_btn_frame, 
            text="🗑️ Aktif Sohbeti Sil", 
            command=self.clear_current_history,
            fg_color="#ef4444",
            hover_color="#dc2626",
            width=180,
            height=45,
            corner_radius=8
        ).pack(side="left")
        
        self.refresh_rag_models()

    def refresh_rag_models(self):
        """RAG için kullanılabilecek modelleri yükle"""
        ollama_models = self.model_manager.list_ollama_models()
        options = ["Otomatik (En iyi model)"] + ollama_models
        self.rag_model_dropdown.configure(values=options)

    # === SAYFA YÖNETİMİ ===
    
    def show_page(self, page_name):
        """Sayfaları göster/gizle"""
        # Buton renklerini güncelle
        active_color = ("#3b82f6", "#2563eb")
        inactive_color = "transparent"
        
        self.btn_chat.configure(fg_color=active_color if page_name == "chat" else inactive_color)
        self.btn_models.configure(fg_color=active_color if page_name == "models" else inactive_color)
        self.btn_settings.configure(fg_color=active_color if page_name == "settings" else inactive_color)
        
        # Sayfaları göster/gizle
        for page_obj in [self.page_chat, self.page_models, self.page_settings]:
            page_obj.grid_forget()
        
        if page_name == "chat":
            self.page_chat.grid(row=0, column=1, sticky="nsew")
            self.refresh_model_list()
        elif page_name == "models":
            self.page_models.grid(row=0, column=1, sticky="nsew")
        elif page_name == "settings":
            self.page_settings.grid(row=0, column=1, sticky="nsew")

    # === MODEL YÖNETİMİ ===
    
    def refresh_model_list(self):
        """Model listesini güncelle"""
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

    def refresh_history_list(self):
        """Sohbet geçmişi listesini güncelle"""
        import os
        import json
        
        for widget in self.history_list_frame.winfo_children():
            widget.destroy()
        
        history_dir = "chat_history"
        if not os.path.exists(history_dir):
            ctk.CTkLabel(
                self.history_list_frame, 
                text="Henüz sohbet yok", 
                text_color="gray"
            ).pack(pady=20)
            return
        
        history_files = [f for f in os.listdir(history_dir) if f.endswith('.json')]
        
        if not history_files:
            ctk.CTkLabel(
                self.history_list_frame, 
                text="Henüz sohbet yok", 
                text_color="gray"
            ).pack(pady=20)
            return
        
        for filename in sorted(history_files, reverse=True):
            filepath = os.path.join(history_dir, filename)
            model_name = filename.replace('.json', '')
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    preview = data[0].get('content', '')[:25] + "..." if data else "(Boş)"
            except:
                preview = "(Hata)"
            
            row_frame = ctk.CTkFrame(self.history_list_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=3)
            
            btn = ctk.CTkButton(
                row_frame,
                text=f"{model_name}\n{preview}",
                command=lambda mn=model_name: self.load_history_conversation(mn),
                anchor="w",
                height=55,
                corner_radius=8
            )
            btn.pack(side="left", fill="x", expand=True, padx=(0, 3))
            
            ctk.CTkButton(
                row_frame,
                text="✖",
                width=35,
                height=55,
                command=lambda fp=filepath, mn=model_name: self.delete_history(fp, mn),
                fg_color="#ef4444",
                hover_color="#dc2626",
                corner_radius=8
            ).pack(side="right")

    def delete_history(self, filepath, model_name):
        """Sohbet geçmişini sil"""
        import os
        if messagebox.askyesno("Onay", f"'{model_name}' sohbetini silmek istediğinizden emin misiniz?"):
            try:
                os.remove(filepath)
                messagebox.showinfo("Başarılı", "Sohbet geçmişi silindi")
                self.refresh_history_list()
            except Exception as e:
                messagebox.showerror("Hata", f"Silinemedi: {e}")

    def load_history_conversation(self, model_name):
        """Belirli bir sohbet geçmişini yükle ve göster"""
        import os
        import json
        
        self.model_selector_var.set(model_name)
        self.on_model_select(model_name)
        
        filepath = os.path.join("chat_history", f"{model_name}.json")
        if not os.path.exists(filepath):
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            self.chat_display.configure(state="normal")
            self.chat_display.delete("1.0", "end")
            
            for msg in history:
                role = msg.get('role', '?')
                content = msg.get('content', '')
                time = msg.get('time', '')
                
                if role == 'human':
                    self.chat_display.insert("end", f"\n😊 Siz ({time}):\n{content}\n")
                elif role == 'ai':
                    self.chat_display.insert("end", f"\n🤖 AI ({time}):\n{content}\n")
            
            self.chat_display.see("end")
            self.chat_display.configure(state="disabled")
        
        except Exception as e:
            messagebox.showerror("Hata", f"Geçmiş yüklenemedi: {e}")

    def on_model_select(self, choice):
        """Model seçildiğinde"""
        if choice in ["Model Yok", "Model Seçiniz"]:
            return
        
        api_key = self.api_key_entry.get()
        provider_name = self.provider_var.get()
        
        # Provider mapping
        provider_map = {
            "Ollama (Local)": "ollama",
            "OpenAI": "openai",
            "Google AI": "google",
            "Anthropic": "anthropic"
        }
        provider = provider_map.get(provider_name, "ollama")
        
        preferred_rag = self.rag_base_model_var.get()
        
        def status_update(msg):
            self.chat_display.configure(state="normal")
            self.chat_display.insert("end", f"\n{msg}\n")
            self.chat_display.see("end")
            self.chat_display.configure(state="disabled")
            self.update()
        
        try:
            success, msg = self.chat_engine.load_model(
                choice, 
                api_key=api_key, 
                provider=provider,
                status_callback=status_update,
                preferred_rag_model=preferred_rag
            )
            
            self.chat_display.configure(state="normal")
            self.chat_display.insert("end", f"\n{msg}\n")
            self.chat_display.see("end")
            self.chat_display.configure(state="disabled")
            
            if not success:
                messagebox.showwarning("Uyarı", msg)
        
        except Exception as e:
            messagebox.showerror("Hata", f"Model yüklenemedi:\n{str(e)}")

    def select_files(self):
        """Dosya seç"""
        files = filedialog.askopenfilenames(
            title="Eğitim Dosyalarını Seçin",
            filetypes=[
                ("Desteklenen", "*.txt;*.pdf;*.docx;*.doc;*.xlsx;*.xls"),
                ("Tüm Dosyalar", "*.*")
            ]
        )
        
        if files:
            self.files_to_train = list(files)
            self.file_label.configure(text=f"✓ {len(files)} dosya seçildi")
        else:
            self.files_to_train = []
            self.file_label.configure(text="Henüz dosya seçilmedi")

    def create_model(self):
        """Model oluştur"""
        name = self.model_name_entry.get().strip()
        strategy = self.strategy_var.get()
        
        if not name:
            messagebox.showerror("Hata", "Lütfen bir model ismi girin!")
            return
        
        if not self.files_to_train:
            messagebox.showerror("Hata", "Lütfen en az bir dosya seçin!")
            return
        
        # Base model (Ollama ve FineTune için)
        base_model = None
        if strategy in ["Ollama", "FineTune"]:
            base_model = self.base_model_var.get()
            if not base_model or base_model == "Model Yok":
                messagebox.showerror("Hata", "Lütfen bir baz model seçin veya Ollama'yı başlatın!")
                return
        
        self.progress.set(0.2)
        
        def worker():
            try:
                if strategy == "RAG":
                    msg = self.model_manager.create_rag_model(name, self.files_to_train)
                elif strategy == "Ollama":
                    msg = self.model_manager.create_ollama_model(name, base_model, self.files_to_train)
                elif strategy == "FineTune":
                    msg = self.model_manager.create_finetune_model(name, base_model, self.files_to_train)
                
                self.after(0, lambda: self.progress.set(1.0))
                self.after(0, lambda: messagebox.showinfo("Başarılı!", msg))
                self.after(0, lambda: self.refresh_model_list())
                
                if strategy == "RAG":
                    self.after(0, lambda: self.model_selector_var.set(name))
                    self.after(0, lambda: self.on_model_select(name))
                
                self.files_to_train = []
                self.after(0, lambda: self.file_label.configure(text="Dosya seçilmedi"))
                self.after(0, lambda: self.progress.set(0))
            
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Hata", str(e)))
                self.after(0, lambda: self.progress.set(0))
        
        threading.Thread(target=worker, daemon=True).start()

    # === SOHBET ===
    
    def send_message(self):
        """Mesaj gönder"""
        msg = self.chat_entry.get().strip()
        if not msg:
            return
        
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"\n😊 Siz: {msg}\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")
        
        self.chat_entry.delete(0, "end")
        
        def worker():
            response = self.chat_engine.chat(msg)
            self.after(0, lambda: self._show_response(response))
        
        threading.Thread(target=worker, daemon=True).start()

    def _show_response(self, response):
        """Cevabı göster"""
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"🤖 AI: {response}\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    # === AYARLAR ===
    
    def open_history_folder(self):
        """Geçmiş klasörünü aç"""
        import os
        import subprocess
        folder = os.path.abspath("chat_history")
        
        if not os.path.exists(folder):
            os.makedirs(folder)
        
        try:
            subprocess.Popen(f'explorer "{folder}"')
        except:
            messagebox.showinfo("Konum", f"Sohbet geçmişi:\n{folder}")

    def clear_current_history(self):
        """Mevcut modelin geçmişini temizle"""
        if messagebox.askyesno("Onay", "Mevcut modelin sohbet geçmişi silinecek. Emin misiniz?"):
            result = self.chat_engine.clear_history()
            messagebox.showinfo("Sonuç", result)


if __name__ == "__main__":
    app = App()
    app.mainloop()
