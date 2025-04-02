#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pandas as pd
import csv
from geopy.distance import geodesic
from datetime import datetime
import os

# 設定値
WARNING_DISTANCE = 600  # メートル

def load_address_data(file_path):
    """住所データをJSONファイルから読み込む"""
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

def export_to_csv(results, filename):
    """結果をCSVファイルに出力する"""
    # 出力ディレクトリを確認し、存在しなければ作成
    output_dir = os.path.dirname(filename)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"ディレクトリ {output_dir} を作成しました")
        
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['カテゴリー', '施設名', '最寄り停留所', '距離(m)', 'ステータス'])
        for row in results:
            writer.writerow(row)
    print(f"結果を {filename} に出力しました")

def main():
    # データの読み込み
    try:
        address_data = load_address_data('json/main_facilities.json')
        stops_df = load_stops_data('stops.txt')
    except Exception as e:
        print(f"データの読み込みに失敗しました: {e}")
        return
    
    print("施設チェック開始...")
    print(f"{WARNING_DISTANCE}m以上離れている施設には警告を表示します")
    print("-" * 80)
    
    # 結果を保存するリスト
    results = []
    
    # 各カテゴリーと施設について最短距離を計算
    warning_count = 0
    for category_data in address_data:
        category = category_data['category']
        print(f"\n【{category}】")
        
        for location in category_data['locations']:
            name = location['name']
            nearest_stop, distance = calculate_min_distance(location, stops_df)
            
            status = "OK"
            if distance >= WARNING_DISTANCE:
                status = "警告"
                warning_count += 1
            
            print(f"  {name}: 最寄り停留所「{nearest_stop}」まで {distance:.1f}m [{status}]")
            
            # 結果をリストに追加
            results.append([category, name, nearest_stop, f"{distance:.1f}", status])
    
    print("\n" + "-" * 80)
    print(f"チェック完了: {warning_count}件の警告があります")
    
    # 結果をCSVファイルに出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output/facilities_check_result_{timestamp}.csv"
    export_to_csv(results, filename)

if __name__ == "__main__":
    main() 