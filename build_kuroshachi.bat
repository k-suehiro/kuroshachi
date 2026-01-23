@echo off
chcp 65001 >nul
REM バッチファイルのディレクトリに移動
cd /d "%~dp0"
echo ========================================
echo 黒鯱 - EXEビルドスクリプト
echo ========================================
echo 作業ディレクトリ: %CD%
echo.

REM 必要なファイルの存在確認
if not exist "requirements_kuroshachi.txt" (
    echo エラー: requirements_kuroshachi.txt が見つかりません
    echo 現在のディレクトリ: %CD%
    pause
    exit /b 1
)

if not exist "kuroshachi.spec" (
    echo エラー: kuroshachi.spec が見つかりません
    pause
    exit /b 1
)

REM 仮想環境の確認
if not exist "venv_kuroshachi\" (
    echo [1/4] 仮想環境を作成中...
    python -m venv venv_kuroshachi
    if errorlevel 1 (
        echo エラー: 仮想環境の作成に失敗しました
        pause
        exit /b 1
    )
)

REM 仮想環境をアクティベート
echo [2/4] 仮想環境をアクティベート中...
if exist "venv_kuroshachi\Scripts\activate.bat" (
    call venv_kuroshachi\Scripts\activate.bat
) else (
    echo エラー: 仮想環境が見つかりません
    pause
    exit /b 1
)
if errorlevel 1 (
    echo エラー: 仮想環境のアクティベートに失敗しました
    pause
    exit /b 1
)

REM 依存関係のインストール
echo [3/4] 依存関係をインストール中...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo 警告: pipのアップグレードに失敗しましたが、続行します...
)
python -m pip install -r requirements_kuroshachi.txt
if errorlevel 1 (
    echo エラー: 依存関係のインストールに失敗しました
    echo 現在のディレクトリ: %CD%
    echo requirements_kuroshachi.txtのパス: %CD%\requirements_kuroshachi.txt
    pause
    exit /b 1
)

REM PyInstallerでEXEを作成
echo [4/4] EXEファイルを作成中...
pyinstaller --clean kuroshachi.spec
if errorlevel 1 (
    echo エラー: EXEファイルの作成に失敗しました
    pause
    exit /b 1
)

REM 一時ファイルとフォルダを削除（distフォルダは残す）
echo.
echo [5/5] 一時ファイルをクリーンアップ中...
if exist "build" (
    echo buildフォルダを削除中...
    rmdir /s /q "build"
)
if exist "__pycache__" (
    echo __pycache__フォルダを削除中...
    rmdir /s /q "__pycache__"
)
REM *.pycファイルを削除
for /r %%f in (*.pyc) do del /q "%%f" 2>nul
REM *.pyoファイルを削除
for /r %%f in (*.pyo) do del /q "%%f" 2>nul

echo.
echo ========================================
echo ビルド完了！
echo ========================================
echo EXEファイルは dist\kuroshachi.exe に作成されました
echo 一時ファイルは削除されました（distフォルダのみ残っています）
echo.
pause
