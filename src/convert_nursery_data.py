#!/usr/bin/env python
# -*- coding: utf-8 -*-

import csv
import json
import os
import uuid
import sys
from pathlib import Path

def read_csv_file(file_path):
    """CSVファイルを読み込む関数"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data

def read_json_file(file_path):
    """JSONファイルを読み込む関数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_json_file(file_path, data):
    """JSONファイルを保存する関数"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, ensure_ascii=False, indent=2, fp=f)

def convert_nursery_data(csv_data):
    """保育所データを変換する関数"""
    locations = []
    
    # 決め打ちする値
    description_copyright = "© 東京都福祉局"
    node_copyright = "© 東京都福祉局"
    licence = "CC BY"
    licence_uri = "https://creativecommons.org/licenses/by/4.0/"
    
    for row in csv_data:
        # 必要なデータを取得
        name = row.get('施設名', '')
        lat = float(row.get('緯度', 0))
        lng = float(row.get('経度', 0))
        address = row.get('所在地', '')
        postal_code = row.get('郵便番号', '')
        phone = row.get('電話番号', '')
        capacity = row.get('認可定員', '')
        
        # description の作成
        description_parts = []
        if phone:
            description_parts.append(f"電話番号：{phone}")
        if capacity:
            description_parts.append(f"認可定員：{capacity}名")
        
        description = "、".join(description_parts) if description_parts else None
        
        # 施設情報を作成
        location = {
            "id": str(uuid.uuid4()),
            "name": name,
            "description": description,
            "descriptionCopyright": description_copyright if description else None,
            "imageUri": None,
            "imageCopyright": None,
            "uri": None,
            "lat": lat,
            "lng": lng,
            "nodeCopyright": node_copyright,
            "nodeSourceId": None,
            "licence": licence,
            "licenceUri": licence_uri
        }
        
        locations.append(location)
    
    return locations

def main():
    # CSVファイルのパス
    csv_file = Path('.temp/csv/保育所.csv')
    
    # JSONファイルのパス
    json_file = Path('json/key_locations.json')
    
    print("保育所データを key_locations.json に追加します。")
    
    # CSVデータを読み込む
    try:
        csv_data = read_csv_file(csv_file)
    except Exception as e:
        print(f"CSVファイルの読み込みに失敗しました: {e}")
        sys.exit(1)
    
    # JSONデータを読み込む
    try:
        json_data = read_json_file(json_file)
    except Exception as e:
        print(f"JSONファイルの読み込みに失敗しました: {e}")
        sys.exit(1)
    
    # 保育所データを変換
    nursery_locations = convert_nursery_data(csv_data)
    
    # 保育所カテゴリが既に存在するか確認
    nursery_category_exists = False
    for category in json_data:
        if category.get("category") == "保育所":
            # 既存のカテゴリに追加
            print(f"既存の保育所カテゴリに {len(nursery_locations)} 件の施設を追加します。")
            category["locations"].extend(nursery_locations)
            nursery_category_exists = True
            break
    
    # カテゴリが存在しなければ新規作成
    if not nursery_category_exists:
        print(f"新しい保育所カテゴリを作成し、{len(nursery_locations)} 件の施設を追加します。")
        nursery_category = {
            "category": "保育所",
            "category:en": "nursery",
            "locations": nursery_locations
        }
        json_data.append(nursery_category)
    
    # JSONファイルを保存
    try:
        save_json_file(json_file, json_data)
        print(f"保育所データを {json_file} に保存しました。")
    except Exception as e:
        print(f"JSONファイルの保存に失敗しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 