"""
Modern UI Widget'ları — Chat balonları, Loading overlay, Typing indicator
"""
import customtkinter as ctk
from ui.theme import *


class ChatBubble(ctk.CTkFrame):
    """Tek bir sohbet mesaj balonu — Canlı streaming ve kod bloğu desteği."""
    
    def __init__(self, parent, message="", role="user", timestamp="", **kwargs):
        is_user = role == "user"
        self.is_user = is_user
        self.role = role
        self.message = message
        self.timestamp = timestamp
        bg = CHAT_USER_BG if is_user else CHAT_AI_BG
        
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0 if is_user else 1, weight=1)
        
        # Balon container
        self.bubble = ctk.CTkFrame(self, fg_color=bg, corner_radius=16)
        
        if is_user:
            self.bubble.grid(row=0, column=1, sticky="e", padx=(60, 8), pady=4)
        else:
            self.bubble.grid(row=0, column=0, sticky="w", padx=(8, 60), pady=4)
        
        # İkon ve isim
        header = ctk.CTkFrame(self.bubble, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 2))
        
        icon = "😊" if is_user else "🤖"
        name = "Siz" if is_user else "AI"
        
        ctk.CTkLabel(
            header, text=f"{icon} {name}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_PRIMARY,
            anchor="w"
        ).pack(side="left")
        
        if timestamp:
            self.time_label = ctk.CTkLabel(
                header, text=timestamp,
                font=ctk.CTkFont(size=9),
                text_color=TEXT_MUTED,
                anchor="e"
            )
            self.time_label.pack(side="right")
        
        # İçerik container
        self.content_frame = ctk.CTkFrame(self.bubble, fg_color="transparent")
        self.content_frame.pack(fill="x", padx=12, pady=(2, 8))
        
        # Mesaj metni label (streaming için)
        self.msg_label = ctk.CTkLabel(
            self.content_frame, text=message,
            font=ctk.CTkFont(size=FONT_BODY),
            text_color=TEXT_PRIMARY,
            wraplength=550,
            justify="left",
            anchor="w"
        )
        self.msg_label.pack(fill="x")
        
        # Alt buton çubuğu
        self.action_frame = ctk.CTkFrame(self.bubble, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=8, pady=(0, 6))
        
        self.copy_btn = None
        if not is_user and message:
            self.finalize()

    def _add_copy_button(self):
        if not self.copy_btn:
            self.copy_btn = ctk.CTkButton(
                self.action_frame, text="📋 Kopyala", width=70, height=24,
                fg_color="transparent",
                hover_color=BG_HOVER,
                corner_radius=6,
                font=ctk.CTkFont(size=10),
                text_color=TEXT_SECONDARY,
                command=lambda: self._copy_text(self.message)
            )
            self.copy_btn.pack(side="right", padx=4)

    def append_chunk(self, chunk):
        """Streaming sırasında gelen her token'ı ekler."""
        self.message += chunk
        self.msg_label.configure(text=self.message)

    def finalize(self):
        """Streaming tamamlandığında formatlama ve kopyalama butonunu ayarlar."""
        if not self.is_user:
            self._add_copy_button()
            self._render_code_blocks_if_any()

    def _render_code_blocks_if_any(self):
        """Eğer ``` ile çevrelenmiş kod bloğu varsa özel kutularda gösterir."""
        if "```" not in self.message:
            return
        
        parts = self.message.split("```")
        if len(parts) <= 1:
            return
            
        # Mevcut düz label'ı gizle
        self.msg_label.pack_forget()
        
        for i, part in enumerate(parts):
            if i % 2 == 0:
                text = part.strip()
                if text:
                    ctk.CTkLabel(
                        self.content_frame, text=text,
                        font=ctk.CTkFont(size=FONT_BODY),
                        text_color=TEXT_PRIMARY,
                        wraplength=550, justify="left", anchor="w"
                    ).pack(fill="x", pady=2)
            else:
                lines = part.split("\n", 1)
                lang = lines[0].strip() if len(lines) > 1 else ""
                code = lines[1] if len(lines) > 1 else lines[0]
                
                code_box = ctk.CTkFrame(self.content_frame, fg_color="#0b0b14", corner_radius=8, border_width=1, border_color=BORDER_COLOR)
                code_box.pack(fill="x", pady=4)
                
                code_header = ctk.CTkFrame(code_box, fg_color="#141426", height=26, corner_radius=6)
                code_header.pack(fill="x")
                
                ctk.CTkLabel(code_header, text=f"💻 {lang or 'code'}", font=ctk.CTkFont(size=10, weight="bold"), text_color=ACCENT_INFO).pack(side="left", padx=8)
                ctk.CTkButton(
                    code_header, text="Kopyala", width=55, height=20, font=ctk.CTkFont(size=9),
                    fg_color="transparent", hover_color=BG_HOVER,
                    command=lambda c=code: self._copy_text(c)
                ).pack(side="right", padx=6)
                
                code_tb = ctk.CTkTextbox(code_box, font=ctk.CTkFont(family="Consolas", size=11), fg_color="transparent", text_color="#38bdf8", activate_scrollbars=False)
                code_tb.insert("1.0", code.strip())
                code_tb.configure(state="disabled")
                lines_count = max(2, min(14, len(code.split("\n"))))
                code_tb.configure(height=lines_count * 18 + 10)
                code_tb.pack(fill="x", padx=6, pady=4)

    def _copy_text(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        if self.copy_btn:
            self.copy_btn.configure(text="✓ Kopyalandı!")
            self.after(1500, lambda: self.copy_btn.configure(text="📋 Kopyala"))


class TypingIndicator(ctk.CTkFrame):
    """●●● animasyonlu yazıyor göstergesi"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        bubble = ctk.CTkFrame(self, fg_color=CHAT_AI_BG, corner_radius=16)
        bubble.grid(row=0, column=0, sticky="w", padx=(8, 60), pady=4)
        
        header = ctk.CTkFrame(bubble, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            header, text="🤖 AI",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")
        
        self.dots_label = ctk.CTkLabel(
            bubble, text="●  ●  ●",
            font=ctk.CTkFont(size=16),
            text_color=ACCENT_PRIMARY,
        )
        self.dots_label.pack(padx=12, pady=(2, 12))
        
        self._dot_state = 0
        self._animating = True
        self._animate()
    
    def _animate(self):
        if not self._animating:
            return
        states = [
            ("●  ○  ○", ACCENT_PRIMARY),
            ("○  ●  ○", ACCENT_SECONDARY),
            ("○  ○  ●", ACCENT_INFO),
        ]
        state = states[self._dot_state % 3]
        self.dots_label.configure(text=state[0], text_color=state[1])
        self._dot_state += 1
        self.after(400, self._animate)
    
    def stop(self):
        self._animating = False


class LoadingOverlay(ctk.CTkFrame):
    """Yarı saydam loading ekranı"""
    
    def __init__(self, parent, message="Yükleniyor...", **kwargs):
        super().__init__(parent, fg_color=("gray20", "#0a0a1a"), corner_radius=0, **kwargs)
        
        center = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=16, 
                               width=320, height=180)
        center.place(relx=0.5, rely=0.5, anchor="center")
        center.pack_propagate(False)
        
        # Spinner label
        self.spinner_label = ctk.CTkLabel(
            center, text="⏳",
            font=ctk.CTkFont(size=36)
        )
        self.spinner_label.pack(pady=(30, 10))
        
        self.msg_label = ctk.CTkLabel(
            center, text=message,
            font=ctk.CTkFont(size=FONT_BODY),
            text_color=TEXT_PRIMARY
        )
        self.msg_label.pack(pady=5)
        
        self.status_label = ctk.CTkLabel(
            center, text="",
            font=ctk.CTkFont(size=FONT_SMALL),
            text_color=TEXT_SECONDARY
        )
        self.status_label.pack(pady=(0, 5))
        
        self.cancel_btn = ctk.CTkButton(
            center, text="İptal",
            fg_color=BTN_DANGER, hover_color=BTN_DANGER_HOVER,
            width=80, height=30, corner_radius=8,
            font=ctk.CTkFont(size=FONT_SMALL)
        )
        self.cancel_btn.pack(pady=(5, 15))
        
        self._spin_state = 0
        self._spinning = True
        self._spin_icons = ["◐", "◓", "◑", "◒"]
        self._spin()
    
    def _spin(self):
        if not self._spinning:
            return
        icon = self._spin_icons[self._spin_state % 4]
        self.spinner_label.configure(text=icon)
        self._spin_state += 1
        self.after(250, self._spin)
    
    def update_status(self, text):
        self.status_label.configure(text=text)
    
    def update_message(self, text):
        self.msg_label.configure(text=text)
    
    def stop(self):
        self._spinning = False


class TrainingLogPanel(ctk.CTkFrame):
    """Canlı eğitim log paneli"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=BG_CARD, corner_radius=12, **kwargs)
        
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(12, 5))
        
        ctk.CTkLabel(
            header, text="📊 Eğitim İlerlemesi",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT_PRIMARY
        ).pack(side="left")
        
        self.status_badge = ctk.CTkLabel(
            header, text="⏸ Bekliyor",
            font=ctk.CTkFont(size=FONT_SMALL),
            text_color=ACCENT_WARNING,
            fg_color=BG_SECONDARY,
            corner_radius=8,
            width=80, height=24
        )
        self.status_badge.pack(side="right")
        
        self.progress = ctk.CTkProgressBar(
            self, corner_radius=6,
            progress_color=ACCENT_PRIMARY,
            fg_color=BG_SECONDARY,
            height=8
        )
        self.progress.pack(fill="x", padx=15, pady=8)
        self.progress.set(0)
        
        self.log_box = ctk.CTkTextbox(
            self, font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=BG_PRIMARY, corner_radius=8,
            text_color=TEXT_SECONDARY, height=150
        )
        self.log_box.pack(fill="both", expand=True, padx=15, pady=(0, 12))
    
    def add_log(self, text):
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
    
    def set_progress(self, value):
        self.progress.set(min(1.0, max(0.0, value)))
    
    def set_status(self, text, color=None):
        self.status_badge.configure(text=text, text_color=color or ACCENT_PRIMARY)


class InfoTooltip(ctk.CTkLabel):
    """(?) ikonu — hover'da bilgi kutusu gösterir"""
    
    def __init__(self, parent, tooltip_text, **kwargs):
        super().__init__(
            parent, text="  ⓘ", cursor="hand2",
            font=ctk.CTkFont(size=14),
            text_color=ACCENT_INFO,
            **kwargs
        )
        self._tooltip_text = tooltip_text
        self._tooltip_window = None
        
        self.bind("<Enter>", self._show_tooltip)
        self.bind("<Leave>", self._hide_tooltip)
    
    def _show_tooltip(self, event=None):
        if self._tooltip_window:
            return
        
        x = self.winfo_rootx() + 25
        y = self.winfo_rooty() - 5
        
        import tkinter as tk
        self._tooltip_window = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg="#1e293b")
        
        # Border frame
        border = tk.Frame(tw, bg="#3b4f6b", padx=1, pady=1)
        border.pack(fill="both", expand=True)
        
        inner = tk.Frame(border, bg="#1e293b", padx=10, pady=8)
        inner.pack(fill="both", expand=True)
        
        tk.Label(
            inner, text=self._tooltip_text,
            font=("Segoe UI", 10),
            fg="#e2e8f0", bg="#1e293b",
            justify="left", wraplength=300
        ).pack()
    
    def _hide_tooltip(self, event=None):
        if self._tooltip_window:
            self._tooltip_window.destroy()
            self._tooltip_window = None
