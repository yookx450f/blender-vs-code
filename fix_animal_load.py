"""Helper script to add animal loading functions to blend_scene_creator.py"""

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
target_file = os.path.join(SCRIPT_DIR, "blend_scene_creator.py")

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add load_animals_db and load_animals_config functions before load_cars_config
new_functions = '''def load_animals_db():
    """SQLiteデータベース (cars.db) から動物マスターデータを辞書として読み込む"""
    db_path = os.path.join(SCRIPT_DIR, "cars.db")
    
    if not os.path.exists(db_path):
        print(f"エラー: データベースが見つかりません - {db_path}")
        sys.exit(1)
    
    animals_db = {}
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # animalsテーブルが存在するか確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='animals'")
        if not cursor.fetchone():
            print("エラー: animals テーブルが見つかりません")
            print("pages/01_動物一覧.py で動物データを登録してください。")
            conn.close()
            sys.exit(1)
        
        cursor.execute("SELECT * FROM animals")
        
        for row in cursor.fetchall():
            animal_id = str(row["id"])
            animals_db[animal_id] = {
                "name": row["name"],
                "glb_filename": row["glb_filename"],
                "animal_type": row.get("animal_type", "other"),
                "height": row.get("height", 0),
                "weight": row.get("weight", 0),
                "rotation_direction": row.get("rotation_direction", 0),
                "color_name": row.get("color_name", "グレー")
            }
        
        conn.close()
        print(f"動物マスターDBを読み込みました: {db_path} ({len(animals_db)} 種類)")
    except Exception as e:
        print(f"エラー: animals テーブルの読み込みに失敗しました - {e}")
        sys.exit(1)
    
    return animals_db


def load_animals_config():
    """animals_config.json + cars.db(animalsテーブル) を結合して動物の設定辞書を返す
    
    JSONでは animalA/animalB に id, color, position のみを指定し、
    寸法データは DBからidで自動的に取得・結合する。
    戻り値のキーは carA/carB に変換（アニメーション設定との互換性）。
    """
    config_path = os.path.join(SCRIPT_DIR, "animals_config.json")
    
    if not os.path.exists(config_path):
        print(f"エラー: 設定ファイルが見つかりません - {config_path}")
        print("animals_config.json を作成してください。")
        sys.exit(1)
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # DBから動物マスターデータを取得
        animals_db = load_animals_db()
        
        # GLBディレクトリの取得（JSONのグローバル設定）
        glb_dir = config.get("glb_dir", "")
        
        # animalA/animalB ごとにDBデータを結合し、carA/carB キーに変換
        key_mapping = {"animalA": "carA", "animalB": "carB"}
        merged = {}
        for src_key, dst_key in key_mapping.items():
            if src_key not in config:
                continue
            
            animal_cfg = config[src_key]
            animal_id = animal_cfg.get("id", "")
            
            if animal_id not in animals_db:
                print(f"エラー: DBに動物ID '{animal_id}' が見つかりません")
                print(f"  利用可能なID: {', '.join(animals_db.keys())}")
                sys.exit(1)
            
            db_data = animals_db[animal_id]
            merged[dst_key] = {
                "name": db_data["name"],
                "glb_path": os.path.join(glb_dir, db_data["glb_filename"]),
                "position": tuple(animal_cfg.get("position", [0.0, 0.0, 0])),
                "color": tuple(animal_cfg.get("color", [0.5, 0.5, 0.5])),
                "dimensions_mm": {
                    "height": db_data["height"],
                    "weight": db_data["weight"],
                },
                "rotation_z_degrees": db_data["rotation_direction"]
            }
        
        print(f"動物設定ファイルを読み込みました: {config_path}")
        for key, animal_data in merged.items():
            dims = animal_data.get("dimensions_mm", {})
            src_key = "animalA" if key == "carA" else "animalB"
            print(f"  - {key}: {animal_data['name']} (ID: {config[src_key].get('id', '?')})")
            print(f"    GLBパス: {animal_data['glb_path']}")
            print(f"    寸法: 全高{dims.get('height', '?')}mm, 体重{dims.get('weight', '?')}kg")
        
        return merged
    
    except json.JSONDecodeError as e:
        print(f"エラー: animals_config.json の形式が正しくありません - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"エラー: 動物設定ファイルの読み込みに失敗しました - {e}")
        sys.exit(1)


'''

# Insert before "def load_cars_config():"
insert_marker = "\ndef load_cars_config():\n"
if insert_marker in content:
    content = content.replace(insert_marker, new_functions + insert_marker, 1)
    print("Added animal loading functions")
else:
    print("ERROR: Could not find insertion point")
    exit(1)

# 2. Change main() to conditionally load animals config
old_load_line = '    CARS = load_cars_config()'
new_load_block = '''    # shortAnimal モードは animals_config.json を使用
    if CUT_NUMBER == "shortAnimal":
        CARS = load_animals_config()
    else:
        CARS = load_cars_config()'''

if old_load_line in content:
    content = content.replace(old_load_line, new_load_block, 1)
    print("Modified main() to conditionally load animal config")
else:
    print("ERROR: Could not find CARS = load_cars_config() line")
    exit(1)

with open(target_file, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully modified {target_file}")
