"""
車種データベース管理ツール (SQLite)

使い方:
    python manage_cars.py list                    # 全車種一覧表示
    python manage_cars.py search "ランドクルーザー"  # 車名で検索
    python manage_cars.py show 5                  # ID指定で詳細表示
    python manage_cars.py add --name "新型XX" --glb "xx.glb" \
        --length 4500 --width 1800 --height 1500 \
        --ground-clearance 150 --turning-radius 5200 \
        --acceleration 9.5 --rotation 0           # 新規追加
    python manage_cars.py edit 5 --length 4600    # ID指定で修正
    python manage_cars.py delete 5                # ID指定で削除
    python manage_cars.py import-csv cars.csv     # CSVから一括インポート
    python manage_cars.py export-csv backup.csv   # CSVエクスポート
"""

import argparse
import sqlite3
import csv
import os
import sys

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cars.db")


def get_connection():
    """データベース接続を取得"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """データベース初期化 (テーブル作成)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            glb_filename TEXT NOT NULL UNIQUE,
            length INTEGER NOT NULL,
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            ground_clearance INTEGER DEFAULT 0,
            turning_radius INTEGER DEFAULT 0,
            acceleration_0_to_100 REAL DEFAULT 0.0,
            rotation_direction INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def list_cars():
    """全車種一覧表示"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cars ORDER BY id")
    rows = cursor.fetchall()

    print(f"{'ID':>3} | {'車名':<20} | {'GLBファイル':<25} | {'全長':>5} | {'全幅':>5} | {'全高':>5}")
    print("-" * 85)
    for row in rows:
        print(f"{row['id']:>3} | {row['name']:<20} | {row['glb_filename']:<25} | {row['length']:>5} | {row['width']:>5} | {row['height']:>5}")

    print(f"\n合計: {len(rows)} 台")
    conn.close()


def search_cars(query):
    """車名で部分一致検索"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cars WHERE name LIKE ? ORDER BY id", (f"%{query}%",))
    rows = cursor.fetchall()

    if not rows:
        print(f"「{query}」に一致する車種が見つかりませんでした。")
        conn.close()
        return

    print(f"検索結果: 「{query}」に一致する {len(rows)} 台")
    print(f"{'ID':>3} | {'車名':<20} | {'GLBファイル':<25} | {'全長':>5} | {'全幅':>5} | {'全高':>5}")
    print("-" * 85)
    for row in rows:
        print(f"{row['id']:>3} | {row['name']:<20} | {row['glb_filename']:<25} | {row['length']:>5} | {row['width']:>5} | {row['height']:>5}")

    conn.close()


def add_car(args):
    """新規車種追加"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO cars (name, glb_filename, length, width, height,
                             ground_clearance, turning_radius,
                             acceleration_0_to_100, rotation_direction)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (args.name, args.glb, args.length, args.width, args.height,
              args.ground_clearance, args.turning_radius,
              args.acceleration, args.rotation))
        conn.commit()
        new_id = cursor.lastrowid
        print(f"✓ 車種を追加しました (ID: {new_id}) - {args.name}")
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed" in str(e):
            print(f"✗ エラー: GLBファイル名 '{args.glb}' は既に登録されています。")
        else:
            print(f"✗ エラー: {e}")
    finally:
        conn.close()


def edit_car(car_id, args):
    """車種情報修正"""
    conn = get_connection()
    cursor = conn.cursor()

    # 対象が存在するか確認
    cursor.execute("SELECT * FROM cars WHERE id = ?", (car_id,))
    existing = cursor.fetchone()
    if not existing:
        print(f"✗ エラー: ID {car_id} の車種が見つかりませんでした。")
        conn.close()
        return

    # 修正するフィールドを動的に構築
    updates = []
    values = []

    field_map = [
        ("name", "name"),
        ("glb", "glb_filename"),
        ("length", "length"),
        ("width", "width"),
        ("height", "height"),
        ("ground_clearance", "ground_clearance"),
        ("turning_radius", "turning_radius"),
        ("acceleration", "acceleration_0_to_100"),
        ("rotation", "rotation_direction"),
    ]

    for attr_name, db_column in field_map:
        attr_value = getattr(args, attr_name, None)
        if attr_value is not None:
            updates.append(f"{db_column} = ?")
            values.append(attr_value)

    if not updates:
        print("修正するフィールドを指定してください。")
        conn.close()
        return

    # glb_filename の変更時はUNIQUE制約をチェック
    if "glb_filename = ?" in updates:
        glb_idx = updates.index("glb_filename = ?")
        new_glb = values[glb_idx]
        cursor.execute(
            "SELECT id FROM cars WHERE glb_filename = ? AND id != ?",
            (new_glb, car_id)
        )
        if cursor.fetchone():
            print(f"✗ エラー: GLBファイル名 '{new_glb}' は既に他の車種で使用されています。")
            conn.close()
            return

    values.append(car_id)
    try:
        cursor.execute(f"UPDATE cars SET {', '.join(updates)} WHERE id = ?", values)
        conn.commit()
        print(f"✓ 車種 ID {car_id} の情報を修正しました。")
    except sqlite3.IntegrityError as e:
        print(f"✗ エラー: {e}")
    finally:
        conn.close()


def delete_car(car_id):
    """車種削除"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM cars WHERE id = ?", (car_id,))
    existing = cursor.fetchone()
    if not existing:
        print(f"✗ エラー: ID {car_id} の車種が見つかりませんでした。")
        conn.close()
        return

    cursor.execute("DELETE FROM cars WHERE id = ?", (car_id,))
    conn.commit()
    print(f"✓ 車種「{existing['name']}」(ID: {car_id}) を削除しました。")
    conn.close()


def show_car(car_id):
    """車種の詳細を表示"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cars WHERE id = ?", (car_id,))
    row = cursor.fetchone()

    if not row:
        print(f"✗ エラー: ID {car_id} の車種が見つかりませんでした。")
        conn.close()
        return

    print(f"\n=== 車種詳細 (ID: {row['id']}) ===")
    print(f"  車名:             {row['name']}")
    print(f"  GLBファイル:      {row['glb_filename']}")
    print(f"  全長:             {row['length']} mm")
    print(f"  全幅:             {row['width']} mm")
    print(f"  全高:             {row['height']} mm")
    print(f"  最低地上高:       {row['ground_clearance']} mm")
    print(f"  最小回転半径:     {row['turning_radius']} mm")
    print(f"  0-100km/h加速:   {row['acceleration_0_to_100']} 秒")
    print(f"  Z軸回転角度:      {row['rotation_direction']} 度")

    conn.close()


def import_from_csv(csv_path):
    """CSVから一括インポート"""
    if not os.path.exists(csv_path):
        print(f"✗ エラー: CSVファイル '{csv_path}' が見つかりませんでした。")
        return

    conn = get_connection()
    cursor = conn.cursor()
    imported = 0
    skipped = 0
    errors = 0

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 空行をスキップ
            if not row.get("name", "").strip():
                continue
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO cars
                    (id, name, glb_filename, length, width, height,
                     ground_clearance, turning_radius,
                     acceleration_0_to_100, rotation_direction)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    int(row["id"]),
                    row["name"],
                    row["glb_filename"],
                    int(row["length"]),
                    int(row["width"]),
                    int(row["height"]),
                    int(row["ground_clearance"]),
                    int(row["turning_radius"]),
                    float(row["acceleration_0_to_100"]),
                    int(row["rotation_direction"])
                ))
                if cursor.rowcount > 0:
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  ⚠ 行 {row.get('id', '?')} のインポートに失敗: {e}")
                errors += 1

    conn.commit()
    print(f"✓ インポート完了: {imported} 台追加, {skipped} 台スキップ (既存), {errors} 件エラー")
    conn.close()


def export_to_csv(output_path):
    """CSVエクスポート"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cars ORDER BY id")
    rows = cursor.fetchall()

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "name", "glb_filename", "length", "width", "height",
                         "ground_clearance", "turning_radius",
                         "acceleration_0_to_100", "rotation_direction"])
        for row in rows:
            writer.writerow([row["id"], row["name"], row["glb_filename"],
                            row["length"], row["width"], row["height"],
                            row["ground_clearance"], row["turning_radius"],
                            row["acceleration_0_to_100"], row["rotation_direction"]])

    print(f"✓ CSVエクスポート完了: {output_path} ({len(rows)} 台)")
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="車種データベース管理ツール (SQLite)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python manage_cars.py list
  python manage_cars.py search "ランドクルーザー"
  python manage_cars.py show 5
  python manage_cars.py add --name "新型XX" --glb "xx.glb" --length 4500 --width 1800 --height 1500
  python manage_cars.py edit 5 --length 4600
  python manage_cars.py delete 5
  python manage_cars.py import-csv cars.csv
  python manage_cars.py export-csv backup.csv
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # list
    subparsers.add_parser("list", help="全車種一覧表示")

    # search
    search_parser = subparsers.add_parser("search", help="車名で検索")
    search_parser.add_argument("query", type=str, help="検索キーワード")

    # add
    add_parser = subparsers.add_parser("add", help="新規車種追加")
    add_parser.add_argument("--name", required=True, help="車名")
    add_parser.add_argument("--glb", required=True, help="GLBファイル名")
    add_parser.add_argument("--length", type=int, required=True, help="全長 (mm)")
    add_parser.add_argument("--width", type=int, required=True, help="全幅 (mm)")
    add_parser.add_argument("--height", type=int, required=True, help="全高 (mm)")
    add_parser.add_argument("--ground-clearance", type=int, default=0, help="最低地上高 (mm)")
    add_parser.add_argument("--turning-radius", type=int, default=0, help="最小回転半径 (mm)")
    add_parser.add_argument("--acceleration", type=float, default=0.0, help="0-100km/h加速時間 (秒)")
    add_parser.add_argument("--rotation", type=int, default=0, help="Z軸回転角度 (度)")

    # edit
    edit_parser = subparsers.add_parser("edit", help="車種情報修正")
    edit_parser.add_argument("id", type=int, help="修正対象のID")
    edit_parser.add_argument("--name", default=None, help="車名")
    edit_parser.add_argument("--glb", default=None, help="GLBファイル名")
    edit_parser.add_argument("--length", type=int, default=None, help="全長 (mm)")
    edit_parser.add_argument("--width", type=int, default=None, help="全幅 (mm)")
    edit_parser.add_argument("--height", type=int, default=None, help="全高 (mm)")
    edit_parser.add_argument("--ground-clearance", type=int, default=None, help="最低地上高 (mm)")
    edit_parser.add_argument("--turning-radius", type=int, default=None, help="最小回転半径 (mm)")
    edit_parser.add_argument("--acceleration", type=float, default=None, help="0-100km/h加速時間 (秒)")
    edit_parser.add_argument("--rotation", type=int, default=None, help="Z軸回転角度 (度)")

    # delete
    delete_parser = subparsers.add_parser("delete", help="車種削除")
    delete_parser.add_argument("id", type=int, help="削除対象のID")

    # show
    show_parser = subparsers.add_parser("show", help="車種詳細表示")
    show_parser.add_argument("id", type=int, help="表示対象のID")

    # import-csv
    import_parser = subparsers.add_parser("import-csv", help="CSVから一括インポート")
    import_parser.add_argument("csv_path", type=str, help="インポート元CSVファイルパス")

    # export-csv
    export_parser = subparsers.add_parser("export-csv", help="CSVエクスポート")
    export_parser.add_argument("output_path", type=str, help="出力先CSVファイルパス")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # データベース初期化
    init_db()

    # コマンド実行
    if args.command == "list":
        list_cars()
    elif args.command == "search":
        search_cars(args.query)
    elif args.command == "add":
        add_car(args)
    elif args.command == "edit":
        edit_car(args.id, args)
    elif args.command == "delete":
        delete_car(args.id)
    elif args.command == "show":
        show_car(args.id)
    elif args.command == "import-csv":
        import_from_csv(args.csv_path)
    elif args.command == "export-csv":
        export_to_csv(args.output_path)


if __name__ == "__main__":
    main()
