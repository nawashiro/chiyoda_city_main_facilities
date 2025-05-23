#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pandas as pd
from geopy.distance import geodesic
import os

# 設定値
WARNING_DISTANCE = 600  # メートル

def load_facilities_data(file_path):
    """施設データをJSONファイルから読み込む"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_stops_data(file_path):
    """停留所データをCSVファイルから読み込む"""
    return pd.read_csv(file_path)

def calculate_min_distance(location, stops_df):
    """ある施設から最も近い停留所とその距離を計算する"""
    min_distance = float('inf')
    nearest_stop = None
    
    loc_coords = (location['lat'], location['lng'])
    
    for _, stop in stops_df.iterrows():
        stop_coords = (stop['stop_lat'], stop['stop_lon'])
        distance = geodesic(loc_coords, stop_coords).meters
        
        if distance < min_distance:
            min_distance = distance
            nearest_stop = stop['stop_name']
    
    return nearest_stop, min_distance

def filter_locations_in_radius(facilities_data, stops_df, max_distance):
    """半径max_distance以内の施設をフィルタリングする"""
    filtered_data = []
    
    for category_data in facilities_data:
        category_dict = {}
        # カテゴリーの全属性をコピー
        for key, value in category_data.items():
            if key != 'locations':
                category_dict[key] = value
        
        filtered_locations = []
        
        for location in category_data['locations']:
            nearest_stop, distance = calculate_min_distance(location, stops_df)
            
            if distance <= max_distance:
                # 元のオブジェクトの全属性を保持
                filtered_locations.append(location.copy())
        
        if filtered_locations:
            category_dict['locations'] = filtered_locations
            filtered_data.append(category_dict)
    
    return filtered_data

def export_to_json(data, filename):
    """結果をJSONファイルに出力する"""
    # 出力ディレクトリを確認し、存在しなければ作成
    output_dir = os.path.dirname(filename)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"ディレクトリ {output_dir} を作成しました")
        
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"結果を {filename} に出力しました")

def process_file(input_file):
    """指定されたJSONファイルを処理する"""
    try:
        facilities_data = load_facilities_data(input_file)
        stops_df = load_stops_data('stops.txt')
    except Exception as e:
        print(f"データの読み込みに失敗しました: {e}")
        return
    
    print(f"\n{input_file} の処理を開始...")
    print(f"{WARNING_DISTANCE}m以内の施設のみを抽出します")
    print("-" * 80)
    
    # 半径WARNING_DISTANCE以内の施設をフィルタリング
    filtered_data = filter_locations_in_radius(facilities_data, stops_df, WARNING_DISTANCE)
    
    # 結果の概要を表示
    total_locations = sum(len(category['locations']) for category in filtered_data)
    print("-" * 80)
    print(f"フィルタリング完了: {total_locations}件の施設が{WARNING_DISTANCE}m圏内にあります")
    
    # 元のファイル名から出力ファイル名を作成
    input_filename = os.path.basename(input_file)
    output_filename = f"kazaguruma_json/{input_filename}"
    export_to_json(filtered_data, output_filename)

def main():
    # 処理するファイルリスト
    files_to_process = [
        'json/main_facilities.json',
        'json/key_locations.json'
    ]
    
    print("施設フィルタリング開始...")
    
    # 各ファイルを処理
    for input_file in files_to_process:
        process_file(input_file)
    
    print("\nすべてのファイルの処理が完了しました")

if __name__ == "__main__":
    main() 