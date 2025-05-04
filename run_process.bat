@echo off
setlocal enabledelayedexpansion

echo ========================================================================
echo バリアフリー施設データ処理バッチ
echo ========================================================================
echo.

REM 仮想環境をアクティベート
echo 仮想環境をアクティベートしています...
call .\venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo 仮想環境のアクティベートに失敗しました。
    echo venv ディレクトリが存在するか確認してください。
    exit /b 1
)
echo 仮想環境のアクティベートが完了しました。
echo.

REM 施設と停留所の距離チェックスクリプト実行
echo 施設と停留所の距離チェックスクリプトを実行しています...
python facilities_check.py
if %ERRORLEVEL% neq 0 (
    echo 距離チェックスクリプトの実行に失敗しました。
    echo スクリプトのエラーを確認してください。
    exit /b 2
)
echo 距離チェックスクリプトの実行が完了しました。
echo.

REM JSON圧縮ツール実行
echo 各JSONフォルダを圧縮処理しています...

REM kazaguruma_jsonフォルダを処理
if exist kazaguruma_json (
    echo kazaguruma_jsonフォルダを処理中...
    python json_minifier.py kazaguruma_json
    if %ERRORLEVEL% neq 0 (
        echo kazaguruma_jsonフォルダの圧縮処理に失敗しました。
        echo 詳細なエラーメッセージを確認してください。
    ) else (
        echo kazaguruma_jsonフォルダの圧縮処理が完了しました。
    )
    echo.
) else (
    echo kazaguruma_jsonフォルダが見つかりません。処理をスキップします。
    echo.
)

REM jsonフォルダを処理
if exist json (
    echo jsonフォルダを処理中...
    python json_minifier.py json
    if %ERRORLEVEL% neq 0 (
        echo jsonフォルダの圧縮処理に失敗しました。
        echo 詳細なエラーメッセージを確認してください。
    ) else (
        echo jsonフォルダの圧縮処理が完了しました。
    )
    echo.
) else (
    echo jsonフォルダが見つかりません。処理をスキップします。
    echo.
)

REM 処理完了
echo ========================================================================
echo 全ての処理が完了しました。
echo ========================================================================

REM 仮想環境を非アクティブ化
call deactivate
pause 