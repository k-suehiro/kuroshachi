# 黒鯱（KuroShachi） - EXEビルド手順

このドキュメントでは、黒鯱（KuroShachi）をEXEファイルにビルドする手順を説明します。

## 前提条件

- Python 3.x がインストールされていること
- インターネット接続（依存関係のダウンロード用）
- Windows環境（バッチファイルを使用する場合）

## ビルド手順

### 方法1: バッチファイルを使用（推奨）

1. `build_kuroshachi.bat` をダブルクリックして実行
2. ビルドが完了すると、`dist\kuroshachi.exe` が作成されます

バッチファイルは以下の処理を自動的に実行します：
- 仮想環境の作成（`venv_kuroshachi`）
- 依存関係のインストール
- PyInstallerによるEXEファイルの作成
- 一時ファイルのクリーンアップ

### 方法2: 手動でビルド

1. 仮想環境を作成
```bash
python -m venv venv_kuroshachi
```

2. 仮想環境をアクティベート
```bash
venv_kuroshachi\Scripts\activate
```

3. 依存関係をインストール
```bash
python -m pip install --upgrade pip
python -m pip install -r requirements_kuroshachi.txt
```

4. PyInstallerでEXEを作成
```bash
pyinstaller --clean kuroshachi.spec
```

## ビルド結果

- EXEファイル: `dist\kuroshachi.exe`
- 一時ファイル: ビルド完了後、`build` フォルダと `__pycache__` フォルダは自動的に削除されます
- データベース: 実行時に `pdf_index.db` がEXEと同じディレクトリに作成されます（既存の場合は保持されます）

## 注意事項

- **MeCabの辞書ファイル（ipadic）**: 自動的にバンドルされます
- **ガイドファイル（guide.md）**: EXEに同梱されるため、単体のEXEファイルのみで配布可能です
- **アイコンファイル**: `kuroshachi_icon.ico` と `kuroshachi_icon_512.png` がEXEに同梱されます
- **初回ビルド**: 依存関係のダウンロードとビルドに時間がかかる場合があります（数分程度）
- **EXEファイルサイズ**: 約100-200MB程度になります（依存ライブラリを含むため）
- **データベースの保持**: 既存の `pdf_index.db` は保持されるため、EXEを上書きするだけで既存のインデックスデータをそのまま使用できます

## トラブルシューティング

### MeCabの辞書が見つからない場合

1. `pip install ipadic` でipadicをインストール
2. インストール場所を確認: `python -c "import site; import os; print([os.path.join(s, 'ipadic') for s in site.getsitepackages() if os.path.exists(os.path.join(s, 'ipadic'))])"`

### PyInstallerのエラーが発生する場合

- `pip install --upgrade pyinstaller` でPyInstallerを最新版に更新
- `--clean` オプションを付けて再ビルド: `pyinstaller --clean kuroshachi.spec`
- 仮想環境を再作成してから再試行

### ビルドは成功したがEXEが起動しない場合

- コンソール版で実行してエラーメッセージを確認:
  - `kuroshachi.spec` の `console=False` を `console=True` に変更して再ビルド
- 依存関係が不足している可能性があるため、`requirements_kuroshachi.txt` のすべてのパッケージがインストールされているか確認

### 仮想環境の作成に失敗する場合

- Pythonが正しくインストールされているか確認: `python --version`
- 管理者権限で実行してみる
- 別のディレクトリで仮想環境を作成してみる

### 依存関係のインストールに失敗する場合

- インターネット接続を確認
- `pip` を最新版にアップグレード: `python -m pip install --upgrade pip`
- プロキシ設定が必要な場合は、環境変数で設定するか、`pip` の設定ファイルを確認

## ビルド後の配布について

- `dist\kuroshachi.exe` のみを配布すれば動作します
- データベースファイル（`pdf_index.db`）は実行時に自動的に作成されるため、初回起動時は不要です
- 既存ユーザーへのアップデート配布時は、EXEファイルを上書きするだけで既存のデータベースをそのまま使用できます
