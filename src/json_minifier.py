#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
JSON圧縮スクリプト

このスクリプトは、指定されたフォルダ内のすべてのJSONファイルを読み込み、
インデントを削除した圧縮形式で新しいフォルダに保存します。
元のフォルダ名に「_min」というサフィックスが追加された新しいフォルダが作成されます。

使用方法:
    python json_minifier.py <対象フォルダパス>

引数:
    target_folder: JSONファイルが格納されているフォルダのパス
"""

import argparse
import json
import os
import sys
import shutil
from pathlib import Path


def minify_json_file(input_file, output_file):
    """
    JSONファイルをインデントなしの形式に変換して保存する関数
    
    Args:
        input_file: 入力JSONファイルのパス
        output_file: 出力先JSONファイルのパス
    
    Returns:
        bool: 変換が成功したかどうか
    """
    try:
        # JSONファイルを読み込む
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # インデントなしでJSONを保存
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        
        return True
    except Exception as e:
        print(f"エラー: {input_file} の処理中に例外が発生しました: {str(e)}", file=sys.stderr)
        return False


def process_folder(folder_path):
    """
    指定されたフォルダ内のすべてのJSONファイルを処理する関数
    
    Args:
        folder_path: 処理対象のフォルダパス
    
    Returns:
        tuple: 処理されたファイル数、エラーが発生したファイル数、新しいフォルダのパス
    """
    # パスオブジェクトを作成
    folder = Path(folder_path)
    
    # フォルダが存在するか確認
    if not folder.exists() or not folder.is_dir():
        print(f"エラー: フォルダ '{folder}' が見つかりません。", file=sys.stderr)
        return 0, 0, None
    
    # 新しいフォルダ名を作成（元のフォルダ名 + _min）
    new_folder_name = f"{folder.name}_min"
    new_folder = folder.parent / new_folder_name
    
    # 新しいフォルダが既に存在する場合は確認
    if new_folder.exists():
        overwrite = input(f"警告: フォルダ '{new_folder}' は既に存在します。上書きしますか？ (y/n): ")
        if overwrite.lower() != 'y':
            print("処理を中止しました。")
            return 0, 0, None
        
        # 古いフォルダを削除
        shutil.rmtree(new_folder)
    
    # 新しいフォルダを作成
    new_folder.mkdir(parents=True, exist_ok=True)
    
    # 処理したファイル数とエラーが発生したファイル数をカウント
    processed = 0
    errors = 0
    
    # JSONファイルのリストを取得
    json_files = list(folder.glob('**/*.json'))
    total_files = len(json_files)
    
    if total_files == 0:
        print(f"警告: フォルダ '{folder}' にJSONファイルが見つかりませんでした。")
        return 0, 0, new_folder
    
    print(f"合計 {total_files} 個のJSONファイルを処理します...")
    
    # 各JSONファイルを処理
    for i, json_file in enumerate(json_files, 1):
        # 進捗表示
        print(f"処理中: {i}/{total_files} - {json_file.name}", end='\r')
        
        # 相対パスを計算
        rel_path = json_file.relative_to(folder)
        
        # 出力先のパスを構築
        output_file = new_folder / rel_path
        
        # 必要なディレクトリを作成
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # ファイルを処理
        success = minify_json_file(json_file, output_file)
        
        if success:
            processed += 1
        else:
            errors += 1
    
    print("\n処理が完了しました。")
    return processed, errors, new_folder


def main():
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description='JSONファイルをインデントなしの形式に変換するスクリプト')
    parser.add_argument('target_folder', help='JSONファイルが格納されているフォルダのパス')
    args = parser.parse_args()
    
    # 処理を実行
    processed, errors, new_folder = process_folder(args.target_folder)
    
    # 結果を表示
    if new_folder:
        print(f"結果: {processed} ファイルを処理しました。エラー数: {errors}")
        print(f"圧縮されたJSONファイルは '{new_folder}' に保存されました。")
        
        # 圧縮率の計算（フォルダサイズの比較）
        original_size = sum(f.stat().st_size for f in Path(args.target_folder).glob('**/*.json'))
        new_size = sum(f.stat().st_size for f in new_folder.glob('**/*.json'))
        
        if original_size > 0:
            ratio = (1 - new_size / original_size) * 100
            print(f"圧縮率: {ratio:.2f}% (元のサイズ: {original_size/1024:.2f} KB, 新しいサイズ: {new_size/1024:.2f} KB)")
    
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main()) 