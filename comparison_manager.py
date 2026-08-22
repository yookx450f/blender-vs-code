"""
比較ペア管理モジュール

動画比較ペアの制作状況を追跡・管理するデータベース操作モジュール。
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime

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
    # 既存テーブルに long_views カラムがない場合は追加
    try:
        conn.execute("ALTER TABLE comparisons ADD COLUMN long_views INTEGER DEFAULT 0")
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
    """全比較ペアを取得（車名付き）"""
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


def update_comparison_full(comp_id, short_status, long_status, short_views, long_views, notes):
    """比較ペアの全情報を一括更新"""
    conn = get_connection()
    try:
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
