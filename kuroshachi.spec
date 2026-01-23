# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os

block_cipher = None

# アイコンファイルのパスを取得（specファイルと同じディレクトリ）
# PyInstaller実行時はカレントディレクトリがspecファイルのディレクトリになる
icon_path = os.path.abspath('kuroshachi_icon.ico')

# ---------------------------------------------------------
# 1. 必要なライブラリのデータをすべて収集する
# ---------------------------------------------------------

# tkinterweb (HTML表示用)
datas_tw, binaries_tw, hiddenimports_tw = collect_all('tkinterweb')

# ttkbootstrap (デザインテーマ用 - これがないと起動しない場合があります)
datas_tb, binaries_tb, hiddenimports_tb = collect_all('ttkbootstrap')

# ipadic (MeCab辞書用 - これがないと日本語処理ができません)
datas_ipadic, binaries_ipadic, hiddenimports_ipadic = collect_all('ipadic')

# 収集したデータを1つのリストにまとめる
datas = datas_tw + datas_tb + datas_ipadic
binaries = binaries_tw + binaries_tb + binaries_ipadic
hiddenimports = hiddenimports_tw + hiddenimports_tb + hiddenimports_ipadic

# ---------------------------------------------------------
# 2. ガイドファイルとアイコンファイルを追加
# ---------------------------------------------------------
# guide.md を EXEのルート(.)に配置
datas.append(('guide.md', '.'))
# アイコンファイルを EXEのルート(.)に配置
datas.append(('kuroshachi_icon.ico', '.'))
datas.append(('kuroshachi_icon_512.png', '.'))

# ---------------------------------------------------------
# 3. ビルド設定
# ---------------------------------------------------------
a = Analysis(
    ['kuroshachi.pyw'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='kuroshachi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # GUIアプリなのでFalse
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,  # アイコンファイルを指定
)
