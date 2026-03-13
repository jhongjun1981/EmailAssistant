"""
AI 邮件助手 - 自然语言发送邮件
主界面：Tkinter 现代聊天窗口
"""
import tkinter as tk
from tkinter import ttk, filedialog
import threading
import os
from datetime import datetime

from config_manager import load_config, save_config
from intent_parser import parse_intent, chat_with_llm
from email_client import EmailClient

# ── 颜色主题 ──
COLORS = {
    "bg": "#EAEEF3",
    "sidebar": "#2B2D42",
    "sidebar_text": "#FFFFFF",
    "header": "#FFFFFF",
    "header_border": "#D0D5DD",
    "input_bg": "#FFFFFF",
    "input_border": "#D0D5DD",
    "user_bubble": "#4A6CF7",
    "user_text": "#FFFFFF",
    "bot_bubble": "#FFFFFF",
    "bot_text": "#1D2939",
    "success_bubble": "#ECFDF3",
    "success_text": "#027A48",
    "error_bubble": "#FEF3F2",
    "error_text": "#B42318",
    "info_bubble": "#F2F4F7",
    "info_text": "#667085",
    "time_text": "#98A2B3",
    "btn_primary": "#4A6CF7",
    "btn_primary_hover": "#3B5DE7",
    "btn_text": "#FFFFFF",
    "attach_bg": "#F2F4F7",
    "attach_text": "#344054",
}


class RoundedButton(tk.Canvas):
    """圆角按钮"""
    def __init__(self, parent, text="", command=None, bg="#4A6CF7", fg="#FFFFFF",
                 hover_bg="#3B5DE7", width=70, height=34, radius=8, font=None, **kw):
        super().__init__(parent, width=width, height=height,
                         bg=parent["bg"] if isinstance(parent, tk.Widget) and "bg" in parent.keys() else COLORS["bg"],
                         highlightthickness=0, **kw)
        self._bg = bg
        self._fg = fg
        self._hover_bg = hover_bg
        self._command = command
        self._text = text
        self._radius = radius
        self._width = width
        self._height = height
        self._font = font or ("Microsoft YaHei UI", 9)
        self._enabled = True

        self._draw(bg)
        self.bind("<Enter>", lambda e: self._draw(hover_bg) if self._enabled else None)
        self.bind("<Leave>", lambda e: self._draw(bg) if self._enabled else None)
        self.bind("<Button-1>", self._on_click)

    def _draw(self, color):
        self.delete("all")
        r = self._radius
        w, h = self._width, self._height
        # 圆角矩形
        self.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=color, outline=color)
        self.create_arc(w-r*2, 0, w, r*2, start=0, extent=90, fill=color, outline=color)
        self.create_arc(0, h-r*2, r*2, h, start=180, extent=90, fill=color, outline=color)
        self.create_arc(w-r*2, h-r*2, w, h, start=270, extent=90, fill=color, outline=color)
        self.create_rectangle(r, 0, w-r, h, fill=color, outline=color)
        self.create_rectangle(0, r, w, h-r, fill=color, outline=color)
        # 文字
        self.create_text(w//2, h//2, text=self._text, fill=self._fg, font=self._font)

    def _on_click(self, event):
        if self._enabled and self._command:
            self._command()

    def set_enabled(self, enabled):
        self._enabled = enabled
        if enabled:
            self._draw(self._bg)
        else:
            self._draw("#A0A0A0")


class ChatBubble(tk.Frame):
    """聊天气泡"""
    def __init__(self, parent, sender, text, bubble_type="bot", timestamp=None):
        super().__init__(parent, bg=COLORS["bg"])
        self.columnconfigure(0, weight=1)

        ts = timestamp or datetime.now().strftime("%H:%M")
        is_user = bubble_type == "user"

        # 气泡颜色
        bubble_colors = {
            "user": (COLORS["user_bubble"], COLORS["user_text"]),
            "bot": (COLORS["bot_bubble"], COLORS["bot_text"]),
            "success": (COLORS["success_bubble"], COLORS["success_text"]),
            "error": (COLORS["error_bubble"], COLORS["error_text"]),
            "info": (COLORS["info_bubble"], COLORS["info_text"]),
        }
        bg_color, fg_color = bubble_colors.get(bubble_type, bubble_colors["bot"])

        # 外层容器 - 控制左右对齐
        row_frame = tk.Frame(self, bg=COLORS["bg"])
        row_frame.pack(fill="x", padx=12, pady=3)

        if is_user:
            # 用户消息 - 右对齐
            spacer = tk.Frame(row_frame, bg=COLORS["bg"])
            spacer.pack(side="left", fill="x", expand=True)

        # 气泡内容
        bubble_frame = tk.Frame(row_frame, bg=bg_color, padx=14, pady=10)
        bubble_frame.pack(side="right" if is_user else "left", anchor="e" if is_user else "w")

        # 圆角效果（通过border模拟）
        bubble_frame.configure(highlightbackground=bg_color, highlightthickness=1,
                                bd=0, relief="flat")

        if not is_user and sender:
            # 发送者名称
            name_label = tk.Label(bubble_frame, text=sender, bg=bg_color, fg=fg_color,
                                   font=("Microsoft YaHei UI", 9, "bold"), anchor="w")
            name_label.pack(anchor="w")

        # 消息文本
        msg_label = tk.Label(bubble_frame, text=text, bg=bg_color, fg=fg_color,
                              font=("Microsoft YaHei UI", 10), anchor="w",
                              justify="left", wraplength=420)
        msg_label.pack(anchor="w")

        # 时间
        time_frame = tk.Frame(row_frame, bg=COLORS["bg"])
        time_frame.pack(side="right" if is_user else "left", padx=5, anchor="s")
        tk.Label(time_frame, text=ts, bg=COLORS["bg"], fg=COLORS["time_text"],
                 font=("Microsoft YaHei UI", 8)).pack(anchor="s")

        if not is_user:
            spacer2 = tk.Frame(row_frame, bg=COLORS["bg"])
            spacer2.pack(side="right", fill="x", expand=True)


class SettingsDialog(tk.Toplevel):
    """设置对话框"""

    def __init__(self, parent, config):
        super().__init__(parent)
        self.title("设置")
        self.config = config
        self.result = None
        self.geometry("520x500")
        self.resizable(False, False)
        self.configure(bg="#FFFFFF")
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._center_window()

    def _center_window(self):
        self.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() - self.winfo_width()) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build_ui(self):
        bg = "#FFFFFF"
        pad = {"padx": 15, "pady": 8}

        # 标题
        title_frame = tk.Frame(self, bg=COLORS["sidebar"], height=50)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="  设置", bg=COLORS["sidebar"], fg="#FFFFFF",
                 font=("Microsoft YaHei UI", 13, "bold")).pack(side="left", padx=10, pady=10)

        content = tk.Frame(self, bg=bg)
        content.pack(fill="both", expand=True, padx=0, pady=0)

        # === 模型选择 ===
        self._section_label(content, "AI 模型设置")

        row1 = tk.Frame(content, bg=bg)
        row1.pack(fill="x", **pad)
        tk.Label(row1, text="解析模型", bg=bg, font=("Microsoft YaHei UI", 9)).pack(side="left")
        self.model_var = tk.StringVar(value=self.config.get("model", "zhipu"))
        model_names = {k: v["name"] for k, v in self.config["models"].items()}
        self.model_combo = ttk.Combobox(row1, textvariable=self.model_var,
                                         values=list(model_names.keys()),
                                         state="readonly", width=25)
        self.model_combo.pack(side="right")
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_change)

        self.model_desc = tk.Label(content, text=model_names.get(self.model_var.get(), ""),
                                    bg=bg, fg="#667085", font=("Microsoft YaHei UI", 8))
        self.model_desc.pack(anchor="e", padx=15)

        row2 = tk.Frame(content, bg=bg)
        row2.pack(fill="x", **pad)
        tk.Label(row2, text="API Key", bg=bg, font=("Microsoft YaHei UI", 9)).pack(side="left")
        self.apikey_var = tk.StringVar()
        current_model = self.config["models"].get(self.model_var.get(), {})
        self.apikey_var.set(current_model.get("api_key", ""))
        self.apikey_entry = tk.Entry(row2, textvariable=self.apikey_var, show="*",
                                      font=("Microsoft YaHei UI", 9), relief="solid", bd=1)
        self.apikey_entry.pack(side="right", fill="x", expand=True, padx=(10, 0))

        # === EmailMarketer ===
        self._section_label(content, "EmailMarketer API")

        row3 = tk.Frame(content, bg=bg)
        row3.pack(fill="x", **pad)
        tk.Label(row3, text="API 地址", bg=bg, font=("Microsoft YaHei UI", 9)).pack(side="left")
        self.em_url_var = tk.StringVar(value=self.config["emailmarketer"]["api_url"])
        tk.Entry(row3, textvariable=self.em_url_var, font=("Microsoft YaHei UI", 9),
                 relief="solid", bd=1).pack(side="right", fill="x", expand=True, padx=(10, 0))

        row4 = tk.Frame(content, bg=bg)
        row4.pack(fill="x", **pad)
        tk.Label(row4, text="API Key", bg=bg, font=("Microsoft YaHei UI", 9)).pack(side="left")
        self.em_key_var = tk.StringVar(value=self.config["emailmarketer"]["api_key"])
        tk.Entry(row4, textvariable=self.em_key_var, font=("Microsoft YaHei UI", 9),
                 relief="solid", bd=1).pack(side="right", fill="x", expand=True, padx=(10, 0))

        row5 = tk.Frame(content, bg=bg)
        row5.pack(fill="x", padx=15, pady=3)
        self.conn_status = tk.Label(row5, text="", bg=bg, fg="#667085", font=("Microsoft YaHei UI", 8))
        self.conn_status.pack(side="left")
        tk.Button(row5, text="测试连接", command=self._test_connection, bg="#F2F4F7",
                  fg="#344054", font=("Microsoft YaHei UI", 8), relief="solid", bd=1,
                  cursor="hand2").pack(side="right")

        # === 按钮 ===
        btn_frame = tk.Frame(self, bg=bg)
        btn_frame.pack(fill="x", padx=15, pady=15, side="bottom")

        tk.Button(btn_frame, text="取消", command=self.destroy, bg="#F2F4F7", fg="#344054",
                  font=("Microsoft YaHei UI", 10), relief="flat", padx=20, pady=6,
                  cursor="hand2").pack(side="right", padx=(5, 0))
        tk.Button(btn_frame, text="保存", command=self._save, bg=COLORS["btn_primary"],
                  fg="#FFFFFF", font=("Microsoft YaHei UI", 10), relief="flat", padx=20, pady=6,
                  cursor="hand2", activebackground=COLORS["btn_primary_hover"],
                  activeforeground="#FFFFFF").pack(side="right")

    def _section_label(self, parent, text):
        frame = tk.Frame(parent, bg="#FFFFFF")
        frame.pack(fill="x", padx=15, pady=(12, 0))
        tk.Label(frame, text=text, bg="#FFFFFF", fg=COLORS["sidebar"],
                 font=("Microsoft YaHei UI", 10, "bold")).pack(side="left")
        # 分割线
        sep = tk.Frame(frame, bg=COLORS["header_border"], height=1)
        sep.pack(side="left", fill="x", expand=True, padx=(10, 0), pady=1)

    def _on_model_change(self, event=None):
        key = self.model_var.get()
        model = self.config["models"].get(key, {})
        self.model_desc.config(text=model.get("name", ""))
        self.apikey_var.set(model.get("api_key", ""))
        state = "disabled" if key == "local" else "normal"
        self.apikey_entry.config(state=state)

    def _test_connection(self):
        client = EmailClient(self.em_url_var.get(), self.em_key_var.get())
        if client.check_health():
            self.conn_status.config(text="连接成功!", fg="#027A48")
        else:
            self.conn_status.config(text="连接失败", fg="#B42318")

    def _save(self):
        model_key = self.model_var.get()
        self.config["models"][model_key]["api_key"] = self.apikey_var.get()
        self.config["model"] = model_key
        self.config["emailmarketer"]["api_url"] = self.em_url_var.get()
        self.config["emailmarketer"]["api_key"] = self.em_key_var.get()
        save_config(self.config)
        self.result = self.config
        self.destroy()


class ChatWindow:
    """主聊天窗口"""

    def __init__(self):
        self.config = load_config()
        self.root = tk.Tk()
        self.root.title("AI 邮件助手")
        self.root.geometry("750x650")
        self.root.minsize(550, 450)
        self.root.configure(bg=COLORS["bg"])
        self.current_attachment = None
        self._build_ui()
        self._show_welcome()

    def _build_ui(self):
        # ── 顶部标题栏 ──
        header = tk.Frame(self.root, bg=COLORS["header"], height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        # 左侧图标+标题
        tk.Label(header, text="  AI 邮件助手", bg=COLORS["header"], fg=COLORS["sidebar"],
                 font=("Microsoft YaHei UI", 14, "bold")).pack(side="left", padx=10)

        # 右侧状态+设置
        right_header = tk.Frame(header, bg=COLORS["header"])
        right_header.pack(side="right", padx=10)

        self.status_label = tk.Label(right_header, text="", bg=COLORS["header"],
                                      fg=COLORS["time_text"], font=("Microsoft YaHei UI", 8))
        self.status_label.pack(side="left", padx=(0, 10))

        settings_btn = tk.Label(right_header, text="  设置", bg=COLORS["header"],
                                 fg=COLORS["info_text"], font=("Microsoft YaHei UI", 9),
                                 cursor="hand2")
        settings_btn.pack(side="left")
        settings_btn.bind("<Button-1>", lambda e: self._open_settings())
        settings_btn.bind("<Enter>", lambda e: settings_btn.config(fg=COLORS["btn_primary"]))
        settings_btn.bind("<Leave>", lambda e: settings_btn.config(fg=COLORS["info_text"]))

        # 分割线
        tk.Frame(self.root, bg=COLORS["header_border"], height=1).pack(fill="x")

        self._update_status()

        # ── 聊天区域（可滚动） ──
        chat_outer = tk.Frame(self.root, bg=COLORS["bg"])
        chat_outer.pack(fill="both", expand=True)

        self.chat_canvas = tk.Canvas(chat_outer, bg=COLORS["bg"], highlightthickness=0)
        self.chat_scrollbar = ttk.Scrollbar(chat_outer, orient="vertical",
                                             command=self.chat_canvas.yview)

        self.chat_frame = tk.Frame(self.chat_canvas, bg=COLORS["bg"])
        self.chat_frame.bind("<Configure>",
                              lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))

        self.chat_canvas_window = self.chat_canvas.create_window((0, 0), window=self.chat_frame,
                                                                   anchor="nw")
        self.chat_canvas.configure(yscrollcommand=self.chat_scrollbar.set)

        self.chat_scrollbar.pack(side="right", fill="y")
        self.chat_canvas.pack(side="left", fill="both", expand=True)

        # 让内容宽度跟随窗口
        self.chat_canvas.bind("<Configure>", self._on_canvas_configure)

        # 鼠标滚轮
        self.chat_canvas.bind_all("<MouseWheel>",
                                   lambda e: self.chat_canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # ── 底部输入区 ──
        tk.Frame(self.root, bg=COLORS["header_border"], height=1).pack(fill="x")

        bottom = tk.Frame(self.root, bg=COLORS["header"], height=70)
        bottom.pack(fill="x")
        bottom.pack_propagate(False)

        # 附件栏（有附件时显示）
        self.attach_frame = tk.Frame(bottom, bg=COLORS["attach_bg"])
        self.attach_label = tk.Label(self.attach_frame, text="", bg=COLORS["attach_bg"],
                                      fg=COLORS["attach_text"], font=("Microsoft YaHei UI", 8))
        self.attach_label.pack(side="left", padx=8, pady=2)
        self.attach_remove_btn = tk.Label(self.attach_frame, text=" X ", bg=COLORS["attach_bg"],
                                           fg="#B42318", font=("Microsoft YaHei UI", 8),
                                           cursor="hand2")
        self.attach_remove_btn.pack(side="right", padx=5, pady=2)
        self.attach_remove_btn.bind("<Button-1>", lambda e: self._clear_attachment())

        # 输入行
        input_row = tk.Frame(bottom, bg=COLORS["header"])
        input_row.pack(fill="x", padx=12, pady=12)

        # 附件按钮
        attach_btn = tk.Label(input_row, text=" + ", bg=COLORS["input_bg"],
                               fg=COLORS["info_text"], font=("Microsoft YaHei UI", 14),
                               cursor="hand2", relief="flat")
        attach_btn.pack(side="left", padx=(0, 8))
        attach_btn.bind("<Button-1>", lambda e: self._select_attachment())
        attach_btn.bind("<Enter>", lambda e: attach_btn.config(fg=COLORS["btn_primary"]))
        attach_btn.bind("<Leave>", lambda e: attach_btn.config(fg=COLORS["info_text"]))

        # 输入框
        input_frame = tk.Frame(input_row, bg=COLORS["input_border"], bd=1, relief="solid")
        input_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.input_entry = tk.Entry(input_frame, font=("Microsoft YaHei UI", 11),
                                     bg=COLORS["input_bg"], fg=COLORS["bot_text"],
                                     relief="flat", bd=6, insertbackground=COLORS["bot_text"])
        self.input_entry.pack(fill="x", expand=True)
        self.input_entry.bind("<Return>", lambda e: self._on_send())
        self.input_entry.focus_set()

        # 发送按钮
        self.send_btn = RoundedButton(input_row, text="发送", command=self._on_send,
                                       bg=COLORS["btn_primary"], hover_bg=COLORS["btn_primary_hover"],
                                       width=65, height=36, font=("Microsoft YaHei UI", 10))
        self.send_btn.pack(side="right")

    def _on_canvas_configure(self, event):
        self.chat_canvas.itemconfig(self.chat_canvas_window, width=event.width)

    def _update_status(self):
        model_key = self.config.get("model", "local")
        model_name = self.config["models"].get(model_key, {}).get("name", "未知")
        has_key = bool(self.config["models"].get(model_key, {}).get("api_key"))
        if model_key == "local":
            status = f"{model_name}"
        elif has_key:
            status = f"{model_name}"
        else:
            status = f"{model_name} (无Key，本地规则)"
        self.status_label.config(text=status)

    def _show_welcome(self):
        self._add_bubble("邮件助手", (
            "你好! 我是 AI 邮件助手，用自然语言告诉我就能发邮件。\n\n"
            "例如:\n"
            "  - 给 test@qq.com 发邮件，标题会议通知，内容明天3点开会\n"
            "  - 发送 xxx@sina.com 营业执照 桌面\\图片.jpg\n"
            "  - 帮我把桌面上的报价单发到 xxx@163.com\n\n"
            "点击右上角「设置」可切换 AI 模型。"
        ), "bot")

    def _add_bubble(self, sender, text, bubble_type="bot"):
        bubble = ChatBubble(self.chat_frame, sender, text, bubble_type)
        bubble.pack(fill="x", anchor="w")
        # 滚动到底部
        self.root.after(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def _select_attachment(self):
        path = filedialog.askopenfilename(title="选择附件")
        if path:
            self.current_attachment = path
            fname = os.path.basename(path)
            self.attach_label.config(text=f"  {fname}")
            self.attach_frame.pack(fill="x", padx=12, pady=(4, 0), before=self.attach_frame.master.winfo_children()[-1])

    def _clear_attachment(self):
        self.current_attachment = None
        self.attach_label.config(text="")
        self.attach_frame.pack_forget()

    def _on_send(self):
        text = self.input_entry.get().strip()
        if not text:
            return

        self.input_entry.delete(0, "end")
        self._add_bubble("你", text, "user")

        attachment_override = self.current_attachment
        self._clear_attachment()

        self.send_btn.set_enabled(False)
        self.input_entry.config(state="disabled")

        threading.Thread(target=self._process_input, args=(text, attachment_override),
                         daemon=True).start()

    def _process_input(self, text, attachment_override=None):
        try:
            self._add_on_main("助手", "正在理解你的意思...", "info")
            intent = parse_intent(text, self.config)

            if "_warning" in intent:
                self._add_on_main("提示", intent["_warning"], "info")

            # 聊天回复（非邮件指令）
            if intent.get("action") == "chat":
                reply = intent.get("reply", "你好！有什么可以帮你的？")
                self._add_on_main("助手", reply, "bot")
                self._enable_input()
                return

            if intent.get("action") != "send":
                # 尝试用大模型聊天回复
                reply = chat_with_llm(text, self.config)
                self._add_on_main("助手", reply, "bot")
                self._enable_input()
                return

            to_email = intent.get("to_email")
            if not to_email:
                self._add_on_main("助手", "没有检测到收件人邮箱，请提供邮箱地址。", "error")
                self._enable_input()
                return

            subject = intent.get("subject") or "邮件"
            body = intent.get("body") or ""
            attachment = attachment_override or intent.get("attachment")

            info = f"收件人: {to_email}\n标题: {subject}"
            if body:
                info += f"\n正文: {body}"
            if attachment:
                exists = "存在" if os.path.exists(attachment) else "未找到!"
                info += f"\n附件: {attachment} ({exists})"
            self._add_on_main("解析结果", info, "info")

            if attachment and not os.path.exists(attachment):
                self._add_on_main("助手", f"附件文件不存在: {attachment}", "error")
                self._enable_input()
                return

            self._add_on_main("助手", "正在发送...", "info")
            em_config = self.config["emailmarketer"]
            client = EmailClient(em_config["api_url"], em_config["api_key"])

            result = client.send_email(
                to_email=to_email,
                subject=subject,
                body=body,
                attachment_path=attachment,
            )

            if result["success"]:
                self._add_on_main("助手", f"发送成功! 邮件已发送到 {to_email}", "success")
            else:
                self._add_on_main("助手", result["message"], "error")

        except Exception as e:
            self._add_on_main("助手", f"出错了: {str(e)}", "error")
        finally:
            self._enable_input()

    def _add_on_main(self, sender, text, tag):
        self.root.after(0, self._add_bubble, sender, text, tag)

    def _enable_input(self):
        def _do():
            self.send_btn.set_enabled(True)
            self.input_entry.config(state="normal")
            self.input_entry.focus_set()
        self.root.after(0, _do)

    def _open_settings(self):
        dialog = SettingsDialog(self.root, self.config)
        self.root.wait_window(dialog)
        if dialog.result:
            self.config = dialog.result
            self._update_status()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ChatWindow()
    app.run()
