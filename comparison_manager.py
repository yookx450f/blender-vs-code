"""
比較ペア管理モジュール

動画比較ペアの制作状況を追跡・管理するデータベース操作モジュール。
"""

import sqlite3
import pandas as pd
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cars.db")


def get_connection():
    """データベース接続を取得（sqlite3.Row 対応）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_connection_raw():
    """データベース接続を取得（pandas 用 - row_factory なし）"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_comparisons_table():
    """comparisonsテーブルを作成（存在しない場合）"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_a_id INTEGER NOT NULL,
            car_b_id INTEGER NOT NULL,
            short_status INTEGER DEFAULT 0,
            long_status INTEGER DEFAULT 0,
            short_video_url TEXT DEFAULT '',
            long_video_url TEXT DEFAULT '',
            short_views INTEGER DEFAULT 0,
            long_views INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (car_a_id) REFERENCES cars(id),
            FOREIGN KEY (car_b_id) REFERENCES cars(id),
            UNIQUE(car_a_id, car_b_id)
        )
    """)
    # 既存テーブルに新カラムがない場合は追加（マイグレーション対応）
    new_columns = [
        ("long_views", "INTEGER DEFAULT 0"),
        ("short_likes", "INTEGER DEFAULT 0"),
        ("short_comments", "INTEGER DEFAULT 0"),
        ("long_likes", "INTEGER DEFAULT 0"),
        ("long_comments", "INTEGER DEFAULT 0"),
        ("stats_updated_at", "TIMESTAMP"),
    ]
    for col_name, col_type in new_columns:
        try:
            conn.execute(f"ALTER TABLE comparisons ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass  # カラムが既に存在する場合は無視
    conn.commit()
    conn.close()


def get_all_cars():
    """全車種データをDataFrameとして取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cars ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return pd.DataFrame()
    data = [dict(row) for row in rows]
    return pd.DataFrame(data)


def get_all_comparisons():
    """全比較ペアを取得（車名付き・統計データ付き）"""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT
            c.id,
            c.car_a_id,
            c.car_b_id,
            ca.name AS car_a_name,
            cb.name AS car_b_name,
            c.short_status,
            c.long_status,
            c.short_video_url,
            c.long_video_url,
            c.short_views,
            c.long_views,
            c.short_likes,
            c.short_comments,
            c.long_likes,
            c.long_comments,
            c.stats_updated_at,
            c.notes,
            c.created_at,
            c.updated_at
        FROM comparisons c
        LEFT JOIN cars ca ON c.car_a_id = ca.id
        LEFT JOIN cars cb ON c.car_b_id = cb.id
        ORDER BY c.car_a_id, c.car_b_id
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return pd.DataFrame()
    data = [dict(row) for row in rows]
    return pd.DataFrame(data)


def get_comparison_by_ids(car_a_id, car_b_id):
    """指定ペアの情報を取得（存在しない場合はNone）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM comparisons WHERE car_a_id = ? AND car_b_id = ?
    """, (car_a_id, car_b_id))
    row = cursor.fetchone()
    conn.close()
    # sqlite3.Row を辞書に変換して返す
    if row:
        return dict(row)
    return None


def get_comparisons_for_car(car_id):
    """指定車が関わる全ペアを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT
            c.id,
            c.car_a_id,
            c.car_b_id,
            ca.name AS car_a_name,
            cb.name AS car_b_name,
            c.short_status,
            c.long_status,
            c.short_video_url,
            c.long_video_url,
            c.short_views,
            c.notes
        FROM comparisons c
        LEFT JOIN cars ca ON c.car_a_id = ca.id
        LEFT JOIN cars cb ON c.car_b_id = cb.id
        WHERE c.car_a_id = ? OR c.car_b_id = ?
        ORDER BY c.car_a_id, c.car_b_id
    """
    cursor.execute(query, (car_id, car_id))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return pd.DataFrame()
    data = [dict(row) for row in rows]
    return pd.DataFrame(data)


def create_comparison_if_not_exists(car_a_id, car_b_id):
    """ペアが存在しない場合は自動作成し、IDを返す"""
    existing = get_comparison_by_ids(car_a_id, car_b_id)
    if existing:
        return existing["id"]
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO comparisons (car_a_id, car_b_id, short_status, long_status)
            VALUES (?, ?, 0, 0)
        """, (car_a_id, car_b_id))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id
    except sqlite3.IntegrityError:
        conn.close()
        return None
    except Exception:
        conn.close()
        return None


def update_comparison_status(comp_id, short_status=None, long_status=None):
    """制作状況を更新"""
    conn = get_connection()
    try:
        if short_status is not None and long_status is not None:
            conn.execute("""
                UPDATE comparisons 
                SET short_status = ?, long_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (short_status, long_status, comp_id))
        elif short_status is not None:
            conn.execute("""
                UPDATE comparisons 
                SET short_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (short_status, comp_id))
        elif long_status is not None:
            conn.execute("""
                UPDATE comparisons 
                SET long_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (long_status, comp_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def update_comparison_url(comp_id, video_type, url):
    """YouTube URLを登録 (video_type: 'short' or 'long')"""
    conn = get_connection()
    try:
        if video_type == "short":
            conn.execute("""
                UPDATE comparisons 
                SET short_video_url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (url, comp_id))
        else:
            conn.execute("""
                UPDATE comparisons 
                SET long_video_url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (url, comp_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def update_short_views(comp_id, views):
    """ショート視聴回数を更新"""
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE comparisons 
            SET short_views = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (views, comp_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def update_notes(comp_id, notes):
    """メモを更新"""
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE comparisons 
            SET notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (notes, comp_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def update_comparison_full(comp_id, short_status, long_status, short_views, long_views, notes,
                           short_likes=None, short_comments=None, long_likes=None, long_comments=None):
    """比較ペアの全情報を一括更新"""
    conn = get_connection()
    try:
        if all(v is not None for v in [short_likes, short_comments, long_likes, long_comments]):
            conn.execute("""
                UPDATE comparisons
                SET short_status = ?, long_status = ?,
                    short_views = ?, long_views = ?, notes = ?,
                    short_likes = ?, short_comments = ?,
                    long_likes = ?, long_comments = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (short_status, long_status, short_views, long_views, notes,
                  short_likes, short_comments, long_likes, long_comments, comp_id))
        else:
            conn.execute("""
                UPDATE comparisons
                SET short_status = ?, long_status = ?,
                    short_views = ?, long_views = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (short_status, long_status, short_views, long_views, notes, comp_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def delete_comparison(comp_id):
    """比較ペアを削除"""
    conn = get_connection()
    try:
        conn.execute("""
            DELETE FROM comparisons WHERE id = ?
        """, (comp_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def get_matrix_data():
    """
    マトリクス表示用のデータを生成
    
    戻り値: 
    - cars_df: 車種リスト (縦軸・横軸用)
    - comparisons_df: 全比較ペアデータ
    """
    cars_df = get_all_cars()
    comparisons_df = get_all_comparisons()
    return cars_df, comparisons_df


def get_dashboard_stats():
    """ダッシュボード統計データを取得"""
    comps = get_all_comparisons()
    
    if comps.empty:
        return {
            "total_pairs": 0,
            "not_started": 0,
            "short_only": 0,
            "short_published": 0,
            "long_in_progress": 0,
            "both_done": 0,
            "total_short_views": 0
        }
    
    total = len(comps)
    not_started = len(comps[(comps["short_status"] == 0) & (comps["long_status"] == 0)])
    short_only = len(comps[(comps["short_status"] >= 1) & (comps["long_status"] == 0)])
    short_published = len(comps[comps["short_status"] == 2])
    long_in_progress = len(comps[comps["long_status"] == 1])
    both_done = len(comps[(comps["short_status"] == 2) & (comps["long_status"] == 2)])
    total_views = comps["short_views"].sum()
    
    return {
        "total_pairs": total,
        "not_started": not_started,
        "short_only": short_only,
        "short_published": short_published,
        "long_in_progress": long_in_progress,
        "both_done": both_done,
        "total_short_views": int(total_views)
    }


def get_long_video_candidates(limit=10):
    """長尺制作候補を視聴回数順で取得（ショート公開済み + 長尺未着手）"""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT
            c.id,
            c.car_a_id,
            c.car_b_id,
            ca.name AS car_a_name,
            cb.name AS car_b_name,
            c.short_status,
            c.long_status,
            c.short_views
        FROM comparisons c
        LEFT JOIN cars ca ON c.car_a_id = ca.id
        LEFT JOIN cars cb ON c.car_b_id = cb.id
        WHERE c.short_status = 2 AND c.long_status = 0
        ORDER BY c.short_views DESC
        LIMIT ?
    """
    cursor.execute(query, (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return pd.DataFrame(columns=["id", "car_a_id", "car_b_id", "car_a_name", "car_b_name",
                                      "short_status", "long_status", "short_views"])
    
    # sqlite3.Row を辞書リストに変換
    data = [dict(row) for row in rows]
    return pd.DataFrame(data)


def get_car_comparison_counts():
    """各車が関わる比較ペアの回数をカウント"""
    comps = get_all_comparisons()
    
    if comps.empty:
        return pd.DataFrame(columns=["car_id", "car_name", "comparison_count"])
    
    # car_a と car_b の両方をカウント
    counts_a = comps.groupby(["car_a_id", "car_a_name"]).size().reset_index(name="count_a")
    counts_b = comps.groupby(["car_b_id", "car_b_name"]).size().reset_index(name="count_b")
    
    # 統合
    all_counts = pd.concat([
        counts_a.rename(columns={"car_a_id": "car_id", "car_a_name": "car_name", "count_a": "comparison_count"})[["car_id", "car_name", "comparison_count"]],
        counts_b.rename(columns={"car_b_id": "car_id", "car_b_name": "car_name", "count_b": "comparison_count"})[["car_id", "car_name", "comparison_count"]]
    ])
    
    total_counts = all_counts.groupby(["car_id", "car_name"])["comparison_count"].sum().reset_index()
    total_counts = total_counts.sort_values("comparison_count", ascending=False)
    
    return total_counts


def set_comparison_pair_to_config(car_a_id, car_b_id):
    """cars_config.json に比較ペアを設定"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cars_config.json")
    
    try:
        import json
        glb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "C:\\3d\\Modly\\glb")
        
        # 既存設定を読み込む
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {
                "glb_dir": "C:\\3d\\Modly\\glb",
                "carA": {"id": "1", "color": [0.5, 0.5, 0.5], "position": [2.0, 0.0, 0]},
                "carB": {"id": "2", "color": [0.0, 0.7, 1.0], "position": [-2.0, 0.0, 0]}
            }
        
        config["carA"]["id"] = str(car_a_id)
        config["carB"]["id"] = str(car_b_id)
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return True, f"車A={car_a_id}, 車B={car_b_id} を設定しました"
    except Exception as e:
        return False, str(e)


# 初期化用ステータスラベル
STATUS_LABELS = {
    0: "未着手",
    1: "制作中",
    2: "公開済み"
}

STATUS_COLORS = {
    0: "#e0e0e0",  # グレー
    1: "#64b5f6",  # 青
    2: "#ffb74d"   # オレンジ
}


def get_combined_status(short_status, long_status):
    """
    ショート+長尺のステータスを組み合わせた総合ステータスを返す
    
    戻り値: (ラベル, 色コード)
    
    ステータス優先順位:
    - 両方完了 > ショート完了 > 長尺制作中 > 制作中 > 未着手
    """
    if short_status == 2 and long_status == 2:
        return "両方完了", "#4caf50"  # 緑
    elif short_status == 2 and long_status == 1:
        return "長尺制作中", "#ff9800"  # オレンジ
    elif short_status == 2 and long_status == 0:
        return "ショート完了", "#ffeb3b"  # 黄色
    elif short_status >= 1 or long_status >= 1:
        return "制作中", "#64b5f6"  # 青（片方でも制作中）
    else:
        return "未着手", "#e0e0e0"  # グレー


def is_invalid_pair(car_a_id, car_b_id):
    """無効ペアかどうかを判定（同じ車種 or 重複パターン）"""
    if car_a_id == car_b_id:
        return True
    # 逆順のペアが存在するかチェック
    existing = get_comparison_by_ids(car_b_id, car_a_id)
    if existing:
        return True
    return False


def update_comparison_stats(comp_id, short_stats, long_stats) -> bool:
    """
    比較ペアのYouTube統計データを更新する。

    Args:
        comp_id: 比較ペアのID
        short_stats: ショート動画の統計 {"viewCount", "likeCount", "commentCount"}（Noneでスキップ）
        long_stats: 長尺動画の統計 {"viewCount", "likeCount", "commentCount"}（Noneでスキップ）

    Returns:
        True if success, False otherwise
    """
    conn = get_connection()
    try:
        updates = []
        params = []

        if short_stats:
            updates.append("short_views = ?")
            params.append(short_stats.get("viewCount", 0))
            updates.append("short_likes = ?")
            params.append(short_stats.get("likeCount", 0))
            updates.append("short_comments = ?")
            params.append(short_stats.get("commentCount", 0))

        if long_stats:
            updates.append("long_views = ?")
            params.append(long_stats.get("viewCount", 0))
            updates.append("long_likes = ?")
            params.append(long_stats.get("likeCount", 0))
            updates.append("long_comments = ?")
            params.append(long_stats.get("commentCount", 0))

        if not updates:
            logger.info(f"  [DB SKIP] comp_id={comp_id}: 更新すべきデータなし (short={short_stats is not None}, long={long_stats is not None})")
            conn.close()
            return True  # 更新すべきデータなし

        updates.append("stats_updated_at = CURRENT_TIMESTAMP")
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(comp_id)

        sql = f"UPDATE comparisons SET {', '.join(updates)} WHERE id = ?"
        logger.info(f"  [DB UPDATE] comp_id={comp_id}: SQL={sql}")
        logger.info(f"    パラメータ: {params}")
        conn.execute(sql, params)
        conn.commit()
        
        # 更新後の値を確認
        cursor = conn.cursor()
        cursor.execute("SELECT short_views, short_likes, short_comments, long_views, long_likes, long_comments FROM comparisons WHERE id = ?", (comp_id,))
        row = cursor.fetchone()
        if row:
            logger.info(f"    更新後値: sv={row[0]}, sl={row[1]}, sc={row[2]}, lv={row[3]}, ll={row[4]}, lc={row[5]}")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"  [DB ERROR] comp_id={comp_id}: {e}")
        conn.close()
        return False


def bulk_update_all_stats(comparisons_data, api_stats):
    """
    全比較ペアのYouTube統計を一括更新する。

    Args:
        comparisons_data: 比較ペアのリスト（辞書）
        api_stats: fetch_stats_for_comparisons の戻り値の "stats" フィールド

    Returns:
        {"success": int, "failed": int, "errors": List[str]}
    """
    success = 0
    failed = 0
    errors = []

    logger.info(f"[BULK UPDATE] 比較ペア数: {len(comparisons_data)}, API統計数: {len(api_stats)}")
    logger.info(f"  api_statsのキー型: {type(list(api_stats.keys())[0]) if api_stats else 'N/A'}")

    for comp in comparisons_data:
        comp_id = comp["id"]
        stats = api_stats.get(comp_id)
        if not stats:
            # キーが文字列/整数で不一致している可能性をログ
            str_key = str(comp_id)
            if str_key in api_stats:
                logger.warning(f"  [KEY MISMATCH] comp_id={comp_id} (int) を見つけず、'{str_key}' (str) は存在")
            continue

        short_stats = stats.get("short")
        long_stats = stats.get("long")
        logger.info(f"[BULK UPDATE] comp_id={comp_id}: short={short_stats}, long={long_stats}")

        if update_comparison_stats(comp_id, short_stats, long_stats):
            success += 1
        else:
            failed += 1
            errors.append(f"comp_id={comp_id} の更新に失敗")

    logger.info(f"[BULK UPDATE] 完了: success={success}, failed={failed}")
    return {"success": success, "failed": failed, "errors": errors}


# ============================================================
# 動物用データ層 (animals / animal_comparisons)
# ============================================================

# クレイモデルの色定義（色名 → RGB値）
CLAY_COLOR_MAP = {
    "グレー": [0.5, 0.5, 0.5],
    "青": [0.0, 0.7, 1.0],
    "赤": [1.0, 0.2, 0.2],
    "黄色": [1.0, 0.9, 0.1],
    "ピンク": [1.0, 0.5, 0.7],
    "緑": [0.2, 0.8, 0.3],
    "茶色": [0.6, 0.4, 0.2],
    "黒": [0.15, 0.15, 0.15],
}
CLAY_COLOR_OPTIONS = list(CLAY_COLOR_MAP.keys())


def init_animals_table():
    """animalsテーブルを作成（存在しない場合）"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS animals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            glb_filename TEXT DEFAULT '',
            animal_type TEXT DEFAULT 'other',
            height REAL DEFAULT 0,
            weight REAL DEFAULT 0,
            rotation_direction INTEGER DEFAULT 0,
            color_name TEXT DEFAULT 'グレー'
        )
    """)
    # weight カラムが存在しない場合は追加（旧DBのマイグレーション対応）
    try:
        conn.execute("ALTER TABLE animals ADD COLUMN weight REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # 既に存在する場合は無視
    # color_name カラムが存在しない場合は追加（マイグレーション対応）
    try:
        conn.execute("ALTER TABLE animals ADD COLUMN color_name TEXT DEFAULT 'グレー'")
    except sqlite3.OperationalError:
        pass  # 既に存在する場合は無視
    conn.commit()
    conn.close()
    logger.info("animals テーブルを初期化しました")


def init_animal_comparisons_table():
    """animal_comparisonsテーブルを作成（存在しない場合）"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS animal_comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            animal_a_id INTEGER NOT NULL,
            animal_b_id INTEGER NOT NULL,
            short_status INTEGER DEFAULT 0,
            long_status INTEGER DEFAULT 0,
            short_video_url TEXT DEFAULT '',
            long_video_url TEXT DEFAULT '',
            short_views INTEGER DEFAULT 0,
            long_views INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (animal_a_id) REFERENCES animals(id),
            FOREIGN KEY (animal_b_id) REFERENCES animals(id),
            UNIQUE(animal_a_id, animal_b_id)
        )
    """)
    conn.commit()
    conn.close()
    logger.info("animal_comparisons テーブルを初期化しました")


def get_all_animals():
    """全動物データをDataFrameとして取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM animals ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return pd.DataFrame()
    data = [dict(row) for row in rows]
    return pd.DataFrame(data)


def get_all_animal_comparisons():
    """全動物比較ペアを取得（動物名付き）"""
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT
            c.id,
            c.animal_a_id,
            c.animal_b_id,
            aa.name AS animal_a_name,
            ab.name AS animal_b_name,
            c.short_status,
            c.long_status,
            c.short_video_url,
            c.long_video_url,
            c.short_views,
            c.long_views,
            c.notes,
            c.created_at,
            c.updated_at
        FROM animal_comparisons c
        LEFT JOIN animals aa ON c.animal_a_id = aa.id
        LEFT JOIN animals ab ON c.animal_b_id = ab.id
        ORDER BY c.animal_a_id, c.animal_b_id
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return pd.DataFrame()
    data = [dict(row) for row in rows]
    return pd.DataFrame(data)


def get_animals_db_dict():
    """SQLiteデータベースから動物マスターデータを辞書として読み込む"""
    init_animals_table()
    animals_db = {}
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM animals")
    for row in cursor.fetchall():
        animal = dict(row)  # sqlite3.Row → dict に変換（.get() のため）
        animal_id = str(animal["id"])
        color_name = animal.get("color_name", "グレー")
        if color_name not in CLAY_COLOR_MAP:
            color_name = "グレー"
        animals_db[animal_id] = {
            "name": animal["name"],
            "glb_filename": animal.get("glb_filename", ""),
            "animal_type": animal.get("animal_type", "other"),
            "height": animal.get("height", 0),
            "weight": animal.get("weight", 0),
            "rotation_direction": animal.get("rotation_direction", 0),
            "color_name": color_name,
            "color_rgb": CLAY_COLOR_MAP[color_name]
        }
    conn.close()
    logger.info(f"動物マスターDBを読み込みました: {len(animals_db)} 種類")
    return animals_db


def get_animal_comparison_by_ids(animal_a_id, animal_b_id):
    """指定ペアの情報を取得（存在しない場合はNone）"""
    init_animals_table()
    init_animal_comparisons_table()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM animal_comparisons WHERE animal_a_id = ? AND animal_b_id = ?
    """, (animal_a_id, animal_b_id))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def create_animal_comparison_if_not_exists(animal_a_id, animal_b_id):
    """ペアが存在しない場合は自動作成し、IDを返す"""
    existing = get_animal_comparison_by_ids(animal_a_id, animal_b_id)
    if existing:
        return existing["id"]
    
    init_animals_table()
    init_animal_comparisons_table()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO animal_comparisons (animal_a_id, animal_b_id, short_status, long_status)
            VALUES (?, ?, 0, 0)
        """, (animal_a_id, animal_b_id))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id
    except sqlite3.IntegrityError:
        conn.close()
        return None
    except Exception:
        conn.close()
        return None


def update_animal_comparison_full(comp_id, short_status, long_status, short_views, long_views, notes):
    """動物比較ペアの全情報を一括更新"""
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE animal_comparisons
            SET short_status = ?, long_status = ?,
                short_views = ?, long_views = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (short_status, long_status, short_views, long_views, notes, comp_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def update_animal_comparison_url(comp_id, video_type, url):
    """YouTube URLを登録 (video_type: 'short' or 'long')"""
    conn = get_connection()
    try:
        if video_type == "short":
            conn.execute("""
                UPDATE animal_comparisons
                SET short_video_url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (url, comp_id))
        else:
            conn.execute("""
                UPDATE animal_comparisons
                SET long_video_url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (url, comp_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def delete_animal_comparison(comp_id):
    """動物比較ペアを削除"""
    conn = get_connection()
    try:
        conn.execute("""
            DELETE FROM animal_comparisons WHERE id = ?
        """, (comp_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def set_animal_comparison_pair_to_config(animal_a_id, animal_b_id):
    """animals_config.json に比較ペアを設定（色もDBから取得してRGBに変換）"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "animals_config.json")
    
    try:
        import json
        glb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "C:\\\\3d\\\\Modly\\\\glb")
        
        # DBから動物データを取得（色情報を含む）
        animals_db = get_animals_db_dict()
        
        animal_a_data = animals_db.get(str(animal_a_id), {})
        animal_b_data = animals_db.get(str(animal_b_id), {})
        
        color_a = animal_a_data.get("color_rgb", CLAY_COLOR_MAP.get("グレー", [0.5, 0.5, 0.5]))
        color_b = animal_b_data.get("color_rgb", CLAY_COLOR_MAP.get("青", [0.0, 0.7, 1.0]))
        
        # 既存設定を読み込む
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {
                "glb_dir": glb_dir,
                "animalA": {"id": "1", "color": color_a, "position": [2.0, 0.0, 0]},
                "animalB": {"id": "2", "color": color_b, "position": [-2.0, 0.0, 0]}
            }
        
        config["animalA"]["id"] = str(animal_a_id)
        config["animalA"]["color"] = color_a
        config["animalB"]["id"] = str(animal_b_id)
        config["animalB"]["color"] = color_b
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return True, f"動物A={animal_a_id}, 動物B={animal_b_id} を設定しました"
    except Exception as e:
        return False, str(e)


def is_invalid_animal_pair(animal_a_id, animal_b_id):
    """無効ペアかどうかを判定（同じ動物 or 重複パターン）"""
    if animal_a_id == animal_b_id:
        return True
    # 逆順のペアが存在するかチェック
    existing = get_animal_comparison_by_ids(animal_b_id, animal_a_id)
    if existing:
        return True
    return False


def get_animal_matrix_data():
    """
    動物マトリクス表示用のデータを生成
    
    戻り値:
    - animals_df: 動物リスト (縦軸・横軸用)
    - animal_comparisons_df: 全動物比較ペアデータ
    """
    animals_df = get_all_animals()
    animal_comparisons_df = get_all_animal_comparisons()
    return animals_df, animal_comparisons_df


def get_animal_dashboard_stats():
    """動物ダッシュボード統計データを取得"""
    comps = get_all_animal_comparisons()
    
    if comps.empty:
        return {
            "total_pairs": 0,
            "not_started": 0,
            "short_only": 0,
            "short_published": 0,
            "long_in_progress": 0,
            "both_done": 0,
            "total_short_views": 0
        }
    
    total = len(comps)
    not_started = len(comps[(comps["short_status"] == 0) & (comps["long_status"] == 0)])
    short_only = len(comps[(comps["short_status"] >= 1) & (comps["long_status"] == 0)])
    short_published = len(comps[comps["short_status"] == 2])
    long_in_progress = len(comps[comps["long_status"] == 1])
    both_done = len(comps[(comps["short_status"] == 2) & (comps["long_status"] == 2)])
    total_views = comps["short_views"].sum()
    
    return {
        "total_pairs": total,
        "not_started": not_started,
        "short_only": short_only,
        "short_published": short_published,
        "long_in_progress": long_in_progress,
        "both_done": both_done,
        "total_short_views": int(total_views)
    }


def add_animal(name, glb_filename, animal_type, height, weight, rotation, color_name="グレー"):
    """新規動物追加"""
    if color_name not in CLAY_COLOR_MAP:
        color_name = "グレー"
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO animals (name, glb_filename, animal_type, height, weight, rotation_direction, color_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, glb_filename, animal_type, float(height), float(weight), int(rotation), color_name))
        conn.commit()
        new_id = conn.cursor().lastrowid
        conn.close()
        return True, new_id
    except sqlite3.IntegrityError:
        conn.close()
        return False, "動物名の登録に失敗しました"
    except Exception as e:
        conn.close()
        return False, str(e)


def get_animal_by_id(animal_id):
    """IDで動物データを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM animals WHERE id = ?", (animal_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def update_animal(animal_id, name, glb_filename, animal_type, height, weight, rotation, color_name="グレー"):
    """動物情報更新"""
    if color_name not in CLAY_COLOR_MAP:
        color_name = "グレー"
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE animals SET
                name = ?, glb_filename = ?, animal_type = ?, height = ?, weight = ?,
                rotation_direction = ?, color_name = ?
            WHERE id = ?
        """, (name, glb_filename, animal_type, float(height), float(weight), int(rotation), color_name, animal_id))
        conn.commit()
        conn.close()
        return True, "更新しました"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "動物名の登録に失敗しました"
    except Exception as e:
        conn.close()
        return False, str(e)


def delete_animal(animal_id):
    """動物を削除"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM animals WHERE id = ?", (animal_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False, "指定されたIDの動物が見つかりません"
    animal_name = row["name"]
    cursor.execute("DELETE FROM animals WHERE id = ?", (animal_id,))
    conn.commit()
    conn.close()
    return True, animal_name


def search_animals(query):
    """動物名で部分一致検索"""
    conn = get_connection_raw()
    df = pd.read_sql_query(
        "SELECT * FROM animals WHERE name LIKE ? ORDER BY id",
        (f"%{query}%",),
        conn
    )
    conn.close()
    return df


def export_animals_to_csv():
    """CSVデータを生成"""
    df = get_all_animals()
    return df.to_csv(index=False, encoding="utf-8-sig")
