# 最初の施設変更

このチュートリアルは、既存Placeの公開状態を変更してPull Requestを作る手順です。

## 1. 作業branchを作る

```bash
git clone https://github.com/nawashiro/chiyoda_city_main_facilities.git
cd chiyoda_city_main_facilities
git switch -c data/first-change
```

既存checkoutでは、最初に`git status`と`git pull --ff-only origin main`を実行してください。

## 2. 変更前を検証する

```bash
python3 -m unittest discover -s tests -v
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
git diff --check
```

失敗した場合、データを変更しないでください。

## 3. Placeを確認する

```bash
./fac ls --name <施設名>
./fac get <UUID>
```

`./fac get`でカテゴリ、タグ、公開状態を確認してください。

## 4. 公開状態を変更する

```bash
./fac set <UUID> --vis private
python3 -m src.facility_data validate .
python3 -m src.facility_data build .
```

`private`のPlaceは公開GeoJSONから除外します。

## 5. 差分を確認する

```bash
git diff --check
git diff -- data/registry.json dist/public/
```

正本、公開GeoJSON、manifestだけが意図どおりに変わることを確認してください。

## 6. Pull Requestを作る

```bash
git add data/registry.json dist/public/
git commit -m "data: update facility visibility"
git push -u origin data/first-change
gh pr create
```

対象commitの`Validate data`が成功したことを確認してください。
