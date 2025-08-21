# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project maintains location coordinate data for major facilities in Chiyoda City, Tokyo. The data is provided as JSON files accessible via CDN and includes facilities both with and without accessibility via the Chiyoda City welfare transportation service "Kazaguruma" (風ぐるま).

## Development Environment

### Virtual Environment Setup
```bash
# Activate virtual environment
venv\Scripts\activate    # Windows
source venv/bin/activate # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Dependencies
- pandas==2.2.3
- geopy==2.4.1

## Main Commands

### Full Processing Pipeline (Windows)
```bash
# Run complete process: facilities filtering + JSON minification
run_process.bat
```

### Individual Scripts

#### Distance Check and Filtering
```bash
# Filter facilities within 600m of Kazaguruma stops
python src/facilities_check.py
```

#### JSON Minification
```bash
# Create minified versions for distribution
python src/json_minifier.py json
python src/json_minifier.py kazaguruma_json
```

#### Data Conversion Scripts
```bash
# Convert OSM data to standardized format
python src/transform_json.py

# Convert nursery CSV data to JSON format  
python src/convert_nursery_data.py
```

## Data Architecture

### Core Data Structure

**Directory Layout:**
- `json/` - All major facilities for Chiyoda residents
- `kazaguruma_json/` - Facilities accessible within 600m of Kazaguruma stops
- `json_min/` & `kazaguruma_json_min/` - Minified versions for CDN distribution
- `img/` - 600x450 webp images organized by category

**Data Files:**
- `main_facilities.json` - Essential facilities in simplified format
- `key_locations.json` - Comprehensive locations with detailed metadata

### JSON Schemas

**main_facilities.json format:**
```json
[{
  "category": "カテゴリ名",
  "locations": [{
    "name": "施設名",
    "name:en": "Facility name", 
    "lat": 緯度,
    "lng": 経度,
    "copyright": "© データ作者",
    "licence": "ライセンス",
    "licenceUri": "ライセンスURI"
  }]
}]
```

**key_locations.json format:**
```json
[{
  "category": "カテゴリ名（必須）",
  "category:en": "英語カテゴリ名",
  "locations": [{
    "id": "uuid4（必須）",
    "name": "施設名（必須）",
    "name:en": "Facility name",
    "description": "説明（nullを許容）",
    "descriptionCopyright": "© 説明の作者",
    "imageUri": "写真のURI（nullを許容）",
    "imageCopyright": "© 写真の作者",
    "uri": "URI（nullを許容）",
    "lat": 緯度（必須）,
    "lng": 経度（必須）,
    "nodeCopyright": "© 座標の作者（必須）",
    "nodeSourceId": "提供元のid（nullを許容）",
    "licence": "ライセンス（必須）",
    "licenceUri": "ライセンスURI（必須）"
  }]
}]
```

## Core Processing Logic

### Distance Filtering (facilities_check.py)
- Uses geopy.distance.geodesic for accurate distance calculations
- Filters facilities within 600m radius of Kazaguruma bus stops
- Reads bus stop coordinates from `stops.txt` CSV file
- Preserves all original facility metadata during filtering

### JSON Transformation (transform_json.py) 
- Converts OSM data from `.temp/filtered/` directory
- Generates UUIDs for new facilities
- Prevents duplicate entries using nodeSourceId tracking
- Merges new data with existing JSON files

### Data Minification (json_minifier.py)
- Removes indentation and whitespace for CDN distribution
- Creates `*_min` folders with compressed versions
- Calculates and reports compression ratios

## Key Configuration

- **WARNING_DISTANCE**: 600 meters (used for Kazaguruma accessibility filtering)
- **Image Format**: 600x450 WebP images
- **Coordinate System**: WGS84 (lat/lng decimal degrees)
- to memrize