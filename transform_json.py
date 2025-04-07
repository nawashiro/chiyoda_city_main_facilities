import json
import os
import glob
import uuid

def transform_data():
    # 仮想環境のアクティベート
    activate_venv()
    
    # 入力ディレクトリから全JSONファイルを取得
    input_dir = './.temp/filtered'
    output_file = './json/key_locations.json'
    json_files = glob.glob(os.path.join(input_dir, '*.json'))
    
    # 既存のJSONファイルを読み込む（存在する場合）
    existing_data = []
    existing_nodes = set()  # 既存のnodeSourceIdを格納するセット
    
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                
            # 既存のnodeSourceIdをセットに追加
            for category in existing_data:
                for location in category.get('locations', []):
                    node_id = location.get('nodeSourceId')
                    if node_id:
                        existing_nodes.add(node_id)
            
            print(f"既存のデータから{len(existing_nodes)}件のnodeSourceIdを読み込みました")
        except Exception as e:
            print(f"  警告: 既存ファイルの読み込みに失敗しました: {e}")
            existing_data = []
    
    # 結果を格納する辞書（または既存のデータ）
    result = existing_data if existing_data else []
    
    # カテゴリ名からカテゴリオブジェクトへのマッピング
    category_map = {cat.get('category'): cat for cat in result}
    
    # 追加された施設の数
    total_added = 0
    
    # 各ファイルを処理
    for file_path in json_files:
        # カテゴリ名をファイル名から取得（拡張子を除く）
        category = os.path.splitext(os.path.basename(file_path))[0]
        print(f"処理中: {category}")
        
        # JSONファイルを読み込む
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  エラー: {file_path}の読み込みに失敗しました: {e}")
            continue
        
        # 追加する施設のリスト
        new_locations = []
        
        # 各要素を処理
        for element in data.get('elements', []):
            element_type = element.get('type')
            
            # node, way, relationを処理
            if (element_type == 'node' or element_type == 'way' or element_type == 'relation') and 'tags' in element:
                tags = element.get('tags', {})
                name = tags.get('name')
                
                # 名前がない場合はスキップ
                if not name:
                    continue
                
                # 要素IDの取得
                element_id = element.get('id')
                
                # 既に存在する場合はスキップ
                if element_id in existing_nodes:
                    continue
                
                # 座標の取得 (タイプによって異なる場所から取得)
                lat = None
                lng = None
                if element_type == 'node':
                    lat = element.get('lat')
                    lng = element.get('lon')
                elif (element_type == 'way' or element_type == 'relation') and 'center' in element:
                    center = element.get('center', {})
                    lat = center.get('lat')
                    lng = center.get('lon')
                
                # 座標がない場合はスキップ
                if lat is None or lng is None:
                    print(f"  警告: 座標が見つかりません: {name}")
                    continue
                
                # 基本ロケーション情報
                location = {
                    'id': str(uuid.uuid4()),  # UUIDを生成
                    'name': name,
                    'description': None,
                    'descriptionCopyright': None,  # 説明がないのでnull
                    'imageUri': None,
                    'imageCopyright': None,  # 画像がないのでnull
                    'uri': None,
                    'lat': lat,
                    'lng': lng,
                    'nodeCopyright': "© OpenStreetMap contributors",
                    'nodeSourceId': element_id,
                    'licence': "Open Database License (ODbL) 1.0",
                    'licenceUri': "https://opendatacommons.org/licenses/odbl/"
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
                
                # 新しい施設を追加
                new_locations.append(location)
                existing_nodes.add(element_id)  # 新しく追加したnodeSourceIdを記録
                print(f"  新規施設: {name}, id: {location.get('id')}, nodeSourceId: {location.get('nodeSourceId')}")
        
        # カテゴリごとの追加処理
        if new_locations:
            # 既存のカテゴリに追加するか、新しいカテゴリを作成
            if category in category_map:
                category_map[category]['locations'].extend(new_locations)
            else:
                category_obj = {
                    'category': category,
                    'category:en': category,  # 英語カテゴリ名（仮）
                    'locations': new_locations
                }
                result.append(category_obj)
                category_map[category] = category_obj
            
            total_added += len(new_locations)
            print(f"  {len(new_locations)}件の施設を追加しました")
    
    # 結果をJSONファイルに書き込む
    if total_added > 0:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f'\n{output_file} に変換されたデータを保存しました。全{len(result)}カテゴリ、合計{sum(len(cat["locations"]) for cat in result)}施設が含まれています。')
            print(f'今回の実行で{total_added}件の新規施設が追加されました。')
        except Exception as e:
            print(f"エラー: ファイルの書き込みに失敗しました: {e}")
    else:
        print("\n新たに追加された施設はありませんでした。")

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