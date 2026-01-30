# kuroshachi.pyw
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import sqlite3
import hashlib
import json
import math
from datetime import datetime
from pypdf import PdfReader
import fitz # type: ignore
from PIL import Image, ImageTk
import MeCab
import webbrowser
import traceback
import logging

# ログ設定
log_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
log_file = os.path.join(log_dir, 'pdf_cross_search.log')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # コンソールにも出力
    ]
)

logger = logging.getLogger(__name__)

# ttkbootstrapのインポート（テーマ適用用）
try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.constants import *
    HAS_TTKB = True
except ImportError as e:
    HAS_TTKB = False
    logger.warning(f"ttkbootstrapがインストールされていません: {str(e)}")

# tkinterwebのインポート（HTML表示用）
try:
    from tkinterweb import HtmlFrame
    HAS_WEB = True
except ImportError as e:
    HAS_WEB = False
    logger.warning(f"tkinterwebがインストールされていません: {str(e)}")

# アプリケーションのバージョン情報
APP_VERSION = "1.0.1"
APP_NAME = "黒鯱"

# リソースファイルのパスを取得する関数（EXE化時と通常実行時に対応）
def get_resource_path(relative_path):
    """リソースファイルのパスを取得
    
    Args:
        relative_path: リソースファイルの相対パス（例: 'kuroshachi_icon_512.png'）
    
    Returns:
        リソースファイルの絶対パス
    """
    try:
        # PyInstallerでEXE化された場合
        if getattr(sys, 'frozen', False):
            # EXEファイルのディレクトリ
            base_path = os.path.dirname(sys.executable)
            # リソースファイルはEXEと同じディレクトリにある
            resource_path = os.path.join(base_path, relative_path)
            if os.path.exists(resource_path):
                return resource_path
            # _MEIPASS（一時展開ディレクトリ）も確認
            if hasattr(sys, '_MEIPASS'):
                meipass_path = os.path.join(sys._MEIPASS, relative_path)
                if os.path.exists(meipass_path):
                    return meipass_path
        else:
            # 通常実行時
            base_path = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
            resource_path = os.path.join(base_path, relative_path)
            if os.path.exists(resource_path):
                return resource_path
    except Exception as e:
        logger.warning(f"リソースパスの取得に失敗: {str(e)}")
    
    # フォールバック: カレントディレクトリ
    return os.path.join(os.getcwd(), relative_path)

# メッセージボックスを親ウィンドウの中央に表示するヘルパー関数
def centered_messagebox(parent, message_type, title, message, return_result=False):
    """メッセージボックスを親ウィンドウの中央に表示（カスタムダイアログ）
    
    Args:
        parent: 親ウィンドウ
        message_type: メッセージタイプ ("error", "warning", "info", "question", "yesno")
        title: タイトル
        message: メッセージ
        return_result: Trueの場合、結果を返す（question/yesnoの場合のみ有効）
    
    Returns:
        return_resultがTrueの場合、OK/YesでTrue、Cancel/NoでFalseを返す
    """
    # カスタムダイアログを作成
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.transient(parent)
    dialog.grab_set()  # モーダルにする
    
    # 結果を保持する変数
    result = [False]
    
    # 親ウィンドウの位置とサイズを取得
    parent.update_idletasks()
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()
    
    # アイコンとメッセージタイプに応じた色を設定
    if message_type == "error":
        icon_text = "✕"
        icon_color = "#ff4444"
        button_style = "danger" if HAS_TTKB else None
    elif message_type == "warning":
        icon_text = "⚠"
        icon_color = "#ffaa00"
        button_style = "warning" if HAS_TTKB else None
    elif message_type == "yesno" or message_type == "question":
        icon_text = "?"
        icon_color = "#4a9eff"
        button_style = "primary" if HAS_TTKB else None
    else:  # info
        icon_text = "ℹ"
        icon_color = "#4a9eff"
        button_style = "info" if HAS_TTKB else None
    
    # メインフレーム
    if HAS_TTKB:
        main_frame = ttkb.Frame(dialog)
    else:
        main_frame = ttk.Frame(dialog)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    # アイコンとメッセージ
    content_frame = ttk.Frame(main_frame) if not HAS_TTKB else ttkb.Frame(main_frame)
    content_frame.pack(fill=tk.BOTH, expand=True)
    
    # アイコン
    icon_label = tk.Label(content_frame, text=icon_text, font=('Yu Gothic UI', 24), fg=icon_color)
    icon_label.pack(side=tk.LEFT, padx=(0, 15))
    
    # メッセージ
    message_label = tk.Label(content_frame, text=message, font=('Yu Gothic UI', 11), 
                            justify=tk.LEFT, wraplength=400)
    message_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # ボタンフレーム
    button_frame = ttk.Frame(main_frame) if not HAS_TTKB else ttkb.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(15, 0))
    
    result = [None]  # リストでラップして参照渡しにする
    
    if message_type == "yesno" or message_type == "question":
        # Yes/Noボタン
        def on_yes():
            result[0] = True
            dialog.destroy()
        
        def on_no():
            result[0] = False
            dialog.destroy()
        
        if HAS_TTKB:
            yes_button = ttkb.Button(button_frame, text="はい", command=on_yes, bootstyle="primary")
            no_button = ttkb.Button(button_frame, text="いいえ", command=on_no, bootstyle="secondary")
        else:
            yes_button = ttk.Button(button_frame, text="はい", command=on_yes)
            no_button = ttk.Button(button_frame, text="いいえ", command=on_no)
        yes_button.pack(side=tk.RIGHT, padx=(5, 0))
        no_button.pack(side=tk.RIGHT)
    else:
        # OKボタン
        def on_ok():
            result[0] = True
            dialog.destroy()
        
        if HAS_TTKB:
            ok_button = ttkb.Button(button_frame, text="OK", command=on_ok, bootstyle=button_style)
        else:
            ok_button = ttk.Button(button_frame, text="OK", command=on_ok)
        ok_button.pack(side=tk.RIGHT)
    
    # ダイアログのサイズを計算
    dialog.update_idletasks()
    dialog_width = dialog.winfo_reqwidth()
    dialog_height = dialog.winfo_reqheight()
    
    # 親ウィンドウの中央に配置
    x = parent_x + (parent_width // 2) - (dialog_width // 2)
    y = parent_y + (parent_height // 2) - (dialog_height // 2)
    dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    # ダイアログを表示して待機
    dialog.wait_window()
    
    # 結果を返す
    if return_result:
        return result[0] if result[0] is not None else False
    
    return result

class PDFViewerFrame(ttkb.Frame if HAS_TTKB else ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        
        # メインキャンバスとプレビューを含むフレーム
        if HAS_TTKB:
            FrameClass = ttkb.Frame
        else:
            FrameClass = ttk.Frame
        self.main_frame = FrameClass(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # プレビューフレーム（右上）
        self.preview_frame = FrameClass(self.main_frame)
        self.preview_frame.pack(side=tk.RIGHT, anchor=tk.NE, padx=5, pady=5)
        
        # ヘルプボタン（プレビューエリアの上部）
        ButtonClass = ttkb.Button if HAS_TTKB else ttk.Button
        help_frame = FrameClass(self.preview_frame)
        help_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))
        
        # コールバック関数（メインアプリケーションから設定）
        self.show_guide_callback = None
        self.show_about_callback = None
        self.show_operation_guide_callback = None
        
        # 操作説明ボタン
        self.operation_button = ButtonClass(
            help_frame,
            text="操作説明",
            command=self._on_operation_guide_click
        )
        if HAS_TTKB:
            self.operation_button.configure(bootstyle="secondary")
        self.operation_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        
        # 使い方ガイドボタン
        self.guide_button = ButtonClass(
            help_frame,
            text="使い方ガイド",
            command=self._on_guide_click
        )
        if HAS_TTKB:
            self.guide_button.configure(bootstyle="info")
        self.guide_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 2))
        
        # バージョン情報ボタン
        self.about_button = ButtonClass(
            help_frame,
            text="バージョン情報",
            command=self._on_about_click
        )
        if HAS_TTKB:
            self.about_button.configure(bootstyle="info")
        self.about_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
        
        # コンテンツフレーム（キャンバスとメタ情報用）
        self.preview_content_frame = FrameClass(self.preview_frame)
        self.preview_content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # プレビューキャンバス（ダークモード対応）
        canvas_bg = '#2b2b2b' if HAS_TTKB else 'gray90'  # ダークモード時は暗い背景色
        self.preview_canvas = tk.Canvas(
            self.preview_content_frame, 
            width=200,  # プレビューの幅
            height=283, # A4比率に合わせた高さ
            bg=canvas_bg
        )
        self.preview_canvas.pack()
        
        # プレビューエリアのナビゲーションボタン（メタ情報の下に配置するため、後でpack）
        ButtonClass = ttkb.Button if HAS_TTKB else ttk.Button
        self.nav_frame = FrameClass(self.preview_frame)
        # packはメタ情報の後に実行（update_pdf_info内で）
        
        # 前へボタン
        self.prev_button = ButtonClass(
            self.nav_frame, 
            text="◀", 
            width=3,
            command=self.navigate_prev_result
        )
        if HAS_TTKB:
            self.prev_button.configure(bootstyle="secondary")
        self.prev_button.pack(side=tk.LEFT, padx=2)
        
        # 初期表示に戻るボタン（ファイルアイコン）
        self.reset_button = ButtonClass(
            self.nav_frame, 
            text="📄", 
            width=3,
            command=self.reset_view
        )
        if HAS_TTKB:
            self.reset_button.configure(bootstyle="secondary")
        # フォントサイズを大きくしてアイコンを大きく表示（ボタンサイズは左右と同じ）
        style = ttk.Style()
        style.configure("LargeIcon.TButton", font=('Yu Gothic UI', 10))
        self.reset_button.configure(style="LargeIcon.TButton")
        self.reset_button.pack(side=tk.LEFT, padx=2)
        
        # 次へボタン
        self.next_button = ButtonClass(
            self.nav_frame, 
            text="▶", 
            width=3,
            command=self.navigate_next_result
        )
        if HAS_TTKB:
            self.next_button.configure(bootstyle="secondary")
        self.next_button.pack(side=tk.LEFT, padx=2)
        
        # コールバック関数（メインアプリケーションから設定）
        self.navigate_result_callback = None
        
        # メインキャンバス（ダークモード対応）
        self.canvas = tk.Canvas(self.main_frame, bg=canvas_bg)
        ScrollbarClass = ttkb.Scrollbar if HAS_TTKB else ttk.Scrollbar
        self.scrollbar = ScrollbarClass(self.main_frame, orient=tk.VERTICAL)
        
        # スクロールバーとキャンバスの設定
        self.scrollbar.config(command=self.canvas.yview)
        self.canvas.config(yscrollcommand=self.scrollbar.set)
        
        # パッキング
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 初期表示（ロゴとバージョン）をメインキャンバスに表示（キャンバスサイズ確定後に）
        self.canvas.after(100, self.show_initial_main_view)
        
        # PDF表示用の変数
        self.doc = None
        self.current_page = None
        self.zoom = 1.0
        self.search_term = None
        self.is_phrase_search = False  # フレーズ検索モードを保存
        self.current_text = None  # 現在のページのテキストを保持
        
        # マウスイベントのバインド
        self.canvas.bind('<MouseWheel>', self.on_zoom)          # マウスホイールで拡大・縮小
        self.canvas.bind('<Control-MouseWheel>', self.on_navigate_result)  # Ctrl+ホイールで検索結果の前後移動
        # 左クリックで手のひらツール（パン）
        self.canvas.bind('<Button-1>', self.start_pan)           # パン開始
        self.canvas.bind('<B1-Motion>', self.update_pan)         # パン更新
        self.canvas.bind('<ButtonRelease-1>', self.end_pan)      # パン終了
        self.canvas.bind('<Control-c>', self.copy_selection)     # コピー
        # 右クリックでテキスト選択
        self.canvas.bind('<Button-3>', self.start_select)        # 選択開始
        self.canvas.bind('<B3-Motion>', self.update_select)      # 選択更新
        self.canvas.bind('<ButtonRelease-3>', self.end_select)   # 選択終了
        
        # 選択用の変数
        self.start_x = None
        self.start_y = None
        self.selection_rect = None
        self.selected_text = ""
        self.text_highlights = []  # テキストハイライト用の矩形IDリスト
        self.text_blocks = []  # 現在のページのテキストブロック情報
        
        # 手のひらツール用の変数（右クリックドラッグ）
        self.image_id = None  # 画像のID
        self.image_x = 0  # 画像のX座標
        self.image_y = 0  # 画像のY座標
        self.pan_start_x = None  # パン開始時のマウスX座標
        self.pan_start_y = None  # パン開始時のマウスY座標
        self.pan_start_image_x = 0  # パン開始時の画像X座標
        self.pan_start_image_y = 0  # パン開始時の画像Y座標
        
    def on_zoom(self, event):
        """マウスホイールで拡大・縮小"""
        if event.delta > 0:
            self.zoom *= 1.1  # 拡大
        else:
            self.zoom *= 0.9  # 縮小
        self.zoom = max(0.1, min(5.0, self.zoom))  # ズーム範囲を制限
        
        # 選択をクリア（ズーム時に選択範囲が正しくない位置になるのを防ぐ）
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        self.selection_rect = None
        self.selected_text = ""
        self.start_x = None
        self.start_y = None
        
        # テキストハイライトも削除
        for highlight_id in self.text_highlights:
            self.canvas.delete(highlight_id)
        self.text_highlights = []
        
        # 現在のページを再表示（検索語とフレーズ検索モードを渡してハイライトを維持）
        if self.doc and self.current_page is not None:
            # case_sensitiveは検索オプションから取得（デフォルトはFalse）
            case_sensitive = getattr(self, 'case_sensitive', False)
            self.show_page(self.current_page, self.search_term, fit_to_page=False, 
                         is_phrase_search=self.is_phrase_search, case_sensitive=case_sensitive)
    
    def on_navigate_result(self, event):
        """Ctrl+ホイールで検索結果の前後を移動"""
        if self.navigate_result_callback:
            # 上にスクロール（delta > 0）で前へ、下にスクロール（delta < 0）で次へ
            direction = -1 if event.delta > 0 else 1
            self.navigate_result_callback(direction)
            
    def load_pdf(self, filepath, page=0):
        """PDFファイルを読み込む"""
        try:
            if self.doc:
                self.doc.close()
            self.doc = fitz.open(filepath)
            self.current_page = page
            self.current_path = filepath  # 現在のファイルパスを保存
            
            # PDFが切り替わったのでプレビューと情報を更新
            self.update_preview()
            self.update_pdf_info()
            
            return True
        except Exception as e:
            messagebox.showerror("エラー", f"PDFの読み込みに失敗: {str(e)}")
            return False

    def update_pdf_info(self):
        """PDF情報を更新"""
        if not self.doc:
            return
            
        try:
            # メタデータを取得
            metadata = self.doc.metadata
            
            # 1ページ目のサイズを取得
            first_page = self.doc[0]
            page_size = first_page.rect
            
            # ファイル名を取得
            filename = os.path.basename(self.current_path) if hasattr(self, 'current_path') and self.current_path else "不明"
            
            # ファイルサイズを取得
            try:
                if hasattr(self, 'current_path') and self.current_path and os.path.exists(self.current_path):
                    file_size = os.path.getsize(self.current_path)
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                else:
                    size_str = "不明"
            except:
                size_str = "不明"
            
            # セキュリティ情報を取得
            try:
                is_encrypted = self.doc.is_encrypted
                security_str = "あり" if is_encrypted else "なし"
            except:
                security_str = "不明"
            
            # 日付のフォーマット
            def format_date(date_str):
                if not date_str or date_str == '不明':
                    return '不明'
                try:
                    # PDF日付形式: D:YYYYMMDDHHmmSSOHH'mm
                    date_str = date_str.replace('D:', '')
                    if len(date_str) >= 8:
                        year = date_str[0:4]
                        month = date_str[4:6]
                        day = date_str[6:8]
                        return f"{year}-{month}-{day}"
                except:
                    pass
                return date_str[:8] if len(date_str) >= 8 else date_str
            
            # PDFバージョンの取得
            try:
                pdf_version_str = f"{self.doc.pdf_version / 10:.1f}" if self.doc.pdf_version else "不明"
            except:
                pdf_version_str = "不明"
            
            # タイトルの取得
            title = metadata.get('title', '不明')
            if not title or title.strip() == '':
                title = '不明'
            
            # 情報を表形式で表示（2列のテーブル）- 画像の順序に合わせる
            info_data = [
                ("ファイル名", filename),
                ("ファイルサイズ", size_str),
                ("ページ数", f"{len(self.doc)}ページ"),
                ("作成日", format_date(metadata.get('creationDate', ''))),
                ("更新日", format_date(metadata.get('modDate', ''))),
                ("PDFバージョン", pdf_version_str),
                ("セキュリティ", security_str),
                ("作成者", metadata.get('author', '不明')),
                ("タイトル", title),
                ("アプリケーション", metadata.get('producer', '不明'))
            ]
            
            # 既存の情報フレームを削除
            if hasattr(self, 'info_frame'):
                self.info_frame.destroy()
            
            # ナビゲーションボタンが既にpackされている場合は一度forget
            if hasattr(self, 'nav_frame') and self.nav_frame.winfo_manager() != '':
                self.nav_frame.pack_forget()
            
            # 情報表示用のフレームを作成（ダークグレーの背景）
            if HAS_TTKB:
                self.info_frame = ttkb.Labelframe(self.preview_content_frame, text="メタ情報", bootstyle="secondary")
            else:
                self.info_frame = ttk.LabelFrame(self.preview_content_frame, text="メタ情報")
                # 標準ttkの場合は背景色を設定
                style = ttk.Style()
                style.configure("Dark.TLabelframe", background="#404040")
                style.configure("Dark.TLabelframe.Label", background="#404040", foreground="white")
                self.info_frame.configure(style="Dark.TLabelframe")
            
            self.info_frame.pack(pady=(10, 0), padx=5, fill=tk.X)
            
            # 内部フレーム（パディング用）
            if HAS_TTKB:
                inner_frame = ttkb.Frame(self.info_frame)
            else:
                inner_frame = ttk.Frame(self.info_frame)
                inner_frame.configure(style="Dark.TLabelframe")
            inner_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
            
            # 表形式で情報を表示
            LabelClass = ttkb.Label if HAS_TTKB else ttk.Label
            for i, (label, value) in enumerate(info_data):
                # ラベル列
                label_widget = LabelClass(
                    inner_frame,
                    text=f"{label}:",
                    font=('Yu Gothic UI', 9),
                    anchor=tk.W
                )
                if not HAS_TTKB:
                    label_widget.configure(background="#404040", foreground="white")
                label_widget.grid(row=i, column=0, sticky=tk.W, padx=(0, 8), pady=2)
                
                # 値列
                value_widget = LabelClass(
                    inner_frame,
                    text=str(value),
                    font=('Yu Gothic UI', 9),
                    anchor=tk.W,
                    wraplength=180
                )
                if not HAS_TTKB:
                    value_widget.configure(background="#404040", foreground="white")
                value_widget.grid(row=i, column=1, sticky=tk.W, pady=2)
            
            # 列の幅を設定
            inner_frame.columnconfigure(0, weight=0, minsize=90)
            inner_frame.columnconfigure(1, weight=1)
            
            # ナビゲーションボタンを一番下に配置（上のマージンを小さく、センター揃え）
            if hasattr(self, 'nav_frame'):
                # 既にpackされている場合は一度forgetしてから再配置
                if self.nav_frame.winfo_manager() != '':
                    self.nav_frame.pack_forget()
                # 上のマージンを小さく（30px）、下のマージンは5px、センター揃え
                self.nav_frame.pack(side=tk.BOTTOM, pady=(30, 5), padx=5, anchor=tk.CENTER)
                
        except Exception as e:
            print(f"PDF情報の更新に失敗: {str(e)}")
            import traceback
            traceback.print_exc()

    def show_initial_main_view(self):
        """メインキャンバスに初期表示（ロゴとバージョン）を表示"""
        try:
            self.canvas.delete("all")
            
            # 画像ファイルのパスを取得（EXE化時にも対応）
            icon_path = get_resource_path("kuroshachi_icon_512.png")
            
            # キャンバスのサイズを取得
            self.canvas.update_idletasks()
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            if canvas_width <= 1:
                canvas_width = 800  # デフォルト幅
            if canvas_height <= 1:
                canvas_height = 600  # デフォルト高さ
            
            # 画像を読み込む
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                # 画像サイズを調整（メインキャンバスに収まるように）
                max_size = 256
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                self.initial_main_photoimg = ImageTk.PhotoImage(img)
                
                # 画像を中央に配置（上側に配置）
                img_x = (canvas_width - self.initial_main_photoimg.width()) // 2
                img_y = (canvas_height - self.initial_main_photoimg.height()) // 2 - 180
                self.canvas.create_image(
                    img_x, img_y,
                    anchor=tk.NW,
                    image=self.initial_main_photoimg
                )
                
                # 画像の下端位置を計算
                img_bottom = img_y + self.initial_main_photoimg.height()
            else:
                img_bottom = canvas_height // 2 - 100
            
            # テキストを中央に配置（画像の下、間隔を空けて）
            # タイトル「黒鯱」（画像の下から60px空ける）
            title_y = img_bottom + 60
            self.canvas.create_text(
                canvas_width // 2, title_y,
                text="黒鯱",
                font=('Yu Gothic UI', 24, 'bold'),
                fill='white',
                anchor=tk.CENTER
            )
            
            # 読み仮名「（KuroShachi）」
            subtitle_y = title_y + 35
            self.canvas.create_text(
                canvas_width // 2, subtitle_y,
                text="（KuroShachi）",
                font=('Yu Gothic UI', 14),
                fill='white',
                anchor=tk.CENTER
            )
            
            # バージョン
            version_y = subtitle_y + 40
            self.canvas.create_text(
                canvas_width // 2, version_y,
                text=f"Version {APP_VERSION}",
                font=('Yu Gothic UI', 14),
                fill='white',
                anchor=tk.CENTER
            )
        except Exception as e:
            print(f"初期メインビューの表示に失敗: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def show_initial_preview(self):
        """プレビューキャンバスに初期表示（ロゴとバージョン）を表示"""
        try:
            self.preview_canvas.delete("all")
            
            # 画像ファイルのパスを取得（EXE化時にも対応）
            icon_path = get_resource_path("kuroshachi_icon_512.png")
            
            # 画像を読み込む
            if os.path.exists(icon_path):
                img = Image.open(icon_path)
                # 画像サイズを調整（プレビューエリアに収まるように）
                max_size = 150
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                self.initial_photoimg = ImageTk.PhotoImage(img)
                
                # キャンバスのサイズを取得
                canvas_width = self.preview_canvas.winfo_width()
                canvas_height = self.preview_canvas.winfo_height()
                if canvas_width <= 1:
                    canvas_width = 200
                if canvas_height <= 1:
                    canvas_height = 283
                
                # 画像を中央に配置
                img_x = (canvas_width - self.initial_photoimg.width()) // 2
                img_y = (canvas_height - self.initial_photoimg.height()) // 2 - 40
                self.preview_canvas.create_image(
                    img_x, img_y,
                    anchor=tk.NW,
                    image=self.initial_photoimg
                )
            
            # タイトルとバージョンを表示
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            if canvas_width <= 1:
                canvas_width = 200
            if canvas_height <= 1:
                canvas_height = 283
            
            # タイトル
            title_y = canvas_height // 2 + 20
            self.preview_canvas.create_text(
                canvas_width // 2, title_y,
                text="黒鯱",
                font=('Yu Gothic UI', 16, 'bold'),
                fill='white' if HAS_TTKB else 'black',
                anchor=tk.CENTER
            )
            
            # バージョン
            version_y = title_y + 25
            self.preview_canvas.create_text(
                canvas_width // 2, version_y,
                text=f"Version {APP_VERSION}",
                font=('Yu Gothic UI', 10),
                fill='light gray' if HAS_TTKB else 'gray',
                anchor=tk.CENTER
            )
        except Exception as e:
            print(f"初期プレビューの表示に失敗: {str(e)}")
    
    def update_preview(self):
        """プレビュー（1ページ目）を更新"""
        if not self.doc:
            # PDFが読み込まれていない場合はプレビューキャンバスをクリア
            self.preview_canvas.delete("all")
            return
            
        try:
            preview_page = self.doc[0]
            # プレビューサイズに合わせたズーム計算
            preview_zoom = min(
                200 / preview_page.rect.width,
                283 / preview_page.rect.height
            )
            preview_matrix = fitz.Matrix(preview_zoom, preview_zoom)
            preview_pix = preview_page.get_pixmap(matrix=preview_matrix)
            
            self.preview_photoimg = ImageTk.PhotoImage(
                Image.frombytes("RGB", 
                              [preview_pix.width, preview_pix.height],
                              preview_pix.samples)
            )
            
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(
                0, 0, 
                anchor=tk.NW, 
                image=self.preview_photoimg
            )
            
            # プレビュー更新後、メタ情報も更新（確実に表示されるように）
            self.update_pdf_info()
        except Exception as e:
            print(f"プレビューの更新に失敗: {str(e)}")
    
    def navigate_prev_result(self):
        """検索結果の前の項目に移動"""
        if self.navigate_result_callback:
            self.navigate_result_callback(-1)  # -1は前へ
    
    def navigate_next_result(self):
        """検索結果の次の項目に移動"""
        if self.navigate_result_callback:
            self.navigate_result_callback(1)  # 1は次へ
    
    def reset_view(self):
        """初期表示に戻る（拡大縮小をリセット）"""
        if self.doc and self.current_page is not None:
            # 検索語を取得
            search_term = self.search_term
            is_phrase_search = self.is_phrase_search
            # case_sensitiveはPDFViewerFrameに保存されている
            case_sensitive = getattr(self, 'case_sensitive', False)
            # fit_to_page=Trueで初期表示に戻す
            self.show_page(self.current_page, search_term, fit_to_page=True, 
                         is_phrase_search=is_phrase_search, case_sensitive=case_sensitive)
    
    def _on_guide_click(self):
        """使い方ガイドボタンのクリックハンドラ"""
        if self.show_guide_callback:
            self.show_guide_callback()
    
    def _on_about_click(self):
        """バージョン情報ボタンのクリックハンドラ"""
        if self.show_about_callback:
            self.show_about_callback()
    
    def _on_operation_guide_click(self):
        """操作説明ボタンのクリックハンドラ"""
        if self.show_operation_guide_callback:
            self.show_operation_guide_callback()

    def start_select(self, event):
        """テキスト選択開始"""
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        # 既存の選択を削除
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None
        # テキストハイライトも削除
        for highlight_id in self.text_highlights:
            self.canvas.delete(highlight_id)
        self.text_highlights = []
        self.selected_text = ""
    
    def update_select(self, event):
        """選択範囲の更新"""
        if self.start_x is None or self.start_y is None:
            return
        
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        
        # 既存の選択矩形とテキストハイライトを削除
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None
        
        # 既存のテキストハイライトを削除
        for highlight_id in self.text_highlights:
            self.canvas.delete(highlight_id)
        self.text_highlights = []
        
        # 新しい選択矩形を描画（半透明）
        self.selection_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, cur_x, cur_y,
            outline='blue', fill='light blue', stipple='gray25', width=1
        )
        
        # テキスト選択を更新
        if self.doc and self.current_page is not None:
            page = self.doc[self.current_page]
            
            # 画像の実際の位置を取得（パンや拡大縮小後の位置）
            # image_x, image_yは画像の左上隅のキャンバス座標
            # canvasx()とcanvasy()は既にスクロール位置を考慮した座標を返す
            image_x = self.image_x if self.image_id else 0
            image_y = self.image_y if self.image_id else 0
            
            # 座標をPDF座標系に変換
            # キャンバス座標から画像の左上隅を引いて、ズーム倍率で割る
            start_point = (
                (self.start_x - image_x) / self.zoom,
                (self.start_y - image_y) / self.zoom
            )
            end_point = (
                (cur_x - image_x) / self.zoom,
                (cur_y - image_y) / self.zoom
            )
            
            # 選択範囲のテキストを取得
            rect = (min(start_point[0], end_point[0]),
                   min(start_point[1], end_point[1]),
                   max(start_point[0], end_point[0]),
                   max(start_point[1], end_point[1]))
            
            self.selected_text = page.get_text("text", clip=rect)
            
            # テキストブロックの位置情報を取得してハイライト表示
            self.highlight_text_blocks(start_point, end_point, image_x, image_y)
    
    def end_select(self, event):
        """選択終了"""
        # 選択したテキストをクリップボードにコピー
        if self.selected_text:
            self.clipboard_clear()
            self.clipboard_append(self.selected_text)
    
    def copy_selection(self, event):
        """Ctrl+Cでコピー"""
        if self.selected_text:
            self.clipboard_clear()
            self.clipboard_append(self.selected_text)
    
    def highlight_text_blocks(self, start_point, end_point, image_x, image_y):
        """選択範囲内のテキストブロックをハイライト表示"""
        if not self.doc or self.current_page is None:
            return
        
        try:
            page = self.doc[self.current_page]
            
            # テキストブロックの位置情報を取得
            text_dict = page.get_text("dict")
            
            # 選択範囲の矩形
            select_rect = (
                min(start_point[0], end_point[0]),
                min(start_point[1], end_point[1]),
                max(start_point[0], end_point[0]),
                max(start_point[1], end_point[1])
            )
            
            # 各テキストブロックをチェック
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        # テキストの位置情報
                        bbox = span.get("bbox", [])
                        if len(bbox) != 4:
                            continue
                        
                        # テキストブロックの矩形
                        text_rect = (bbox[0], bbox[1], bbox[2], bbox[3])
                        
                        # 選択範囲とテキストブロックが重なっているかチェック
                        if self.rects_intersect(select_rect, text_rect):
                            # キャンバス座標に変換
                            x1 = image_x + text_rect[0] * self.zoom
                            y1 = image_y + text_rect[1] * self.zoom
                            x2 = image_x + text_rect[2] * self.zoom
                            y2 = image_y + text_rect[3] * self.zoom
                            
                            # ハイライト矩形を描画（黄色の半透明）
                            highlight_id = self.canvas.create_rectangle(
                                x1, y1, x2, y2,
                                outline='', fill='yellow', stipple='gray50', width=0
                            )
                            self.text_highlights.append(highlight_id)
                            
        except Exception as e:
            # エラーが発生しても処理を続行
            print(f"テキストハイライトエラー: {str(e)}")
    
    def rects_intersect(self, rect1, rect2):
        """2つの矩形が交差しているかチェック"""
        x1_min, y1_min, x1_max, y1_max = rect1
        x2_min, y2_min, x2_max, y2_max = rect2
        
        return not (x1_max < x2_min or x2_max < x1_min or y1_max < y2_min or y2_max < y1_min)
    
    def start_pan(self, event):
        """手のひらツール開始（左クリック）"""
        # パン開始時に選択範囲をクリア
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
            self.selection_rect = None
        # テキストハイライトも削除
        for highlight_id in self.text_highlights:
            self.canvas.delete(highlight_id)
        self.text_highlights = []
        self.selected_text = ""
        self.start_x = None
        self.start_y = None
        
        self.pan_start_x = self.canvas.canvasx(event.x)
        self.pan_start_y = self.canvas.canvasy(event.y)
        self.pan_start_image_x = self.image_x
        self.pan_start_image_y = self.image_y
        # カーソルを手のひらアイコンに変更
        self.canvas.config(cursor="hand2")
    
    def update_pan(self, event):
        """手のひらツール更新（右クリックドラッグ中）"""
        if self.pan_start_x is None or self.pan_start_y is None:
            return
        
        # 現在のマウス位置を取得
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        
        # マウスの移動量を計算
        dx = cur_x - self.pan_start_x
        dy = cur_y - self.pan_start_y
        
        # 画像の新しい位置を計算
        self.image_x = self.pan_start_image_x + dx
        self.image_y = self.pan_start_image_y + dy
        
        # 画像の位置を更新
        if self.image_id:
            self.canvas.coords(self.image_id, self.image_x, self.image_y)
    
    def end_pan(self, event):
        """手のひらツール終了（右クリック離す）"""
        self.pan_start_x = None
        self.pan_start_y = None
        # カーソルを元に戻す
        self.canvas.config(cursor="")
    
    def show_page(self, page_num, search_term=None, fit_to_page=True, is_phrase_search=False, case_sensitive=False):
        if not self.doc:
            # PDFが読み込まれていない場合は初期表示を表示
            self.show_initial_main_view()
            return
        
        try:
            # ページ番号の確認
            if page_num < 0:
                page_num = 0
            if page_num >= len(self.doc):
                page_num = len(self.doc) - 1
                
            page = self.doc[page_num]
            self.current_page = page_num
            
            # 既存のハイライトを削除（拡大縮小時の重複を防ぐ）
            for annot in page.annots():
                page.delete_annot(annot)
            
            # ズャンバスのサイズを取得
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # ページのサイズを取得
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            if fit_to_page:  # 初期表示時のみページサイズに合わせる
                # 高さに合わせてズーム倍率を計算
                zoom_height = canvas_height / page_height
                zoom_width = canvas_width / page_width
                self.zoom = min(zoom_height, zoom_width) * 0.95  # 少し余白を持たせる
            
            # ズーム倍率を適用
            zoom_matrix = fitz.Matrix(self.zoom, self.zoom)
            
            # 検索語とフレーズ検索モードを保存
            self.search_term = search_term
            self.is_phrase_search = is_phrase_search
            
            # ペイライトの色を定義（RGB値）
            highlight_colors = [
                None,  # インデックス0: デフォルトの黄色
                (0.5, 1, 0.5),    # インデックス1: 薄い緑
                (0.5, 0.8, 1),    # インデックス2: 薄い青
                (1, 0.5, 1)       # インデックス3: 薄い紫
            ]
            
            # ページのテキストと位置情報を取得
            if search_term:
                # フレーズ検索モードの判定
                # 引数で渡されたis_phrase_searchを使用、なければsearch_termから判定
                if not is_phrase_search:
                    # ダブルクォーテーションで囲まれているかチェック
                    is_phrase_search = (search_term.startswith('"') and search_term.endswith('"'))
                    if is_phrase_search:
                        # クォートを除去
                        search_term = search_term.strip('"')
                
                # 検索語のリスト化
                if is_phrase_search:
                    # フレーズ検索：検索語をそのまま使用
                    search_terms = [search_term]
                else:
                    # AND検索：スペースで分割
                    search_terms = search_term.split()
                
                # マージのコピーを作成
                pix = page.get_pixmap(matrix=zoom_matrix)
                
                # 各検索語に対して異なる色でハイライト
                for i, term in enumerate(search_terms):
                    if case_sensitive:
                        # 大文字小文字を区別する場合は、search_forの結果をフィルタリング
                        # まず、大文字小文字を区別せずに検索（これにより「Sen-sor」のようなハイフンを含む単語も見つかる）
                        all_instances = page.search_for(term, quads=True)
                        instances = []
                        # ページ全体のテキストブロックを取得（大文字小文字を区別した判定のため）
                        blocks = page.get_text("dict")
                        # 各インスタンスの位置を確認して、大文字小文字を区別してフィルタリング
                        for quads in all_instances:
                            try:
                                rect = quads.rect
                                # 矩形を少し拡張して、その範囲内のテキストを取得（誤差を考慮）
                                expanded_rect = fitz.Rect(
                                    max(0, rect.x0 - 2),
                                    max(0, rect.y0 - 2),
                                    min(page.rect.width, rect.x1 + 2),
                                    min(page.rect.height, rect.y1 + 2)
                                )
                                # 拡張した矩形内のテキストを取得
                                try:
                                    text_in_rect = page.get_textbox(expanded_rect)
                                except:
                                    text_in_rect = ""
                                
                                # テキストが空の場合は、テキストブロックから取得
                                if not text_in_rect:
                                    # 矩形内のすべてのテキストスパンを集める（位置順にソート）
                                    span_list = []
                                    for block in blocks.get("blocks", []):
                                        if "lines" not in block:
                                            continue
                                        for line in block["lines"]:
                                            for span in line.get("spans", []):
                                                span_text = span.get("text", "")
                                                span_bbox = span.get("bbox", [])
                                                # 矩形がquadsの矩形と重なっているか確認
                                                if (len(span_bbox) == 4 and 
                                                    span_bbox[0] <= rect.x1 and span_bbox[2] >= rect.x0 and
                                                    span_bbox[1] <= rect.y1 and span_bbox[3] >= rect.y0):
                                                    span_list.append((span_bbox[1], span_bbox[0], span_text))  # y座標、x座標、テキスト
                                    # y座標、x座標の順でソートしてテキストを結合
                                    span_list.sort(key=lambda x: (x[0], x[1]))
                                    text_in_rect = "".join([s[2] for s in span_list])
                                
                                # 大文字小文字を区別して検索語が含まれているか確認
                                if term in text_in_rect:
                                    instances.append(quads)
                            except Exception as e:
                                # エラーが発生した場合はスキップ
                                logger.debug(f"テキスト取得エラー: {str(e)}")
                                continue
                    else:
                        # 大文字小文字を区別しない場合は、page.search_forを使用
                        instances = page.search_for(term, quads=True)
                    
                    if instances:
                        for quads in instances:
                            try:
                                # quadsの検証
                                if quads and hasattr(quads, 'rect'):
                                    rect = quads.rect
                                    # 矩形が有効か確認
                                    if (rect.width > 0 and rect.height > 0 and 
                                        not math.isnan(rect.x0) and not math.isnan(rect.y0) and
                                        not math.isnan(rect.x1) and not math.isnan(rect.y1) and
                                        not math.isinf(rect.x0) and not math.isinf(rect.y0) and
                                        not math.isinf(rect.x1) and not math.isinf(rect.y1)):
                                        annot = page.add_highlight_annot(quads)
                                        if i > 0:  # 2つ目以降の単語
                                            color_index = min(i, len(highlight_colors) - 1)
                                            if highlight_colors[color_index]:
                                                annot.set_colors(stroke=highlight_colors[color_index])
                                                annot.update()
                            except Exception as e:
                                # エラーが発生した場合はスキップ
                                logger.debug(f"ハイライト作成エラー: {str(e)}")
                                continue
                
                # ハイライト付きのページを表示
                pix = page.get_pixmap(matrix=zoom_matrix)
                
                # ハイライトを削除（次回の表示のため）
                for annot in page.annots():
                    page.delete_annot(annot)
            else:
                pix = page.get_pixmap(matrix=zoom_matrix)
            
            # PhotoImageに変換
            self.photoimg = ImageTk.PhotoImage(
                Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            )
            
            # キャンバスをクリアして新しい画像を表示
            self.canvas.delete("all")
            # 画像を中央に配置（初回表示時のみ、パン中は現在位置を維持）
            if fit_to_page or self.image_id is None:
                x = (canvas_width - pix.width) // 2
                x = max(0, x)  # 負の値にならないように
                self.image_x = x
                self.image_y = 0
            # 画像を作成（IDを保存）
            self.image_id = self.canvas.create_image(self.image_x, self.image_y, anchor=tk.NW, image=self.photoimg)
            
            # スクロール領域の設定
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            
            # 選択をクリア
            if self.selection_rect:
                self.canvas.delete(self.selection_rect)
            self.selection_rect = None
            # テキストハイライトもクリア
            for highlight_id in self.text_highlights:
                self.canvas.delete(highlight_id)
            self.text_highlights = []
            self.selected_text = ""
            self.start_x = None
            self.start_y = None
            
        except Exception as e:
            messagebox.showerror("エラー", f"ページの表示に失敗: {str(e)}")

    def clear_view(self):
        """ビューアをクリア"""
        self.canvas.delete("all")
        self.preview_canvas.delete("all")
        if hasattr(self, 'info_frame'):
            self.info_frame.destroy()  # 情報表示フレームを削除
        self.doc = None
        self.current_page = None
        self.search_term = None
        self.selected_text = ""
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        self.selection_rect = None
        # 画像IDと位置をリセット
        self.image_id = None
        self.image_x = 0
        self.image_y = 0
        self.pan_start_x = None
        self.pan_start_y = None

class ProgressDialog:
    def __init__(self, parent, title, maximum):
        # Toplevelはttkbootstrapで直接サポートされていないため、標準のtk.Toplevelを使用
        # テーマは自動的に適用されます
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.transient(parent)
        
        # ウィンドウサイズと位置
        width = 300
        height = 100
        x = parent.winfo_x() + parent.winfo_width()//2 - width//2
        y = parent.winfo_y() + parent.winfo_height()//2 - height//2
        self.top.geometry(f"{width}x{height}+{x}+{y}")
        
        # プログレスバー
        ProgressbarClass = ttkb.Progressbar if HAS_TTKB else ttk.Progressbar
        self.progress = ProgressbarClass(
            self.top, 
            mode='determinate',
            maximum=maximum,
            bootstyle="info-striped" if HAS_TTKB else None
        )
        self.progress.pack(padx=20, pady=10, fill=tk.X)
        
        # 状態表示ラベル
        LabelClass = ttkb.Label if HAS_TTKB else ttk.Label
        self.label = LabelClass(self.top, text="処理中...")
        self.label.pack(pady=5)
        
    def update(self, value, text=None):
        self.progress['value'] = value
        if text:
            self.label['text'] = text
        self.top.update()
        
    def close(self):
        self.top.destroy()

class PDFSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("黒鯱 – PDF横断検索ツール")
        self.root.geometry("1440x900")
        
        # アイコンの設定
        try:
            # アイコンファイルのパスを取得（EXE化時にも対応）
            icon_path = get_resource_path('kuroshachi_icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                logger.warning(f"アイコンファイルが見つかりません: {icon_path}")
        except Exception as e:
            logger.warning(f"アイコンの設定に失敗: {str(e)}")
        
        
        # MeCabの初期化
        try:
            import MeCab
            import site
            
            # 辞書パスの検出（EXE化時と通常実行時の両方に対応）
            dict_path = None
            
            # PyInstallerでEXE化された場合
            if getattr(sys, 'frozen', False):
                # EXEファイルのディレクトリ
                base_path = sys._MEIPASS
                # 辞書の候補パス
                candidate_paths = [
                    os.path.join(base_path, 'ipadic', 'dicdir'),
                    os.path.join(base_path, 'dicdir'),
                ]
                for path in candidate_paths:
                    if os.path.exists(path):
                        dict_path = path
                        break
            else:
                # 通常のPython実行時
                # site-packagesからipadicを探す
                for site_packages in site.getsitepackages():
                    candidate = os.path.join(site_packages, 'ipadic', 'dicdir')
                    if os.path.exists(candidate):
                        dict_path = candidate
                        break
                
                # 見つからない場合はハードコードされたパスを試す
                if not dict_path:
                    hardcoded_path = r"C:/Users/suehiro/AppData/Local/Programs/Python/Python311/Lib/site-packages/ipadic/dicdir"
                    if os.path.exists(hardcoded_path):
                        dict_path = hardcoded_path
            
            if dict_path:
                self.mecab = MeCab.Tagger(f'-d "{dict_path}"')
                # 初期化テスト
                self.mecab.parseToNode("")
            else:
                # 辞書が見つからない場合はデフォルトで初期化を試みる
                self.mecab = MeCab.Tagger()
                self.mecab.parseToNode("")
            
        except Exception as e:
            print(f"MeCab初期化エラー: {str(e)}")
            self.mecab = None
            
        # 初期化テスト用の空文字列解析
        if self.mecab:
            self.mecab.parse("")  # この行はエンコーディングの初期化のために必要
        
        # データベースのパスを設定
        self.db_path = "pdf_index.db"
        
        # ここでDBの初期化を呼び出し
        self.init_database()
        self.ensure_saved_results_tables()  # 保存された検索結果用のテーブルを確認
        
        # データベーススキーマの更新
        self.update_database_schema()
        
        # データベース接続とテーブル作成を確実に行う
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # pdf_filesテール
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pdf_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filepath TEXT UNIQUE,
                        filename TEXT,
                        file_hash TEXT,
                        last_modified DATETIME
                    )
                """)
                
                # FTSテーブルの作成
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS pdf_contents_fts USING fts5(
                        content,
                        pdf_id,
                        page
                    )
                """)
                
                # メタデータテーブル
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pdf_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pdf_id INTEGER,
                        title TEXT,
                        author TEXT,
                        creation_date TEXT,
                        modification_date TEXT,
                        producer TEXT,
                        page_count INTEGER,
                        FOREIGN KEY (pdf_id) REFERENCES pdf_files (id)
                    )
                """)
                
                conn.commit()
                
        except sqlite3.Error as e:
            messagebox.showerror("エラー", f"データベースの初期化に失敗: {str(e)}")
            print(f"DB Initialization Error: {str(e)}")
        
        # メインの分割ペイン
        if HAS_TTKB:
            self.main_paned = ttkb.Panedwindow(root, orient=tk.HORIZONTAL)
        else:
            self.main_paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)
        
        # 左側フレーム（コントロール用）- 約14%
        if HAS_TTKB:
            self.left_frame = ttkb.Frame(self.main_paned)
        else:
            self.left_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.left_frame, weight=1)  # weight=1 で約14%
        
        # 右側のフレーム（PDFビューア用）- 約86%
        if HAS_TTKB:
            self.right_frame = ttkb.Frame(self.main_paned)
        else:
            self.right_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.right_frame, weight=6)  # weight=6 で約86%
        
        # 折りたたみボタン用のフレーム（右側フレームの左端に配置）
        if HAS_TTKB:
            self.toggle_button_frame = ttkb.Frame(self.right_frame)
        else:
            self.toggle_button_frame = ttk.Frame(self.right_frame)
        self.toggle_button_frame.pack(side=tk.LEFT, fill=tk.Y, padx=0, pady=0)
        
        # 折りたたみボタン
        self.left_panel_collapsed = False
        self.left_panel_sashpos = None  # 折りたたみ前のsash位置を保存
        if HAS_TTKB:
            self.toggle_button = ttkb.Button(self.toggle_button_frame, text="✕", width=2, 
                                             command=self.toggle_left_panel,
                                             bootstyle="secondary")
        else:
            self.toggle_button = ttk.Button(self.toggle_button_frame, text="✕", width=2,
                                           command=self.toggle_left_panel)
        self.toggle_button.pack(side=tk.TOP, padx=2, pady=5)
        
        # コントロールの作成
        self.create_controls(self.left_frame)
        
        # PDFビューアフレーム（折りたたみボタンの右側に配置）
        pdf_viewer_frame = ttk.Frame(self.right_frame) if not HAS_TTKB else ttkb.Frame(self.right_frame)
        pdf_viewer_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.pdf_viewer = PDFViewerFrame(pdf_viewer_frame)
        self.pdf_viewer.pack(fill=tk.BOTH, expand=True)
        
        # プレビューエリアのナビゲーションコールバックを設定
        self.pdf_viewer.navigate_result_callback = self.navigate_search_result
        # ヘルプボタンのコールバックを設定
        self.pdf_viewer.show_guide_callback = self.show_guide
        self.pdf_viewer.show_about_callback = self.show_about
        self.pdf_viewer.show_operation_guide_callback = self.show_operation_guide
        # ヘルプボタンのコールバックを設定
        self.pdf_viewer.show_guide_callback = self.show_guide
        self.pdf_viewer.show_about_callback = self.show_about
        
        # データベースが存在する場合のみ、既存のファイルを読み込む
        if os.path.exists(self.db_path):
            self.load_existing_files()
    
    def toggle_left_panel(self):
        """左側パネルの折りたたみ/展開を切り替え"""
        if self.left_panel_collapsed:
            # 展開時：insertを使って左側に追加（weight=1で初期化時と同じ比率を維持）
            self.main_paned.insert(0, self.left_frame, weight=1)
            # 保存されたsash位置があれば復元
            if self.left_panel_sashpos is not None:
                try:
                    self.main_paned.sashpos(0, self.left_panel_sashpos)
                except:
                    pass  # sashposが設定できない場合は無視
            self.toggle_button.config(text="✕")  # パネルが開いている時は閉じるボタン
            self.left_panel_collapsed = False
        else:
            # 折りたたみ：現在のsash位置を保存
            try:
                # 左側フレームが最初のペインなので、sashpos(0)で位置を取得
                self.left_panel_sashpos = self.main_paned.sashpos(0)
            except:
                self.left_panel_sashpos = None
            self.main_paned.forget(self.left_frame)
            self.toggle_button.config(text="☰")  # パネルが閉じている時は開くボタン（ハンバーガーメニュー）
            self.left_panel_collapsed = True

    
    def show_guide(self):
        """使い方ガイドを表示（Markdownファイル）"""
        logger.info("使い方ガイドを表示開始")
        
        try:
            # Markdownファイルのパスを取得
            guide_path = None
            
            if getattr(sys, 'frozen', False):
                # PyInstallerでEXE化された場合
                logger.info("EXEモードで実行中")
                try:
                    meipass_path = sys._MEIPASS
                    logger.info(f"_MEIPASS: {meipass_path}")
                    guide_path = os.path.join(meipass_path, "guide.md")
                    logger.info(f"ガイドパス（_MEIPASS）: {guide_path}, 存在: {os.path.exists(guide_path)}")
                    
                    if not os.path.exists(guide_path):
                        # _MEIPASSにない場合は、EXEファイルと同じディレクトリを確認
                        exe_dir = os.path.dirname(sys.executable)
                        guide_path = os.path.join(exe_dir, "guide.md")
                        logger.info(f"ガイドパス（EXEディレクトリ）: {guide_path}, 存在: {os.path.exists(guide_path)}")
                        
                        if not os.path.exists(guide_path):
                            # さらに、_MEIPASS内のサブディレクトリも確認
                            logger.info("_MEIPASS内を再帰的に検索中...")
                            for root, dirs, files in os.walk(meipass_path):
                                if 'guide.md' in files:
                                    guide_path = os.path.join(root, 'guide.md')
                                    logger.info(f"ガイドファイルを発見: {guide_path}")
                                    break
                except AttributeError as e:
                    logger.error(f"_MEIPASSエラー: {str(e)}")
                    exe_dir = os.path.dirname(sys.executable)
                    guide_path = os.path.join(exe_dir, "guide.md")
            else:
                # 通常のPython実行時
                logger.info("通常モードで実行中")
                script_dir = os.path.dirname(os.path.abspath(__file__))
                guide_path = os.path.join(script_dir, "guide.md")
                logger.info(f"ガイドパス: {guide_path}, 存在: {os.path.exists(guide_path)}")
            
            # Markdownファイルを読み込む
            markdown_content = None
            try:
                if not guide_path or not os.path.exists(guide_path):
                    raise FileNotFoundError(f"ガイドファイルが見つかりません: {guide_path}")
                
                logger.info(f"ガイドファイルを読み込み中: {guide_path}")
                with open(guide_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                logger.info(f"ガイドファイル読み込み成功（{len(markdown_content)}文字）")
            except FileNotFoundError as e:
                logger.error(f"ガイドファイルが見つかりません: {str(e)}")
                messagebox.showerror("エラー", f"ガイドファイルが見つかりません。\n\n{str(e)}")
                return
            except Exception as e:
                logger.error(f"ガイドファイル読み込みエラー: {str(e)}", exc_info=True)
                messagebox.showerror("エラー", f"ガイドファイルの読み込みに失敗しました。\n\nエラー: {str(e)}")
                return
            
            # tkinterのTextウィジェットでMarkdownを直接表示（スタイル適用が確実）
            logger.info("Textウィジェットでガイドを表示します...")
            try:
                # 背景色を先に定義
                bg_color = '#2b2b2b' if HAS_TTKB else 'white'
                
                # ttkbootstrapスタイルのウィンドウを作成（ダークモード対応）
                if HAS_TTKB:
                    guide_window = ttkb.Window(title="使い方ガイド", themename="darkly")
                    # ttkb.Windowは独立したウィンドウなので、transientは設定しない
                else:
                    guide_window = tk.Toplevel(self.root)
                    guide_window.title("使い方ガイド")
                    guide_window.transient(self.root)  # Toplevelの場合のみtransientを設定
                    guide_window.configure(bg=bg_color)  # ウィンドウの背景色を設定
                guide_window.geometry("1000x800")
                
                # メインフレーム（背景色を設定）
                main_frame = tk.Frame(guide_window, bg=bg_color)
                main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                # テキストエリア用のフレーム（左マージン用）
                bg_color = '#2b2b2b' if HAS_TTKB else 'white'
                text_frame = tk.Frame(main_frame, bg=bg_color)  # 背景色を設定
                text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(50, 0))  # 左マージンを大きく
                
                # スクロールバー
                scrollbar = ttk.Scrollbar(main_frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                # Textウィジェット（ダークモード対応）
                bg_color = '#2b2b2b' if HAS_TTKB else 'white'
                fg_color = '#e0e0e0' if HAS_TTKB else 'black'
                text_widget = tk.Text(
                    text_frame,
                    wrap=tk.WORD,
                    yscrollcommand=scrollbar.set,
                    font=('Yu Gothic UI', 11),
                    bg=bg_color,
                    fg=fg_color,
                    padx=20,  # 左右のパディング
                    pady=15,
                    insertbackground=fg_color,
                    selectbackground='#4a9eff',
                    selectforeground='white'
                )
                text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.config(command=text_widget.yview)
                
                # スタイルタグの定義（カラフルに）
                text_widget.tag_configure("h1", foreground="#4a9eff", font=('Yu Gothic UI', 18, 'bold'), spacing1=10, spacing3=5)
                text_widget.tag_configure("h2", foreground="#6bb3ff", font=('Yu Gothic UI', 16, 'bold'), spacing1=8, spacing3=4)
                text_widget.tag_configure("h3", foreground="#8cc8ff", font=('Yu Gothic UI', 14, 'bold'), spacing1=6, spacing3=3)
                text_widget.tag_configure("h4", foreground="#a8d5ff", font=('Yu Gothic UI', 12, 'bold'), spacing1=5, spacing3=2)
                text_widget.tag_configure("strong", foreground="#ffd700", font=('Yu Gothic UI', 11, 'bold'))  # 金色
                text_widget.tag_configure("em", foreground="#ffa500", font=('Yu Gothic UI', 11, 'italic'))  # オレンジ
                text_widget.tag_configure("code", foreground="#f8f8f2", background="#3a3a3a", font=('Consolas', 10))
                text_widget.tag_configure("hr", foreground="#666666", font=('Yu Gothic UI', 1))
                text_widget.tag_configure("list", foreground="#b0e0ff")  # リスト項目用の色
                # ハイライト色用のタグ
                text_widget.tag_configure("highlight_yellow", foreground="#ffd700")  # 黄色
                text_widget.tag_configure("highlight_green", foreground="#90ee90")  # 緑
                text_widget.tag_configure("highlight_blue", foreground="#87ceeb")  # 青
                text_widget.tag_configure("highlight_purple", foreground="#da70d6")  # 紫
                
                # MarkdownをパースしてTextウィジェットに挿入
                import re
                
                def insert_formatted_text(text_widget, text, tags=None):
                    """テキストをフォーマットして挿入（強調、コードなどを処理）"""
                    if tags is None:
                        tags = []
                    
                    # **強調**と`コード`を処理
                    parts = re.split(r'(\*\*[^*]+\*\*|`[^`]+`)', text)
                    for part in parts:
                        if part.startswith('**') and part.endswith('**'):
                            # 強調
                            content = part[2:-2]
                            text_widget.insert(tk.END, content, tags + ["strong"])
                        elif part.startswith('`') and part.endswith('`'):
                            # コード
                            content = part[1:-1]
                            text_widget.insert(tk.END, content, tags + ["code"])
                        elif part:
                            # 通常テキスト
                            text_widget.insert(tk.END, part, tags)
                
                lines = markdown_content.split('\n')
                in_list = False
                in_highlight_section = False  # ハイライト色のセクションかどうか
                
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    
                    # 見出し
                    if stripped.startswith('# '):
                        if in_list:
                            in_list = False
                            text_widget.insert(tk.END, '\n')
                        in_highlight_section = False
                        heading_text = stripped[2:].strip()
                        insert_formatted_text(text_widget, heading_text, ["h1"])
                        text_widget.insert(tk.END, '\n')
                    elif stripped.startswith('## '):
                        if in_list:
                            in_list = False
                            text_widget.insert(tk.END, '\n')
                        in_highlight_section = False
                        heading_text = stripped[3:].strip()
                        insert_formatted_text(text_widget, heading_text, ["h2"])
                        text_widget.insert(tk.END, '\n')
                    elif stripped.startswith('### '):
                        if in_list:
                            in_list = False
                            text_widget.insert(tk.END, '\n')
                        in_highlight_section = False
                        heading_text = stripped[4:].strip()
                        insert_formatted_text(text_widget, heading_text, ["h3"])
                        text_widget.insert(tk.END, '\n')
                    elif stripped.startswith('#### '):
                        if in_list:
                            in_list = False
                            text_widget.insert(tk.END, '\n')
                        # 「ハイライトの色の意味」セクションかどうかをチェック
                        heading_text = stripped[5:].strip()
                        if 'ハイライト' in heading_text and '色' in heading_text:
                            in_highlight_section = True
                        else:
                            in_highlight_section = False
                        insert_formatted_text(text_widget, heading_text, ["h4"])
                        text_widget.insert(tk.END, '\n')
                    # 水平線
                    elif stripped == '---':
                        if in_list:
                            in_list = False
                            text_widget.insert(tk.END, '\n')
                        in_highlight_section = False
                        text_widget.insert(tk.END, '─' * 50 + '\n', "hr")
                    # リスト（- または *）
                    elif stripped.startswith('- ') or stripped.startswith('* '):
                        if not in_list:
                            in_list = True
                        list_content = stripped[2:]
                        
                        # ハイライト色のセクションの場合、色を適用
                        if in_highlight_section:
                            # 絵文字を検出して色を適用
                            if '🟨' in list_content or '黄色' in list_content:
                                text_widget.insert(tk.END, '  ■ ', ["highlight_yellow"])
                                # 絵文字を削除して色付きテキストに置き換え
                                list_content = re.sub(r'🟨\s*', '', list_content)
                                insert_formatted_text(text_widget, list_content, ["highlight_yellow"])
                            elif '🟩' in list_content or '緑' in list_content:
                                text_widget.insert(tk.END, '  ■ ', ["highlight_green"])
                                list_content = re.sub(r'🟩\s*', '', list_content)
                                insert_formatted_text(text_widget, list_content, ["highlight_green"])
                            elif '🟦' in list_content or '青' in list_content:
                                text_widget.insert(tk.END, '  ■ ', ["highlight_blue"])
                                list_content = re.sub(r'🟦\s*', '', list_content)
                                insert_formatted_text(text_widget, list_content, ["highlight_blue"])
                            elif '🟪' in list_content or '紫' in list_content:
                                text_widget.insert(tk.END, '  ■ ', ["highlight_purple"])
                                list_content = re.sub(r'🟪\s*', '', list_content)
                                insert_formatted_text(text_widget, list_content, ["highlight_purple"])
                            else:
                                text_widget.insert(tk.END, '  • ', ["list"])
                                insert_formatted_text(text_widget, list_content, ["list"])
                        else:
                            text_widget.insert(tk.END, '  • ', ["list"])
                            insert_formatted_text(text_widget, list_content, ["list"])
                        text_widget.insert(tk.END, '\n')
                    # 番号付きリスト
                    elif re.match(r'^\d+\.\s', stripped):
                        if not in_list:
                            in_list = True
                        list_content = re.sub(r'^\d+\.\s', '', stripped)
                        text_widget.insert(tk.END, '  ', ["list"])
                        insert_formatted_text(text_widget, stripped, ["list"])
                        text_widget.insert(tk.END, '\n')
                    # 空行
                    elif not stripped:
                        if in_list:
                            in_list = False
                            text_widget.insert(tk.END, '\n')
                        else:
                            text_widget.insert(tk.END, '\n')
                    # 通常の段落
                    else:
                        if in_list:
                            in_list = False
                            text_widget.insert(tk.END, '\n')
                        insert_formatted_text(text_widget, stripped)
                        text_widget.insert(tk.END, '\n')
                
                text_widget.configure(state="disabled")  # 読み取り専用
                
                # ボタンフレーム（ブラウザで見るボタンと閉じるボタン）
                if HAS_TTKB:
                    button_frame = ttkb.Frame(guide_window)
                    browser_button = ttkb.Button(button_frame, text="ブラウザで見る", 
                                                 command=lambda: self.show_guide_in_browser(),
                                                 bootstyle="secondary")
                    close_button = ttkb.Button(button_frame, text="閉じる", command=guide_window.destroy,
                                               bootstyle="primary")
                else:
                    button_frame = ttk.Frame(guide_window)
                    browser_button = ttk.Button(button_frame, text="ブラウザで見る",
                                               command=lambda: self.show_guide_in_browser())
                    close_button = ttk.Button(button_frame, text="閉じる", command=guide_window.destroy)
                button_frame.pack(fill=tk.X, padx=10, pady=10)
                browser_button.pack(side=tk.LEFT, padx=(0, 10))
                close_button.pack(side=tk.RIGHT)
                
                logger.info("ガイド表示成功")
                return
                
            except Exception as e:
                logger.error(f"Textウィジェット表示エラー: {str(e)}", exc_info=True)
                # エラーが発生した場合のみ外部ブラウザで開く（フォールバック）
                try:
                    import markdown
                    html_content = markdown.markdown(markdown_content, extensions=['extra', 'codehilite'])
                    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Yu Gothic UI', 'Meiryo', sans-serif; background-color: #2b2b2b; color: #e0e0e0; padding: 20px; }}
        h1, h2, h3 {{ color: #ffffff; }}
        code {{ background-color: #3a3a3a; color: #f8f8f2; padding: 2px 6px; }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""
                    import tempfile
                    temp_html = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
                    temp_html.write(html_content)
                    temp_html.close()
                    webbrowser.open(f"file:///{temp_html.name.replace(os.sep, '/')}")
                    messagebox.showwarning("警告", f"内部表示に失敗したため、外部ブラウザで開きました。\n\nエラー: {str(e)}")
                except Exception as browser_error:
                    logger.error(f"ブラウザ起動エラー: {str(browser_error)}", exc_info=True)
                    messagebox.showerror("エラー", f"ガイドの表示に失敗しました。\n\n{str(e)}")
            
        except Exception as e:
            logger.critical(f"show_guideで予期しないエラー: {str(e)}", exc_info=True)
            try:
                messagebox.showerror("エラー", f"ガイドの表示中にエラーが発生しました。\n\n{str(e)}\n\nログファイルを確認してください: {log_file}")
            except:
                print(f"致命的なエラー: {str(e)}")
                traceback.print_exc()
    
    def show_about(self):
        """バージョン情報ダイアログを表示"""
        about_text = f"""{APP_NAME}

バージョン: {APP_VERSION}

PDFファイルの全文検索ツール

機能:
• 複数PDFファイルの横断検索
• フレーズ検索対応
• 検索結果のハイライト表示
• PDFプレビュー機能

© 2026"""
        
        centered_messagebox(self.root, "info", "バージョン情報", about_text)
    
    def show_operation_guide(self):
        """操作説明ダイアログを表示"""
        operation_text = """マウス操作

• マウスホイール
  拡大・縮小

• Ctrl + ホイール
  検索結果の前後を移動
  （上にスクロールで前へ、下にスクロールで次へ）

• 左クリックドラッグ
  手のひらツール（パン）でページを移動

• 右クリックドラッグ
  テキスト選択（黄色でハイライト表示）"""
        
        centered_messagebox(self.root, "info", "操作説明", operation_text)
    
    def show_guide_in_browser(self):
        """使い方ガイドをブラウザで表示"""
        logger.info("使い方ガイドをブラウザで表示開始")
        
        try:
            # Markdownファイルのパスを取得
            guide_path = None
            
            if getattr(sys, 'frozen', False):
                # PyInstallerでEXE化された場合
                logger.info("EXEモードで実行中")
                try:
                    meipass_path = sys._MEIPASS
                    logger.info(f"_MEIPASS: {meipass_path}")
                    guide_path = os.path.join(meipass_path, "guide.md")
                    logger.info(f"ガイドパス（_MEIPASS）: {guide_path}, 存在: {os.path.exists(guide_path)}")
                    
                    if not os.path.exists(guide_path):
                        # _MEIPASSにない場合は、EXEファイルと同じディレクトリを確認
                        exe_dir = os.path.dirname(sys.executable)
                        guide_path = os.path.join(exe_dir, "guide.md")
                        logger.info(f"ガイドパス（EXEディレクトリ）: {guide_path}, 存在: {os.path.exists(guide_path)}")
                        
                        if not os.path.exists(guide_path):
                            # さらに、_MEIPASS内のサブディレクトリも確認
                            logger.info("_MEIPASS内を再帰的に検索中...")
                            for root, dirs, files in os.walk(meipass_path):
                                if 'guide.md' in files:
                                    guide_path = os.path.join(root, 'guide.md')
                                    logger.info(f"ガイドファイルを発見: {guide_path}")
                                    break
                except AttributeError as e:
                    logger.error(f"_MEIPASSエラー: {str(e)}")
                    exe_dir = os.path.dirname(sys.executable)
                    guide_path = os.path.join(exe_dir, "guide.md")
            else:
                # 通常のPython実行時
                logger.info("通常モードで実行中")
                script_dir = os.path.dirname(os.path.abspath(__file__))
                guide_path = os.path.join(script_dir, "guide.md")
                logger.info(f"ガイドパス: {guide_path}, 存在: {os.path.exists(guide_path)}")
            
            # Markdownファイルを読み込む
            markdown_content = None
            try:
                if not guide_path or not os.path.exists(guide_path):
                    raise FileNotFoundError(f"ガイドファイルが見つかりません: {guide_path}")
                
                logger.info(f"ガイドファイルを読み込み中: {guide_path}")
                with open(guide_path, 'r', encoding='utf-8') as f:
                    markdown_content = f.read()
                logger.info(f"ガイドファイル読み込み成功（{len(markdown_content)}文字）")
            except FileNotFoundError as e:
                logger.error(f"ガイドファイルが見つかりません: {str(e)}")
                messagebox.showerror("エラー", f"ガイドファイルが見つかりません。\n\n{str(e)}")
                return
            except Exception as e:
                logger.error(f"ガイドファイル読み込みエラー: {str(e)}", exc_info=True)
                messagebox.showerror("エラー", f"ガイドファイルの読み込みに失敗しました。\n\nエラー: {str(e)}")
                return
            
            # MarkdownをHTMLに変換してブラウザで開く
            try:
                import markdown
                html_content = markdown.markdown(markdown_content, extensions=['extra', 'codehilite'])
                html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>黒鯱 - 使い方ガイド</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Yu Gothic UI', 'Meiryo', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #e0e0e0;
            line-height: 1.8;
            padding: 0;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 30px;
            background: rgba(27, 27, 43, 0.95);
            box-shadow: 0 0 50px rgba(0, 0, 0, 0.5);
            border-radius: 10px;
            margin-top: 20px;
            margin-bottom: 20px;
        }}
        
        h1 {{
            color: #ffffff;
            font-size: 2.5em;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid transparent;
            border-image: linear-gradient(90deg, #4a9eff, #6bb3ff, #4a9eff) 1;
            background: linear-gradient(135deg, rgba(74, 158, 255, 0.1) 0%, rgba(107, 179, 255, 0.1) 100%);
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(74, 158, 255, 0.2);
        }}
        
        h2 {{
            color: #ffffff;
            font-size: 1.8em;
            margin-top: 40px;
            margin-bottom: 20px;
            padding: 15px 20px;
            background: linear-gradient(90deg, rgba(74, 158, 255, 0.15) 0%, transparent 100%);
            border-left: 4px solid #4a9eff;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(74, 158, 255, 0.1);
        }}
        
        h3 {{
            color: #b8d4ff;
            font-size: 1.4em;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-left: 15px;
            border-left: 3px solid #6bb3ff;
        }}
        
        h4 {{
            color: #d0e4ff;
            font-size: 1.2em;
            margin-top: 25px;
            margin-bottom: 12px;
        }}
        
        p {{
            margin-bottom: 16px;
            text-align: justify;
        }}
        
        code {{
            background: linear-gradient(135deg, #2a2a3e 0%, #1e1e2e 100%);
            color: #f8f8f2;
            padding: 3px 8px;
            border-radius: 4px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
            border: 1px solid rgba(74, 158, 255, 0.3);
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
        }}
        
        pre {{
            background: linear-gradient(135deg, #1a1a2e 0%, #0f1419 100%);
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            border: 1px solid rgba(74, 158, 255, 0.2);
            box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.5), 0 4px 15px rgba(0, 0, 0, 0.3);
            margin: 20px 0;
        }}
        
        pre code {{
            background: transparent;
            padding: 0;
            border: none;
            box-shadow: none;
            color: #f8f8f2;
        }}
        
        a {{
            color: #6bb3ff;
            text-decoration: none;
            transition: all 0.3s ease;
            border-bottom: 1px solid transparent;
        }}
        
        a:hover {{
            color: #4a9eff;
            border-bottom: 1px solid #4a9eff;
            text-shadow: 0 0 8px rgba(74, 158, 255, 0.5);
        }}
        
        ul, ol {{
            padding-left: 30px;
            margin: 20px 0;
        }}
        
        li {{
            margin: 12px 0;
            padding-left: 10px;
            position: relative;
        }}
        
        ul li::marker {{
            color: #6bb3ff;
        }}
        
        ul li {{
            list-style-type: none;
        }}
        
        ul li::before {{
            content: "▸";
            color: #4a9eff;
            font-weight: bold;
            position: absolute;
            left: -20px;
            text-shadow: 0 0 5px rgba(74, 158, 255, 0.5);
        }}
        
        ol li {{
            counter-increment: item;
        }}
        
        ol {{
            counter-reset: item;
        }}
        
        ol li::marker {{
            color: #6bb3ff;
            font-weight: bold;
        }}
        
        blockquote {{
            border-left: 4px solid #4a9eff;
            padding: 15px 20px;
            margin: 20px 0;
            background: rgba(74, 158, 255, 0.1);
            border-radius: 5px;
            font-style: italic;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
        }}
        
        hr {{
            border: none;
            height: 2px;
            background: linear-gradient(90deg, transparent, #4a9eff, transparent);
            margin: 40px 0;
            box-shadow: 0 0 10px rgba(74, 158, 255, 0.3);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            overflow: hidden;
        }}
        
        th {{
            background: linear-gradient(135deg, #4a9eff 0%, #6bb3ff 100%);
            color: #ffffff;
            padding: 15px;
            text-align: left;
            font-weight: bold;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid rgba(74, 158, 255, 0.2);
            background: rgba(27, 27, 43, 0.5);
        }}
        
        tr:hover td {{
            background: rgba(74, 158, 255, 0.1);
        }}
        
        strong {{
            color: #ffffff;
            font-weight: 600;
        }}
        
        em {{
            color: #b8d4ff;
            font-style: italic;
        }}
        
        ::-webkit-scrollbar {{
            width: 12px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: #1a1a2e;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: linear-gradient(135deg, #4a9eff 0%, #6bb3ff 100%);
            border-radius: 6px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: linear-gradient(135deg, #6bb3ff 0%, #4a9eff 100%);
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 20px 15px;
                margin: 10px;
            }}
            
            h1 {{
                font-size: 2em;
            }}
            
            h2 {{
                font-size: 1.5em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
{html_content}
    </div>
</body>
</html>"""
                import tempfile
                temp_html = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
                temp_html.write(html_content)
                temp_html.close()
                webbrowser.open(f"file:///{temp_html.name.replace(os.sep, '/')}")
                logger.info("ブラウザでガイドを表示しました")
            except ImportError:
                logger.error("markdownライブラリがインストールされていません")
                messagebox.showerror("エラー", "markdownライブラリが必要です。\n\npip install markdown でインストールしてください。")
            except Exception as e:
                logger.error(f"ブラウザ表示エラー: {str(e)}", exc_info=True)
                messagebox.showerror("エラー", f"ブラウザでの表示に失敗しました。\n\n{str(e)}")
            
        except Exception as e:
            logger.critical(f"show_guide_in_browserで予期しないエラー: {str(e)}", exc_info=True)
            try:
                messagebox.showerror("エラー", f"ガイドの表示中にエラーが発生しました。\n\n{str(e)}\n\nログファイルを確認してください: {log_file}")
            except:
                print(f"致命的なエラー: {str(e)}")
                traceback.print_exc()

    def load_existing_files(self):
        """既存のPDFファイルをツリービューに読み込む"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT filepath FROM pdf_files")
                files = cursor.fetchall()
                
                for file in files:
                    filepath = file[0]
                    filename = os.path.basename(filepath)
                    self.file_tree.insert("", "end", text=filename, values=(filepath,))
        except sqlite3.Error as e:
            print(f"既存ファイルの読み込みエラー: {str(e)}")

    def create_controls(self, parent):
        """左側のコントロールを作成"""
        # 1. PDFを追加ボタンと登録クリアボタン
        if HAS_TTKB:
            add_button_frame = ttkb.Frame(parent)
            ttkb.Button(add_button_frame, text="PDFを追加", command=self.add_file,
                       bootstyle="success").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 2), pady=5)
            ttkb.Button(add_button_frame, text="登録クリア", command=self.clear_all_files,
                       bootstyle="danger").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 5), pady=5)
        else:
            add_button_frame = ttk.Frame(parent)
            ttk.Button(add_button_frame, text="PDFを追加", command=self.add_file).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 2), pady=5)
            ttk.Button(add_button_frame, text="登録クリア", command=self.clear_all_files).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 5), pady=5)
        add_button_frame.pack(fill=tk.X)
        
        # 2. 追加済みPDFの一覧（高さ固定）
        if HAS_TTKB:
            file_frame = ttkb.Labelframe(parent, text="追加済みPDF", height=200, bootstyle="primary")
        else:
            file_frame = ttk.LabelFrame(parent, text="追加済みPDF", height=200)
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        file_frame.pack_propagate(False)
        
        # スクロールバー用のフレームを作成
        tree_frame = ttk.Frame(file_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeviewはttkbootstrapで直接サポートされていないため、標準のttk.Treeviewを使用
        self.file_tree = ttk.Treeview(
            tree_frame, 
            columns=("path",),
            show="tree headings"
        )
        self.file_tree.heading("#0", text="ファイル名")
        
        # 縦スクロールバー
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=v_scrollbar.set)
        
        # 横スクロールバー
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.file_tree.xview)
        self.file_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # 配置
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # グリッドの重み設定
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # 右クリックメニューの作成
        self.popup_menu = tk.Menu(self.file_tree, tearoff=0)
        self.popup_menu.add_command(label="フォルダを開く", command=self.open_file_folder)
        self.popup_menu.add_separator()
        self.popup_menu.add_command(label="削除", command=self.delete_file)
        
        # 右クリックイベントのバインド
        self.file_tree.bind("<Button-3>", self.show_popup_menu)
        # ダブルクリックでPDFをプレビュー表示
        self.file_tree.bind("<Double-Button-1>", self.on_file_double_click)
        
        # 3. 検索窓と検索ボタン
        if HAS_TTKB:
            search_frame = ttkb.Frame(parent)
        else:
            search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.search_var = tk.StringVar()
        if HAS_TTKB:
            search_entry = ttkb.Entry(
                search_frame, 
                textvariable=self.search_var,
                font=('Yu Gothic UI', 12),
                bootstyle="primary"
            )
        else:
            search_entry = ttk.Entry(
                search_frame, 
                textvariable=self.search_var,
                font=('Yu Gothic UI', 12),
                style='Large.TEntry'
            )
            # カスタムスタイルの定義
            style = ttk.Style()
            style.configure('Large.TEntry', padding=(5, 8))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        if HAS_TTKB:
            ttkb.Button(search_frame, text="検索", command=self.search_pdfs,
                       bootstyle="primary").pack(side=tk.LEFT)
        else:
            ttk.Button(search_frame, text="検索", command=self.search_pdfs).pack(side=tk.LEFT)
        
        # 4. フレーズ検索ON/OFFと大文字小文字を区別
        # 検索オプションの変数を初期化
        self.phrase_search_var = tk.BooleanVar()
        self.case_sensitive_var = tk.BooleanVar(value=False)  # 大文字小文字を区別
        self.whole_word_var = tk.BooleanVar(value=False)  # 単語全体で検索
        self.regex_search_var = tk.BooleanVar(value=False)  # 正規表現検索
        
        if HAS_TTKB:
            options_frame = ttkb.Frame(parent)
        else:
            options_frame = ttk.Frame(parent)
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # フレーズ検索用チェックボックス
        if HAS_TTKB:
            ttkb.Checkbutton(options_frame, text="フレーズ検索", variable=self.phrase_search_var,
                           bootstyle="primary-round-toggle").pack(side=tk.LEFT, padx=(0, 5))
        else:
            ttk.Checkbutton(options_frame, text="フレーズ検索", variable=self.phrase_search_var).pack(side=tk.LEFT, padx=(0, 5))
        
        # 大文字小文字を区別するチェックボックス
        if HAS_TTKB:
            ttkb.Checkbutton(options_frame, text="大文字小文字を区別", variable=self.case_sensitive_var,
                           bootstyle="primary-round-toggle").pack(side=tk.LEFT, padx=(0, 5))
        else:
            ttk.Checkbutton(options_frame, text="大文字小文字を区別", variable=self.case_sensitive_var).pack(side=tk.LEFT, padx=(0, 5))
        
        # 5. 検索結果クリアボタン、検索結果保存ボタン、保存リストボタン
        if HAS_TTKB:
            result_buttons_frame = ttkb.Frame(parent)
            ttkb.Button(result_buttons_frame, text="検索結果クリア", command=self.clear_search_results,
                       bootstyle="secondary").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 2), pady=5)
            ttkb.Button(result_buttons_frame, text="検索結果保存", command=self.save_search_results,
                       bootstyle="info").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=5)
            ttkb.Button(result_buttons_frame, text="保存リスト", command=self.show_saved_results,
                       bootstyle="info").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 5), pady=5)
        else:
            result_buttons_frame = ttk.Frame(parent)
            ttk.Button(result_buttons_frame, text="検索結果クリア", command=self.clear_search_results).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 2), pady=5)
            ttk.Button(result_buttons_frame, text="検索結果保存", command=self.save_search_results).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, pady=5)
            ttk.Button(result_buttons_frame, text="保存リスト", command=self.show_saved_results).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 5), pady=5)
        result_buttons_frame.pack(fill=tk.X)
        
        # 検索結果
        if HAS_TTKB:
            result_frame = ttkb.Labelframe(parent, text="検索結果", bootstyle="info")
        else:
            result_frame = ttk.LabelFrame(parent, text="検索結果")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeviewはttkbootstrapで直接サポートされていないため、標準のttk.Treeviewを使用
        # テーマは自動的に適用されます
        self.result_tree = ttk.Treeview(
            result_frame,
            columns=("filename", "page"),  # ファイル名、ページの2列
            show="headings"
        )
        self.result_tree.heading("filename", text="ファイル名")
        self.result_tree.heading("page", text="ページ")
        # 列の比率: ファイル名:ページ
        self.result_tree.column("filename", width=0, stretch=True, minwidth=100)
        self.result_tree.column("page", width=45, stretch=False, minwidth=45)     # 固定幅
        
        if HAS_TTKB:
            scrollbar = ttkb.Scrollbar(result_frame, orient=tk.VERTICAL, bootstyle="round")
        else:
            scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.result_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.result_tree.yview)
        
        # 列の相対的な重みを設定
        # 比率: ファイル名:ページ = 3:1
        result_frame.columnconfigure(0, weight=3)   # filename列
        result_frame.columnconfigure(1, weight=1)   # page列
        
        # 検索結果選択時のイベント
        self.result_tree.bind("<<TreeviewSelect>>", self.on_result_select)
    
    def init_database(self):
        """データベースの初期化（pdf_index.dbが存在しない場合のみ）"""
        try:
            # 同階層にpdf_index.dbが存在する場合は何もしない
            if os.path.exists("pdf_index.db"):
                return
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # contentとsearch_contentを別々のテーブルとして作成
                cursor.execute("""
                    CREATE VIRTUAL TABLE pdf_contents_fts USING fts5(
                        content,
                        pdf_id UNINDEXED,
                        page UNINDEXED
                    )
                """)
                
                cursor.execute("""
                    CREATE VIRTUAL TABLE pdf_search_contents USING fts5(
                        search_content,
                        pdf_id UNINDEXED,
                        page UNINDEXED
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE pdf_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        filepath TEXT UNIQUE,
                        filename TEXT,
                        file_hash TEXT,
                        last_modified DATETIME
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE pdf_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pdf_id INTEGER,
                        title TEXT,
                        author TEXT,
                        creation_date TEXT,
                        modification_date TEXT,
                        producer TEXT,
                        page_count INTEGER,
                        FOREIGN KEY (pdf_id) REFERENCES pdf_files (id)
                    )
                """)
                
                # 保存された検索結果用のテーブル
                cursor.execute("""
                    CREATE TABLE saved_search_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT,
                        is_phrase_search INTEGER DEFAULT 0,
                        timestamp DATETIME
                    )
                """)
                
                # saved_search_result_itemsテーブルは使用しない（検索語のみ保存）
                
                conn.commit()
                
        except Exception as e:
            log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sqlite_info.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n=== ERROR {datetime.now()} ===\n")
                f.write(f"Database initialization error: {str(e)}\n")
    
    def ensure_saved_results_tables(self):
        """保存された検索結果用のテーブルが存在することを確認（存在しない場合は作成）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # saved_search_resultsテーブルの存在確認
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='saved_search_results'
                """)
                if not cursor.fetchone():
                    cursor.execute("""
                        CREATE TABLE saved_search_results (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            query TEXT,
                            is_phrase_search INTEGER DEFAULT 0,
                            timestamp DATETIME
                        )
                    """)
                else:
                    # 既存テーブルにis_phrase_searchカラムが存在するか確認
                    cursor.execute("PRAGMA table_info(saved_search_results)")
                    columns = [col[1] for col in cursor.fetchall()]
                    if 'is_phrase_search' not in columns:
                        cursor.execute("""
                            ALTER TABLE saved_search_results 
                            ADD COLUMN is_phrase_search INTEGER DEFAULT 0
                        """)
                
                # saved_search_result_itemsテーブルは使用しない（検索語のみ保存）
                
                conn.commit()
        except Exception as e:
            logger.error(f"テーブル作成エラー: {str(e)}")
    
    def get_file_hash(self, filepath):
        """ファイルのハッシュ値を計算"""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
        
    def index_pdf(self, filepath, progress_dialog, last_modified):
        """PDFファイルのインデックス化"""
        try:
            # ファイル情報の取得
            filename = os.path.basename(filepath)
            file_hash = self.get_file_hash(filepath)
            
            # トランザクションを開始
            self.conn.execute("BEGIN")
            
            # 既存のインデックスを削除
            self.cursor.execute(
                "SELECT id FROM pdf_files WHERE filepath = ?",
                (filepath,)
            )
            result = self.cursor.fetchone()
            if result:
                pdf_id = result[0]
                self.cursor.execute(
                    "DELETE FROM pdf_contents_fts WHERE pdf_id = ?",
                    (pdf_id,)
                )
                self.cursor.execute(
                    "DELETE FROM pdf_files WHERE id = ?",
                    (pdf_id,)
                )
            
            # 新しいインデックスを作成
            self.cursor.execute(
                """INSERT INTO pdf_files 
                   (filename, filepath, file_hash, last_modified)
                   VALUES (?, ?, ?, ?)""",
                (filename, filepath, file_hash, last_modified.strftime('%Y-%m-%d %H:%M:%S'))
            )
            pdf_id = self.cursor.lastrowid
            
            # PDFの内容をインデックス化
            doc = fitz.open(filepath)
            total_pages = len(doc)
            
            # バッチ処理用のリスト
            content_values = []
            
            # 各ページの内容をインデックス化
            for i in range(total_pages):
                text = doc[i].get_text()
                
                # MeCabで前処理（設定されている場合）
                if self.mecab:
                    text = self.preprocess_text(text)
                
                content_values.append((text, pdf_id, i))
                
                if len(content_values) >= 100:  # 100ページごとにバッチ挿入
                    self.cursor.executemany(
                        "INSERT INTO pdf_contents_fts (content, pdf_id, page) VALUES (?, ?, ?)",
                        content_values
                    )
                    content_values = []
                
                progress_dialog.update(
                    i + 1,
                    f"{filename} ({i+1}/{total_pages}ページ)"
                )
            
            # 残りのページを挿入
            if content_values:
                self.cursor.executemany(
                    "INSERT INTO pdf_contents_fts (content, pdf_id, page) VALUES (?, ?, ?)",
                    content_values
                )
            
            # トランザクションをコミット
            self.conn.commit()
            doc.close()
            return True
            
        except Exception as e:
            self.conn.rollback()  # エラー時はロールバック
            centered_messagebox(self.root, "error", "エラー", f"インデックス作成中にエラー: {str(e)}")
            return False
            
    def add_file(self):
        """PDFファイルを追加"""
        filepaths = filedialog.askopenfilenames(
            title="PDFファイルを選択",
            filetypes=[("PDFファイル", "*.pdf")]
        )
        
        if not filepaths:
            return
        
        # プログレスウィンドウの作成
        # Toplevelはttkbootstrapで直接サポートされていないため、標準のtk.Toplevelを使用
        # テーマは自動的に適用されます
        progress_window = tk.Toplevel(self.root)
        progress_window.title("処理中")
        progress_window.geometry("300x150")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        LabelClass = ttkb.Label if HAS_TTKB else ttk.Label
        progress_label = LabelClass(progress_window, text="PDFファイルを読み込んでいます...")
        progress_label.pack(pady=10)
        ProgressbarClass = ttkb.Progressbar if HAS_TTKB else ttk.Progressbar
        progress_bar = ProgressbarClass(progress_window, mode='determinate', length=200,
                                       bootstyle="info-striped" if HAS_TTKB else None)
        progress_bar.pack(pady=10)
        file_label = LabelClass(progress_window, text="")
        file_label.pack(pady=10)
        
        total_files = len(filepaths)
        progress_bar['maximum'] = total_files
        
        for index, filepath in enumerate(filepaths, 1):
            try:
                filename = os.path.basename(filepath)
                file_label.config(text=f"処理中: {filename}")
                progress_label.config(text=f"処理中... ({index}/{total_files})")
                
                # PDFファイルを開いてメタデータを取得
                doc = fitz.open(filepath)
                metadata = doc.metadata
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # デァイル情報を追加
                    cursor.execute("""
                        INSERT OR REPLACE INTO pdf_files 
                        (filepath, filename, last_modified) 
                        VALUES (?, ?, ?)
                    """, (
                        filepath,
                        filename,
                        datetime.fromtimestamp(os.path.getmtime(filepath))
                    ))
                    
                    pdf_id = cursor.lastrowid
                    
                    # メタデータを保存
                    cursor.execute("""
                        INSERT OR REPLACE INTO pdf_metadata 
                        (pdf_id, title, author, creation_date, modification_date, 
                         producer, page_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        pdf_id,
                        metadata.get('title', ''),
                        metadata.get('author', ''),
                        metadata.get('creationDate', ''),
                        metadata.get('modDate', ''),
                        metadata.get('producer', ''),
                        len(doc)
                    ))
                    
                    # PDFの内容を保存
                    for page_num in range(len(doc)):
                        page = doc[page_num]
                        # テキスト抽出時のオプションを指定
                        text = page.get_text()  # 余分なオプションを削除
                        # テキストの前処理を行う（名詞の分断結合のみ）
                        processed_text = self.preprocess_text(text)
                        
                        cursor.execute("""
                            INSERT INTO pdf_contents_fts (content, pdf_id, page)
                            VALUES (?, ?, ?)
                        """, (processed_text, pdf_id, page_num))
                    
                    conn.commit()
                
                doc.close()
                self.file_tree.insert("", "end", text=filename, values=(filepath,))
                progress_bar['value'] = index
                progress_window.update()
                
            except Exception as e:
                centered_messagebox(self.root, "error", "エラー", f"ファイルの追加に失敗: {str(e)}")
                print(f"Error: {str(e)}")
        
        progress_window.destroy()
    
    def search_pdfs(self):
        """PDFの内容を検索"""
        query = self.search_var.get().strip()
        if not query:
            centered_messagebox(self.root, "warning", "警告", "検索語を入力してください")
            return
        
        # 検索結果をクリア
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 検索オプションを取得
                case_sensitive = self.case_sensitive_var.get()
                whole_word = self.whole_word_var.get()
                regex_search = self.regex_search_var.get()
                
                # PRAGMA case_sensitive_like で大文字小文字の区別を制御
                if case_sensitive:
                    cursor.execute("PRAGMA case_sensitive_like = ON")
                else:
                    cursor.execute("PRAGMA case_sensitive_like = OFF")
                
                # ダブルクォーテーションで囲まれているかチェック
                is_quoted = query.startswith('"') and query.endswith('"')
                # クォートを除去した検索語を取得（ハイライト用）
                clean_query = query.strip('"') if is_quoted else query
                
                # フレーズ検索モードの判定（チェックボックスまたはダブルクォーテーション）
                is_phrase_search = self.phrase_search_var.get() or is_quoted
                
                # 検索語をスペースで分割（フレーズ検索の場合は分割しない）
                search_terms = []
                if is_phrase_search:
                    # フレーズ検索：クォート除去済みの検索語をそのまま使用
                    search_terms.append(clean_query)
                else:
                    # AND検索：スペースで分割
                    search_terms = clean_query.split()
                
                # SQLクエリの構築
                sql_query = """
                    SELECT DISTINCT
                        f.filepath,
                        c.page,
                        c.content
                    FROM pdf_files f
                    JOIN pdf_contents_fts c ON f.id = c.pdf_id
                    WHERE 
                """
                
                conditions = []
                params = []
                
                for term in search_terms:
                    if '|' in term:  # OR検索
                        or_terms = term.split('|')
                        or_conditions = []
                        for or_term in or_terms:
                            or_term_clean = or_term.strip()
                            if whole_word:
                                # 単語全体で検索（単語境界を考慮）
                                or_conditions.append("(c.content LIKE ? OR c.content LIKE ? OR c.content LIKE ?)")
                                params.append(f'% {or_term_clean} %')
                                params.append(f'{or_term_clean} %')
                                params.append(f'% {or_term_clean}')
                            else:
                                or_conditions.append("c.content LIKE ?")
                                params.append(f'%{or_term_clean}%')
                        conditions.append(f"({' OR '.join(or_conditions)})")
                    else:  # AND検索
                        term_clean = term.strip()
                        if whole_word:
                            # 単語全体で検索（単語境界を考慮）
                            conditions.append("(c.content LIKE ? OR c.content LIKE ? OR c.content LIKE ?)")
                            params.append(f'% {term_clean} %')
                            params.append(f'{term_clean} %')
                            params.append(f'% {term_clean}')
                        else:
                            conditions.append("c.content LIKE ?")
                            params.append(f'%{term_clean}%')
                
                sql_query += ' AND '.join(conditions)
                sql_query += " ORDER BY f.filepath, c.page"
                
                # 検索の実行
                cursor.execute(sql_query, params)
                results = cursor.fetchall()
                
                # 正規表現検索の場合は、結果をフィルタリング
                if regex_search:
                    import re
                    filtered_results = []
                    for filepath, page, content in results:
                        # 各検索語に対して正規表現でマッチするか確認
                        match_found = False
                        for term in search_terms:
                            if '|' in term:
                                # OR検索
                                or_terms = term.split('|')
                                for or_term in or_terms:
                                    try:
                                        flags = 0 if case_sensitive else re.IGNORECASE
                                        or_term_clean = or_term.strip()
                                        if whole_word:
                                            # 単語境界を考慮した正規表現
                                            pattern = r'\b' + or_term_clean + r'\b'
                                        else:
                                            # 正規表現としてそのまま使用
                                            pattern = or_term_clean
                                        if re.search(pattern, content, flags):
                                            match_found = True
                                            break
                                    except re.error:
                                        # 正規表現エラーの場合は通常の検索として扱う
                                        if case_sensitive:
                                            if or_term.strip() in content:
                                                match_found = True
                                                break
                                        else:
                                            if or_term.strip().lower() in content.lower():
                                                match_found = True
                                                break
                                if match_found:
                                    break
                            else:
                                # AND検索
                                try:
                                    flags = 0 if case_sensitive else re.IGNORECASE
                                    term_clean = term.strip()
                                    if whole_word:
                                        # 単語境界を考慮した正規表現
                                        pattern = r'\b' + term_clean + r'\b'
                                    else:
                                        # 正規表現としてそのまま使用
                                        pattern = term_clean
                                    if re.search(pattern, content, flags):
                                        match_found = True
                                except re.error:
                                    # 正規表現エラーの場合は通常の検索として扱う
                                    if case_sensitive:
                                        if term.strip() in content:
                                            match_found = True
                                    else:
                                        if term.strip().lower() in content.lower():
                                            match_found = True
                        
                        if match_found:
                            filtered_results.append((filepath, page, content))
                    results = filtered_results
                
                # 検索語を保存（後でハイライト表示に使用）
                self.current_search_terms = search_terms
                self.current_search_query = clean_query  # クォート除去済み
                self.current_is_phrase_search = is_phrase_search

                # 結果の表示
                for filepath, page, content in results:
                    filename = os.path.basename(filepath)
                    
                    # 最初に見つかった検索語のコンテキストを表示（50文字程度）
                    context = ""
                    found_term = None
                    start_pos = 0
                    end_pos = 0
                    for term in search_terms:
                        if '|' in term:
                            or_terms = term.split('|')
                            for or_term in or_terms:
                                or_term_clean = or_term.strip()
                                if case_sensitive:
                                    pos = content.find(or_term_clean)
                                else:
                                    pos = content.lower().find(or_term_clean.lower())
                                if pos != -1:
                                    found_term = or_term_clean
                                    # 検索語の前後25文字ずつ（合計50文字程度）
                                    start_pos = max(0, pos - 25)
                                    end_pos = min(len(content), pos + len(or_term_clean) + 25)
                                    context = content[start_pos:end_pos].replace('\n', ' ').strip()
                                    break
                            if found_term:
                                break
                        else:
                            term_clean = term.strip()
                            if case_sensitive:
                                pos = content.find(term_clean)
                            else:
                                pos = content.lower().find(term_clean.lower())
                            if pos != -1:
                                found_term = term_clean
                                # 検索語の前後25文字ずつ（合計50文字程度）
                                start_pos = max(0, pos - 25)
                                end_pos = min(len(content), pos + len(term_clean) + 25)
                                context = content[start_pos:end_pos].replace('\n', ' ').strip()
                                break
                    
                    if not context:  # コンテキストが見つからない場合は先頭から表示
                        context = content[:50].replace('\n', ' ').strip()
                        start_pos = 0
                        end_pos = len(context)
                    
                    # 50文字に制限
                    if len(context) > 50:
                        context = context[:50]
                    
                    # 前後に省略記号を追加（内容が長い場合のみ）
                    if len(content) > len(context):
                        if start_pos > 0:
                            context = "..." + context
                        if end_pos < len(content):
                            context = context + "..."
                    
                    # 検索語を強調表示（【】で囲む）
                    if found_term:
                        # 大文字小文字の区別に応じて置換
                        import re
                        if case_sensitive:
                            pattern = re.compile(re.escape(found_term))
                        else:
                            pattern = re.compile(re.escape(found_term), re.IGNORECASE)
                        context_highlighted = pattern.sub(lambda m: f"【{m.group()}】", context)
                    else:
                        context_highlighted = context
                    
                    self.result_tree.insert(
                        "", "end",
                        values=(filename, page + 1),
                        tags=(filepath, str(page))
                    )

                result_count = len(results)
                if result_count > 0:
                    centered_messagebox(self.root, "info", "検索完了", f"{result_count}件見つかりました")
                else:
                    centered_messagebox(self.root, "info", "検索完了", "該当する結果が見つかりませんでした")

        except Exception as e:
            centered_messagebox(self.root, "error", "エラー", f"検索中にエラー: {str(e)}")

    def parse_search_query(self, query):
        """検索クエリを解析して検索条件のリストを返す"""
        search_terms = []
        current_pos = 0
        query_length = len(query)

        while current_pos < query_length:
            char = query[current_pos]

            # ダブルクオートで囲まれた完全一致検索
            if char == '"':
                end_quote = query.find('"', current_pos + 1)
                if end_quote != -1:
                    term = query[current_pos + 1:end_quote]
                    if term:
                        search_terms.append({'type': 'exact', 'value': term})
                    current_pos = end_quote + 1
                else:
                    current_pos += 1

            # OR検索
            elif query[current_pos:].upper().startswith('OR '):
                # 前の検索語と次の索語をOR条件として結合
                if search_terms and current_pos + 3 < query_length:
                    prev_term = search_terms.pop()['value']
                    next_space = query.find(' ', current_pos + 3)
                    next_term = query[current_pos + 3:next_space if next_space != -1 else None]
                    search_terms.append({
                        'type': 'or',
                        'values': [prev_term, next_term]
                    })
                    current_pos = next_space if next_space != -1 else query_length
                else:
                    current_pos += 3

            # ワイルドカード検索
            elif '*' in query[current_pos:].split()[0]:
                end_space = query.find(' ', current_pos)
                term = query[current_pos:end_space if end_space != -1 else None]
                if term:
                    search_terms.append({'type': 'wildcard', 'value': term})
                current_pos = end_space if end_space != -1 else query_length

            # 通常の検索語（AND検索）
            else:
                end_space = query.find(' ', current_pos)
                if end_space == -1:
                    term = query[current_pos:]
                    if term:
                        search_terms.append({'type': 'exact', 'value': term})
                    break
                else:
                    term = query[current_pos:end_space]
                    if term:
                        search_terms.append({'type': 'exact', 'value': term})
                    current_pos = end_space

            # スペースをスキップ
            while current_pos < query_length and query[current_pos] == ' ':
                current_pos += 1

        return search_terms

    def get_search_context(self, content, search_terms):
        """検索語を含む前後のコンテキストを取得"""
        # 最初に見つかった検索語の位置を特定
        min_pos = len(content)
        search_len = 0
        
        for term in search_terms:
            if term['type'] == 'exact':
                pos = content.lower().find(term['value'].lower())
                if pos != -1 and pos < min_pos:
                    min_pos = pos
                    search_len = len(term['value'])
            elif term['type'] == 'or':
                for or_term in term['values']:
                    pos = content.lower().find(or_term.lower())
                    if pos != -1 and pos < min_pos:
                        min_pos = pos
                        search_len = len(or_term)
        
        if min_pos == len(content):
            return content[:50]  # 見つからない場合は先頭から50文字
        
        # 前後10文字を抽出
        start_pos = max(0, min_pos - 10)
        end_pos = min(len(content), min_pos + search_len + 10)
        
        context = content[start_pos:end_pos].replace('\n', ' ').strip()
        
        # 前後に省略記号を追加
        if start_pos > 0:
            context = "..." + context
        if end_pos < len(content):
            context = context + "..."
        
        return context
    
    def on_result_select(self, event):
        """検索結果選択時のハンドラ"""
        selection = self.result_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        filepath, page = self.result_tree.item(item, "tags")
        page = int(page)
        
        try:
            # 検索語を取得（保存された検索語を使用）
            if hasattr(self, 'current_search_query'):
                search_term = self.current_search_query
                is_phrase_search = getattr(self, 'current_is_phrase_search', False)
            else:
                # フォールバック：入力欄から取得
                search_term = self.search_var.get().strip()
                # ダブルクォーテーションを除去
                if search_term.startswith('"') and search_term.endswith('"'):
                    search_term = search_term.strip('"')
                    is_phrase_search = True
                else:
                    is_phrase_search = self.phrase_search_var.get()
            
            # 検索オプションを取得
            case_sensitive = self.case_sensitive_var.get()
            
            self.pdf_viewer.load_pdf(filepath, page)
            self.pdf_viewer.show_page(page, search_term, fit_to_page=True, 
                                     is_phrase_search=is_phrase_search, case_sensitive=case_sensitive)
            # PDFViewerFrameにcase_sensitiveを保存（ズーム時に使用）
            self.pdf_viewer.case_sensitive = case_sensitive
        except Exception as e:
            centered_messagebox(self.root, "error", "エラー", f"PDFの表示に失敗: {str(e)}")
    
    def navigate_search_result(self, direction):
        """検索結果の前後を移動（direction: -1=前へ, 1=次へ）"""
        # 検索結果が存在するか確認
        items = self.result_tree.get_children()
        if not items:
            return
        
        # 現在選択されている項目を取得
        selection = self.result_tree.selection()
        if not selection:
            # 選択されていない場合は最初の項目を選択
            if items:
                self.result_tree.selection_set(items[0])
                self.result_tree.focus(items[0])
                # 選択イベントをトリガー
                self.on_result_select(None)
            return
        
        current_item = selection[0]
        current_index = items.index(current_item) if current_item in items else -1
        
        if current_index == -1:
            return
        
        # 前後を計算
        new_index = current_index + direction
        
        # 範囲チェック
        if new_index < 0:
            new_index = len(items) - 1  # 最後にループ
        elif new_index >= len(items):
            new_index = 0  # 最初にループ
        
        # 新しい項目を選択
        new_item = items[new_index]
        self.result_tree.selection_set(new_item)
        self.result_tree.focus(new_item)
        # 表示領域にスクロール
        self.result_tree.see(new_item)
        # 選択イベントをトリガー
        self.on_result_select(None)
    
    def show_popup_menu(self, event):
        """右クリックメニューを表示"""
        # 右クリックされた項目を選択状態にする
        item = self.file_tree.identify_row(event.y)
        if item:
            self.file_tree.selection_set(item)
            self.popup_menu.post(event.x_root, event.y_root)
    
    def on_file_double_click(self, event):
        """ファイルツリーのダブルクリックでPDFをプレビュー表示"""
        item = self.file_tree.identify_row(event.y)
        if not item:
            return
        
        try:
            filepath = self.file_tree.item(item)['values'][0]
            if filepath and os.path.exists(filepath):
                # PDFを読み込んで1ページ目を表示
                self.pdf_viewer.load_pdf(filepath, 0)
                self.pdf_viewer.show_page(0, fit_to_page=True)
        except Exception as e:
            centered_messagebox(self.root, "error", "エラー", f"PDFの表示に失敗: {str(e)}")
    
    def remove_pdf(self):
        """選択されたPDFを削除"""
        selection = self.file_tree.selection()
        if not selection:
            return
            
        item = selection[0]
        filepath = self.file_tree.item(item)['values'][0]
        
        if centered_messagebox(self.root, "yesno", "確認", "選択したPDFをストから削除しますか？"):
            try:
                # データベースから削除
                self.cursor.execute(
                    "SELECT id FROM pdf_files WHERE filepath = ?",
                    (filepath,)
                )
                result = self.cursor.fetchone()
                
                if result:
                    pdf_id = result[0]
                    # トランザクションを開始
                    self.conn.execute("BEGIN")
                    
                    # 関連するコンテンツを削除
                    self.cursor.execute(
                        "DELETE FROM pdf_contents_fts WHERE pdf_id = ?",
                        (pdf_id,)
                    )
                    
                    # ファイル情報を削除
                    self.cursor.execute(
                        "DELETE FROM pdf_files WHERE id = ?",
                        (pdf_id,)
                    )
                    
                    # トランザクションをコミット
                    self.conn.commit()
                
                # Treeviewから項目を削除
                self.file_tree.delete(item)
                
                centered_messagebox(self.root, "info", "完了", "PDFをリストから削除しました")
                
            except Exception as e:
                self.conn.rollback()
                centered_messagebox(self.root, "error", "エラー", f"削除中エラーが発生しました: {str(e)}")
    
    def load_registered_pdfs(self):
        """データベースから登録済みPDFファイルを読み込んで表示"""
        try:
            self.cursor.execute("""
                SELECT filename, filepath 
                FROM pdf_files 
                ORDER BY filename
            """)
            
            for filename, filepath in self.cursor.fetchall():
                # ファイル実際に存するか確認
                if os.path.exists(filepath):
                    self.file_tree.insert(
                        "", "end",
                        text=filename,
                        values=(filepath,)
                    )
                else:
                    # ファイルが見つからない場合はDBから削除
                    self.cursor.execute("""
                        DELETE FROM pdf_contents_fts 
                        WHERE pdf_id IN (
                            SELECT id 
                            FROM pdf_files 
                            WHERE filepath = ?
                        )
                    """, (filepath,))
                    self.cursor.execute(
                        "DELETE FROM pdf_files WHERE filepath = ?",
                        (filepath,)
                    )
                    self.conn.commit()
                
        except Exception as e:
            centered_messagebox(self.root, "error", "エラー", f"登録済みPDFの読み込みに失敗: {str(e)}")

    def _set_ime_mode(self, widget):
        """IMEを全角入力モードに設定"""
        try:
            widget.tk.call('tk', 'ime', 'configure', widget, '-mode', 'active')
        except tk.TclError:
            pass  # IME設定が利用できない環境の場合

    def clear_search_results(self):
        """検索結果をクリア"""
        # 検索結果ツリーをクリア
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # 検索窓もクリア
        self.search_var.set("")
        
        # PDFビューアもクリア
        if hasattr(self, 'pdf_viewer'):
            self.pdf_viewer.clear_view()

    def open_file_folder(self):
        """選択されたPDFファイルのフォルダを開く"""
        selection = self.file_tree.selection()
        if not selection:
            return
        
        try:
            # 最初に選択されたファイルのパスを取得
            item = selection[0]
            filepath = self.file_tree.item(item)["values"][0]
            
            # ファイルパスからディレクトリを取得
            folder_path = os.path.dirname(filepath)
            
            # フォルダが存在するか確認
            if os.path.exists(folder_path):
                # Windowsの場合
                if sys.platform == "win32":
                    os.startfile(folder_path)
                # macOSの場合
                elif sys.platform == "darwin":
                    os.system(f'open "{folder_path}"')
                # Linuxの場合
                else:
                    os.system(f'xdg-open "{folder_path}"')
            else:
                centered_messagebox(self.root, "error", "エラー", f"フォルダが見つかりません:\n{folder_path}")
        except Exception as e:
            centered_messagebox(self.root, "error", "エラー", f"フォルダを開くのに失敗: {str(e)}")
    
    def delete_file(self):
        """選択されたPDFファイルを削除"""
        selection = self.file_tree.selection()
        if not selection:
            return
        
        if messagebox.askyesno("確認", "選択したPDFをリストから削除しますか？"):
            for item in selection:
                try:
                    # ファイルパスを取得
                    filepath = self.file_tree.item(item)["values"][0]
                    
                    # データベースから削除
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        # pdf_filesのIDを取得
                        cursor.execute("SELECT id FROM pdf_files WHERE filepath = ?", (filepath,))
                        pdf_id = cursor.fetchone()
                        
                        if pdf_id:
                            pdf_id = pdf_id[0]
                            # pdf_contents_ftsテーブルから削除
                            cursor.execute("DELETE FROM pdf_contents_fts WHERE pdf_id = ?", (pdf_id,))
                            # pdf_filesテーブルから削除
                            cursor.execute("DELETE FROM pdf_files WHERE id = ?", (pdf_id,))
                            conn.commit()
                            
                            # 削除が成功したらツリービューからも削除
                            self.file_tree.delete(item)
                            
                            # PDFビューアをクリア（表示中のファイルが削除された場合）
                            if hasattr(self, 'pdf_viewer') and self.pdf_viewer.doc:
                                current_path = self.pdf_viewer.current_path if hasattr(self.pdf_viewer, 'current_path') else None
                                if current_path == filepath:
                                    self.pdf_viewer.clear_view()
                            
                            # 検索結果から該当ファイルの項目を削除
                            for result_item in self.result_tree.get_children():
                                result_values = self.result_tree.item(result_item)
                                if "tags" in result_values and result_values["tags"]:
                                    result_filepath = result_values["tags"][0]
                                    if result_filepath == filepath:
                                        self.result_tree.delete(result_item)
                
                except sqlite3.Error as e:
                    centered_messagebox(self.root, "error", "エラー", f"データベースからの削除に失敗: {str(e)}")
                    print(f"DB Error: {str(e)}")  # デバッグ用
                except Exception as e:
                    centered_messagebox(self.root, "error", "エラー", f"削除処理に失敗: {str(e)}")
                    print(f"Error: {str(e)}")  # デバッグ用
            
            # データベースの最適化（VACUUMの実行）
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("VACUUM")
            except sqlite3.Error as e:
                print(f"DB Optimization Error: {str(e)}")  # デバッグ用

    def clear_all_files(self):
        """すべてのPDF登録を削除"""
        # 確認ダイアログ
        if not centered_messagebox(self.root, "question", "確認", 
                                   "すべてのPDF登録を削除しますか？\nこの操作は取り消せません。", 
                                   return_result=True):
            return
        
        try:
            # データベースからすべてのPDFを削除
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # pdf_contents_ftsテーブルからすべて削除
                cursor.execute("DELETE FROM pdf_contents_fts")
                # pdf_filesテーブルからすべて削除
                cursor.execute("DELETE FROM pdf_files")
                # pdf_metadataテーブルからすべて削除
                cursor.execute("DELETE FROM pdf_metadata")
                conn.commit()
            
            # ツリービューからすべて削除
            for item in self.file_tree.get_children():
                self.file_tree.delete(item)
            
            # PDFビューアをクリア
            if hasattr(self, 'pdf_viewer'):
                self.pdf_viewer.clear_view()
            
            # 検索結果をクリア
            self.clear_search_results()
            
            centered_messagebox(self.root, "info", "完了", "すべてのPDF登録を削除しました。")
            
        except Exception as e:
            centered_messagebox(self.root, "error", "エラー", f"削除処理に失敗: {str(e)}")
    
    def save_search_results(self):
        """検索語とフレーズ検索の状態をデータベースに保存"""
        # 検索語を取得
        query = self.search_var.get().strip()
        if not query:
            centered_messagebox(self.root, "warning", "警告", "保存する検索語がありません。")
            return
        
        # フレーズ検索の状態を取得
        is_phrase_search = 1 if self.phrase_search_var.get() else 0
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 同じ検索語とフレーズ検索の状態の組み合わせが既に保存されているかチェック
                cursor.execute("""
                    SELECT id FROM saved_search_results 
                    WHERE query = ? AND is_phrase_search = ?
                """, (query, is_phrase_search))
                existing = cursor.fetchone()
                
                if existing:
                    # 既に存在する場合はタイムスタンプを更新
                    cursor.execute("""
                        UPDATE saved_search_results 
                        SET timestamp = ? 
                        WHERE id = ?
                    """, (datetime.now(), existing[0]))
                    conn.commit()
                    phrase_text = "ON" if is_phrase_search else "OFF"
                    centered_messagebox(self.root, "info", "完了", f"検索語を更新しました。\n検索語: {query}\nフレーズ検索: {phrase_text}")
                else:
                    # 新規保存
                    cursor.execute("""
                        INSERT INTO saved_search_results (query, is_phrase_search, timestamp)
                        VALUES (?, ?, ?)
                    """, (query, is_phrase_search, datetime.now()))
                    conn.commit()
                    phrase_text = "ON" if is_phrase_search else "OFF"
                    centered_messagebox(self.root, "info", "完了", f"検索語を保存しました。\n検索語: {query}\nフレーズ検索: {phrase_text}")
        except Exception as e:
            centered_messagebox(self.root, "error", "エラー", f"検索語の保存に失敗: {str(e)}")
    
    def show_saved_results(self):
        """保存された検索結果の一覧を表示"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 保存された検索語を取得（新しい順）
                cursor.execute("""
                    SELECT id, query, is_phrase_search, timestamp
                    FROM saved_search_results
                    ORDER BY timestamp DESC
                """)
                saved_results = cursor.fetchall()
        except Exception as e:
            centered_messagebox(self.root, "error", "エラー", f"保存データの読み込みに失敗: {str(e)}")
            return
        
        if not saved_results:
            centered_messagebox(self.root, "info", "情報", "保存された検索結果がありません。")
            return
        
        # ダイアログを作成
        dialog = tk.Toplevel(self.root)
        dialog.title("保存された検索結果")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 親ウィンドウの位置とサイズを取得
        self.root.update_idletasks()
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        
        # メインフレーム
        if HAS_TTKB:
            main_frame = ttkb.Frame(dialog)
        else:
            main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # リストボックス
        listbox_frame = ttk.Frame(main_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(listbox_frame, yscrollcommand=scrollbar.set, font=('Yu Gothic UI', 11))
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)
        
        # 保存された検索語をリストに追加（新しい順）
        for saved_result in saved_results:
            result_id, query, is_phrase_search, timestamp = saved_result
            if not query:
                query = "（検索語なし）"
            try:
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp)
                else:
                    dt = datetime.fromtimestamp(timestamp)
                time_str = dt.strftime("%Y/%m/%d %H:%M")
            except:
                time_str = str(timestamp)
            phrase_text = "[フレーズ]" if is_phrase_search else ""
            listbox.insert(tk.END, f"{query} {phrase_text} - {time_str}")
        
        # ボタンフレーム
        if HAS_TTKB:
            button_frame = ttkb.Frame(main_frame)
            ttkb.Button(button_frame, text="読み込む", 
                       command=lambda: self.load_saved_result(dialog, listbox, saved_results),
                       bootstyle="primary").pack(side=tk.LEFT, padx=(0, 5))
            ttkb.Button(button_frame, text="削除", 
                       command=lambda: self.delete_saved_result(dialog, listbox, saved_results),
                       bootstyle="danger").pack(side=tk.LEFT, padx=(0, 5))
            ttkb.Button(button_frame, text="閉じる", command=dialog.destroy,
                       bootstyle="secondary").pack(side=tk.LEFT)
        else:
            button_frame = ttk.Frame(main_frame)
            ttk.Button(button_frame, text="読み込む", 
                      command=lambda: self.load_saved_result(dialog, listbox, saved_results)).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="削除", 
                      command=lambda: self.delete_saved_result(dialog, listbox, saved_results)).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="閉じる", command=dialog.destroy).pack(side=tk.LEFT)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # ダブルクリックで読み込み
        listbox.bind("<Double-Button-1>", lambda e: self.load_saved_result(dialog, listbox, saved_results))
        
        # ダイアログのサイズを計算
        dialog.update_idletasks()
        dialog_width = 600
        dialog_height = 400
        x = parent_x + (parent_width // 2) - (dialog_width // 2)
        y = parent_y + (parent_height // 2) - (dialog_height // 2)
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def load_saved_result(self, dialog, listbox, saved_results):
        """保存された検索語を読み込んで検索を実行"""
        selection = listbox.curselection()
        if not selection:
            centered_messagebox(self.root, "warning", "警告", "読み込む検索語を選択してください。")
            return
        
        # 選択された検索語を取得
        result_id, query, is_phrase_search, timestamp = saved_results[selection[0]]
        
        if not query:
            centered_messagebox(self.root, "warning", "警告", "検索語が空です。")
            return
        
        # 検索語を検索窓に設定
        self.search_var.set(query)
        
        # フレーズ検索の状態を復元
        self.phrase_search_var.set(bool(is_phrase_search))
        
        # ダイアログを閉じる
        dialog.destroy()
        
        # 検索を実行
        self.search_pdfs()
    
    def delete_saved_result(self, dialog, listbox, saved_results):
        """保存された検索語を削除"""
        selection = listbox.curselection()
        if not selection:
            centered_messagebox(self.root, "warning", "警告", "削除する検索語を選択してください。")
            return
        
        # 確認
        if not centered_messagebox(self.root, "question", "確認", 
                                   "選択した検索語を削除しますか？", 
                                   return_result=True):
            return
        
        # 選択された検索語のIDを取得
        result_id, query, is_phrase_search, timestamp = saved_results[selection[0]]
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 検索語を削除
                cursor.execute("DELETE FROM saved_search_results WHERE id = ?", (result_id,))
                conn.commit()
            
            # リストボックスを更新
            listbox.delete(selection[0])
            saved_results.pop(selection[0])
            
            centered_messagebox(self.root, "info", "完了", "検索語を削除しました。")
        except Exception as e:
            centered_messagebox(self.root, "error", "エラー", f"削除に失敗: {str(e)}")

    def __del__(self):
        """デストラクタ：データベース接続をじる"""
        if hasattr(self, 'conn'):
            self.conn.close()

    def search_content(self, search_term):
        """PDF内容を検索"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT pdf_id, page, content
                    FROM pdf_contents_fts
                    WHERE content MATCH ?
                """, (search_term,))
                results = cursor.fetchall()
                return results
        except sqlite3.Error as e:
            centered_messagebox(self.root, "error", "エラー", f"検索に失敗: {str(e)}")
            print(f"Search Error: {str(e)}")

    def update_database_schema(self):
        """データベーススキーマの更新"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # メタデータテーブルの存在確認
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='pdf_metadata'
                """)
                
                if not cursor.fetchone():
                    # メタデータテーブルが存在しない場合は作成
                    print("メタデータテーブルを作成中...")
                    cursor.execute("""
                        CREATE TABLE pdf_metadata (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            pdf_id INTEGER,
                            title TEXT,
                            author TEXT,
                            creation_date TEXT,
                            modification_date TEXT,
                            producer TEXT,
                            page_count INTEGER,
                            FOREIGN KEY (pdf_id) REFERENCES pdf_files (id)
                        )
                    """)
                    print("メタデータテーブルが作成されました")
                
                conn.commit()
                
        except sqlite3.Error as e:
            centered_messagebox(self.root, "error", "エラー", f"データベースの更新に失敗: {str(e)}")
            print(f"Database Update Error: {str(e)}")

    def add_pdf_content(self, pdf_id, page_num, content):
        """PDFの内容をFTSテーブルに追加"""
        try:
            # テキストの前処理
            processed_content = self.preprocess_text(content)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO pdf_contents_fts (content, pdf_id, page)
                    VALUES (?, ?, ?)
                """, (processed_content, pdf_id, page_num))
                conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding PDF content: {str(e)}")
    
    def preprocess_text(self, text: str) -> str:
        """テキストの前処理 - 分断された名詞のみを結合"""
        try:
            if self.mecab:
                lines = text.split('\n')
                result_lines = []
                i = 0

                while i < len(lines):
                    current_line = lines[i].rstrip()  # 行末の空白のみ削除

                    # 最後の行でない場合のみ、次の行との結合をチェック
                    if i < len(lines) - 1:
                        next_line = lines[i + 1].rstrip()
                    
                    # 行末と次の行頭で名詞が分断されているかチェック
                    if current_line and next_line:
                        # 【追加】英語（ASCII文字）の場合の処理
                        if current_line[-1].isascii() and next_line[0].isascii():
                            # ハイフンで終わる場合は連結、それ以外はスペースを入れて連結
                            if current_line.endswith('-'):
                                result_lines.append(current_line[:-1] + next_line)
                            else:
                                result_lines.append(current_line + " " + next_line)
                            i += 2
                            continue

                        # 既存のMeCab処理（日本語向け）
                        test_word = current_line[-1] + next_line[0]
                        node = self.mecab.parseToNode(test_word)
                        
                        if node and node.next and node.next.feature.split(',')[0] == '名詞':
                            # 名詞の分断が見つかった場合、行を結合
                            result_lines.append(current_line + next_line)
                            i += 2
                            continue
                
                    # 名詞の分断でない場合は現在の行をそのまま追加
                    result_lines.append(current_line)
                    i += 1
            
                return '\n'.join(result_lines)
            
            return text
        
        except Exception as e:
            print(f"テキスト処理エラー: {str(e)}")
            return text

    def search_pdf_contents(self, query):
        """PDFの内容を検索"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # NEAR演算子を使用して近接検索を実装
                cursor.execute("""
                    SELECT pdf_files.filepath, pdf_files.filename, pdf_contents_fts.page, 
                           snippet(pdf_contents_fts, -1, '【', '】', '...', 64) as content
                    FROM pdf_contents_fts
                    JOIN pdf_files ON pdf_contents_fts.pdf_id = pdf_files.id
                    WHERE pdf_contents_fts MATCH ?
                    ORDER BY rank
                """, (query,))
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Search error: {str(e)}")
            return []

def calculate_file_hash(filepath):
    """ファイルのSHA-256ハッシュ値を計算"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        # ファイルを小分けに読み込んでハッシュ計算
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def main():
    # ttkbootstrapのテーマを適用
    if HAS_TTKB:
        # ttkbootstrapのダークテーマを適用（darklyテーマを使用）
        root = ttkb.Window(themename="darkly")  # ダークテーマ: darkly, cyborg, superhero, solar, vapor など
        # テーマが確実に適用されるようにStyleを設定
        style = ttkb.Style()
        style.theme_use("darkly")
    else:
        root = tk.Tk()
    
    app = PDFSearchApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()