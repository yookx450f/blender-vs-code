"""
DBマイグレーション - mirror_offset_mm 列の追加と既存データの初期化

使い方:
    python migrate_mirror_offset.py
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cars.db")

# 車種タイプ別のミラー突出量（片側 mm）
MIRROR_OFFSET_BY_TYPE = {
    "軽自動車": 70,
    "スポーツカー": 90,
    "セダン": 95,
    "ハッチバック": 95,
    "SUV": 100,
    "ミニバン": 100,
    "ピックアップ": 110,
    "バス/トラック": 80,
}

# 既存43車種の個別設定（ID → mirror_offset_mm）
CAR_MIRROR_OFFSETS = {
    1: 100,   # 日産新型ムラーノ2027 - SUV
    2: 120,   # ランドクルーザー250 - 大型SUV
    3: 120,   # ランドクルーザーFJ - 大型SUV
    4: 100,   # マツダ CX-5 2026 - SUV
    5: 100,   # カローラクロス 2025 - SUV
    6: 100,   # カローラクロス 2026 - SUV
    7: 100,   # ハリアー 2025 - SUV
    8: 70,    # BYD ラッコ - 軽自動車
    9: 70,    # 日産 サクラ - 軽自動車
    10: 120,  # ハイランダー - 大型SUV
    11: 100,  # アルファード 2023 - ミニバン
    12: 100,  # エルグランド 2026 - ミニバン
    13: 120,  # ランドクルーザー300 - 大型SUV
    14: 85,   # TESLA MODEL Y - テスラ（ミラーレス）
    15: 85,   # TESLA MODEL Y L - テスラ（ミラーレス）
    16: 120,  # ランドクルーザー70 - 大型SUV
    17: 95,   # シエンタ - セダン
    18: 90,   # LFA - スポーツカー
    19: 90,   # スープラA90 - スポーツカー
    20: 110,  # タコマ SR5 ダブルキャブ - ピックアップ
    21: 120,  # ラングラー4ドア - 大型SUV
    22: 100,  # セレナ 2023 - ミニバン
    23: 100,  # エルグランド 2010 - ミニバン
    24: 105,  # レクサス LM - 高級ミニバン
    25: 90,   # GR86 - スポーツカー
    26: 90,   # BRZ - スポーツカー
    27: 90,   # ロータス エスプリ - スポーツカー
    28: 90,   # フェアレディZ32 - スポーツカー
    29: 70,   # ルーミー - 軽自動車
    30: 100,  # ノア 2022 - ミニバン
    31: 100,  # ステップワゴン 2017 - ミニバン
    32: 100,  # ヴェルファイア 2023 - ミニバン
    33: 100,  # オデッセイ - ミニバン
    34: 70,   # ミライース - 軽自動車
    35: 80,   # コースター - バス
    36: 120,  # タンドラ - 大型SUV/ピックアップ
    37: 70,   # スマート フォーフォー - 軽自動車
    38: 80,   # 三菱ふそうキャンター - バス/トラック
    39: 80,   # ハイエース - バン
    40: 100,  # RAV4 2025 - SUV
    41: 95,   # クラウン スポーツ - セダン
    42: 95,   # プリウス - セダン
    43: 95,   # アクア - セダン
}


def migrate():
    """マイグレーションを実行"""
    if not os.path.exists(DB_PATH):
        print(f"エラー: データベースが見つかりません - {DB_PATH}")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # mirror_offset_mm 列が存在するか確認
        cursor.execute("PRAGMA table_info(cars)")
        columns = [col[1] for col in cursor.fetchall()]

        if "mirror_offset_mm" in columns:
            print("mirror_offset_mm 列は既に存在します。スキップします。")
        else:
            # 列を追加（デフォルト値は100mm）
            cursor.execute("ALTER TABLE cars ADD COLUMN mirror_offset_mm INTEGER DEFAULT 100")
            print("✓ mirror_offset_mm 列を追加しました")

        # 既存データの初期化
        updated = 0
        for car_id, offset in CAR_MIRROR_OFFSETS.items():
            cursor.execute("SELECT id FROM cars WHERE id = ?", (car_id,))
            if cursor.fetchone():
                cursor.execute(
                    "UPDATE cars SET mirror_offset_mm = ? WHERE id = ?",
                    (offset, car_id)
                )
                updated += 1

        conn.commit()
        print(f"✓ {updated} 台の車種の mirror_offset_mm を初期化しました")

        # 結果を確認
        cursor.execute("SELECT id, name, width, mirror_offset_mm FROM cars ORDER BY id")
        rows = cursor.fetchall()
        print(f"\n{'ID':>3} | {'車名':<20} | {'全幅':>5} | {'mirror_offset':>6} | {'実効幅':>6}")
        print("-" * 60)
        for row in rows:
            car_id, name, width, offset = row
            effective_width = width + (offset * 2)
            print(f"{car_id:>3} | {name:<20} | {width:>5} | {offset:>5}mm | {effective_width:>5}")

        conn.close()
        return True

    except Exception as e:
        conn.rollback()
        print(f"✗ マイグレーションエラー: {e}")
        conn.close()
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("DBマイグレーション - mirror_offset_mm 列追加")
    print("=" * 50)
    migrate()
