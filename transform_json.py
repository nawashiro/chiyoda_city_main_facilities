import json
import os
import glob

def transform_data():
    # 仮想環境のアクティベート
    activate_venv()
    
    # 入力ディレクトリから全JSONファイルを取得
    input_dir = './.temp/filtered'
    output_file = './json/key_locations.json'
    json_files = glob.glob(os.path.join(input_dir, '*.json'))
    
    # 結果を格納する辞書
    result = []
    
    # 各ファイルを処理
    for file_path in json_files:
        # カテゴリ名をファイル名から取得（拡張子を除く）
        category = os.path.splitext(os.path.basename(file_path))[0]
        
        # JSONファイルを読み込む
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # カテゴリごとのロケーションリスト
        locations = []
        
        # 各要素を処理
        for element in data.get('elements', []):
            if element.get('type') == 'node' and 'tags' in element:
                tags = element.get('tags', {})
                name = tags.get('name')
                
                # 名前がない場合はスキップ
                if not name:
                    continue
                
                # 基本ロケーション情報
                location = {
                    'name': name,
                    'description': None,
                    'imageUri': None,
                    'imageCopylight': None,
                    'uri': None,
                    'lat': element.get('lat'),
                    'lng': element.get('lon')
                }
                
                # 他言語の名前を追加
                for key, value in tags.items():
                    if key.startswith('name:'):
                        location[key] = value
                
                # URLがある場合は追加
                if 'website' in tags:
                    location['uri'] = tags.get('website')
                elif 'contact:website' in tags:
                    location['uri'] = tags.get('contact:website')
                
                locations.append(location)
        
        # カテゴリとロケーションを結果に追加（ロケーションが空でない場合）
        if locations:
            result.append({
                'category': category,
                'locations': locations
            })
    
    # 結果をJSONファイルに書き込む
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f'{output_file} に変換されたデータを保存しました。')

def activate_venv():
    """仮想環境をアクティベートする"""
    venv_path = os.path.join(os.getcwd(), 'venv')
    if os.name == 'nt':  # Windows
        activate_script = os.path.join(venv_path, 'Scripts', 'activate.bat')
        os.system(f'call "{activate_script}"')
    else:  # Linux/Mac
        activate_script = os.path.join(venv_path, 'bin', 'activate')
        os.system(f'source "{activate_script}"')

if __name__ == '__main__':
    transform_data() 