import json
import os
from collections import defaultdict
from typing import Dict, List, Set


def count_images_by_category_from_json(data: List[Dict]) -> Dict[str, int]:
    """JSONデータから各カテゴリの画像数をカウント（imageUriフィールドがあるものを数える）"""
    image_counts = defaultdict(int)
    
    for category_data in data:
        category = category_data.get('category', 'Unknown')
        locations = category_data.get('locations', [])
        
        # imageUriフィールドがあり、かつNullでない要素をカウント
        image_count = 0
        for location in locations:
            if location.get('imageUri'):
                image_count += 1
        
        image_counts[category] = image_count
    
    return dict(image_counts)


def analyze_json_file(file_path: str) -> Dict[str, Dict]:
    """JSONファイルを解析して統計情報を取得"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    stats = {}
    
    for category_data in data:
        category = category_data.get('category', 'Unknown')
        locations = category_data.get('locations', [])
        location_count = len(locations)
        
        # key_locations.jsonの場合は画像数も集計
        if locations and 'id' in locations[0]:
            # key_locations.json format
            image_count = 0
            for location in locations:
                if location.get('imageUri'):
                    image_count += 1
            stats[category] = {
                'locations': location_count,
                'images': image_count
            }
        else:
            # main_facilities.json format
            stats[category] = {
                'locations': location_count
            }
    
    return stats


def extract_licenses(file_path: str) -> Set[tuple]:
    """JSONファイルからライセンス情報を抽出し、不一致を報告"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    licenses = set()
    license_uri_mapping = {}
    
    for category_data in data:
        locations = category_data.get('locations', [])
        for location in locations:
            copyright_text = location.get('copyright', location.get('nodeCopyright', ''))
            license_name = location.get('licence', '')
            license_uri = location.get('licenceUri', '')
            
            if copyright_text and license_name:
                # ライセンス名とURIの一致を検証
                if license_name in license_uri_mapping:
                    if license_uri_mapping[license_name] != license_uri:
                        print(f"警告: ライセンス名 '{license_name}' に対して複数の異なるURIが見つかりました:")
                        print(f"  既存URI: {license_uri_mapping[license_name]}")
                        print(f"  新しいURI: {license_uri}")
                        print(f"  ファイル: {file_path}")
                        print(f"  場所: {location.get('name', 'Unknown')}")
                        print()
                else:
                    license_uri_mapping[license_name] = license_uri
                
                licenses.add((copyright_text, license_name, license_uri))
    
    return licenses


def validate_license_consistency() -> None:
    """全ファイルのライセンス一貫性をチェック"""
    print("=== ライセンス一貫性チェック開始 ===\n")

def generate_release_notes(json_dir: str, kazaguruma_json_dir: str) -> str:
    """リリースノートを生成"""
    validate_license_consistency()
    
    release_notes = "このバージョンには以下の内容が含まれます。\n\n"
    
    # json section
    release_notes += "## json\n\n"
    
    # main_facilities.json
    main_facilities_path = os.path.join(json_dir, 'main_facilities.json')
    if os.path.exists(main_facilities_path):
        stats = analyze_json_file(main_facilities_path)
        release_notes += "### main_facilities.json\n\n"
        release_notes += "|分類|座標件数|\n"
        release_notes += "|---|---|\n"
        for category, data in stats.items():
            release_notes += f"|{category}|{data['locations']}|\n"
        release_notes += "\n"
    
    # key_locations.json
    key_locations_path = os.path.join(json_dir, 'key_locations.json')
    if os.path.exists(key_locations_path):
        stats = analyze_json_file(key_locations_path)
        release_notes += "### key_locations.json\n\n"
        release_notes += "|分類|座標件数|写真件数|\n"
        release_notes += "|---|---|---|\n"
        for category, data in stats.items():
            locations = data['locations']
            images = data.get('images', 0)
            release_notes += f"|{category}|{locations}|{images}|\n"
        release_notes += "\n"
    
    # kazaguruma_json section
    release_notes += "## kazaguruma_json\n\n"
    
    # kazaguruma main_facilities.json
    kazaguruma_main_path = os.path.join(kazaguruma_json_dir, 'main_facilities.json')
    if os.path.exists(kazaguruma_main_path):
        stats = analyze_json_file(kazaguruma_main_path)
        release_notes += "### main_facilities.json\n\n"
        release_notes += "|分類|座標件数|\n"
        release_notes += "|---|---|\n"
        for category, data in stats.items():
            release_notes += f"|{category}|{data['locations']}|\n"
        release_notes += "\n"
    
    # kazaguruma key_locations.json
    kazaguruma_key_path = os.path.join(kazaguruma_json_dir, 'key_locations.json')
    if os.path.exists(kazaguruma_key_path):
        stats = analyze_json_file(kazaguruma_key_path)
        release_notes += "### key_locations.json\n\n"
        release_notes += "|分類|座標件数|写真件数|\n"
        release_notes += "|---|---|---|\n"
        for category, data in stats.items():
            locations = data['locations']
            images = data.get('images', 0)
            release_notes += f"|{category}|{locations}|{images}|\n"
        release_notes += "\n"
    
    # ライセンス情報
    all_licenses = set()
    
    for json_file in [main_facilities_path, key_locations_path, 
                      kazaguruma_main_path, kazaguruma_key_path]:
        if os.path.exists(json_file):
            all_licenses.update(extract_licenses(json_file))
    
    if all_licenses:
        release_notes += "## 含まれるライセンス\n\n"
        release_notes += "|作者|ライセンス|\n"
        release_notes += "|---|---|\n"
        
        for copyright_text, license_name, license_uri in sorted(all_licenses):
            if license_uri:
                license_link = f"[{license_name}]({license_uri})"
            else:
                license_link = license_name
            release_notes += f"|{copyright_text}|{license_link}|\n"
    
    return release_notes


def main():
    """メイン処理"""
    import sys
    # Windows環境でのUnicodeエラーを回避
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # プロジェクトのルートディレクトリを基準にパスを設定
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_dir = os.path.join(base_dir, 'json')
    kazaguruma_json_dir = os.path.join(base_dir, 'kazaguruma_json')
    
    # リリースノートを生成
    release_notes = generate_release_notes(json_dir, kazaguruma_json_dir)
    
    # 出力
    print(release_notes)
    
    # ファイルに保存
    output_file = os.path.join(base_dir, 'RELEASE_NOTES.md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(release_notes)
    
    print(f"\nリリースノートが {output_file} に保存されました。")


if __name__ == "__main__":
    main()