"""
各カットの固定位置定義ファイル

各カットは自分のフレーム範囲内のキーフレームのみを操作し、
前のカットの結果に依存しない。
"""

import json
import os

# ============================================================
# フレーム範囲定義
# ============================================================

# 【改訂: カット1の最終的な秒数に調整】最後の停止感をカット
CUT1_START_FRAME = 0
CUT1_END_FRAME = 408

CUT2_START_FRAME = 408  # 【改訂】カット1が576→408に短縮され、-168フレームずれた
CUT2_END_FRAME = 744  # 【改訂】カット2: 912→744 (-168)

CUT3_START_FRAME = 744  # 【改訂】カット2終了に合わせて開始フレーム変更
CUT3_END_FRAME = 960  # 【改訂】カット3: 1128→960 (-168)

CUT4_START_FRAME = 1512
CUT4_END_FRAME = 2136

CUT4B_START_FRAME = 2136
CUT4B_END_FRAME = 2904

CUT5_START_FRAME = 2904
CUT5_END_FRAME = 3168

# ショート動画用（縦長9:16、フレーム0-144、約6秒）
SHORT_START_FRAME = 0
SHORT_END_FRAME = 144

# カット定義のマップ（一括処理用）
CUT_FRAMES = {
    1: (CUT1_START_FRAME, CUT1_END_FRAME),
    2: (CUT2_START_FRAME, CUT2_END_FRAME),
    3: (CUT3_START_FRAME, CUT3_END_FRAME),
    4: (CUT4_START_FRAME, CUT4_END_FRAME),
    "4b": (CUT4B_START_FRAME, CUT4B_END_FRAME),
    5: (CUT5_START_FRAME, CUT5_END_FRAME),
}

# ============================================================
# カメラの固定位置（カット境界で）
# ============================================================

CAMERA_POSITIONS = {
    "cut1_start": {"loc": (6.5, -6.5, 4.0), "target": (0.0, 0.0, 1.5)},
    "cut1_end":   {"loc": (8.0, 0.0, 2.5), "target": (0.0, 0.0, 1.5)},
    "cut2_end":   {"loc": (0.0, -5.5, 2.5), "target": (0.0, 0.0, 1.5)},
    "cut3_end":   {"loc": (-6.0, -2.0, 0.8), "target": (0.0, 0.0, 1.5)},
    "cut4_end":   {"loc": None, "target": None},  # Cut4は回転中心に依存
    "cut4b_end":  {"loc": None, "target": None},  # Cut4bはCut4のカメラ位置を継承（俯瞰に戻す）
    "cut5_end":   {"loc": None, "target": None},  # Cut5はCut4bのカメラ位置を継承
}

# ============================================================
# オフセットJSONファイルの管理
# ============================================================

OFFSET_FILE = "cut_offsets.json"


def get_offset_file_path():
    """オフセットJSONファイルの絶対パスを返す"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, OFFSET_FILE)


def save_offsets(offset_data):
    """
    オフセットデータをJSONファイルに保存する

    Parameters:
        offset_data: dict 形式のオフセットデータ
            {
                "offset_a": [x, y],
                "offset_b": [x, y],
                "grounded_z_a": float,
                "grounded_z_b": float,
                "rear_offset_y": float,
                "car_a_center": [x, y, z],
                "car_b_center": [x, y, z]
            }
    """
    file_path = get_offset_file_path()
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(offset_data, f, indent=4, ensure_ascii=False)
        print(f"[animation_cut_positions] オフセットを保存しました: {file_path}")
        return True
    except Exception as e:
        print(f"[animation_cut_positions] オフセット保存に失敗しました: {e}")
        return False


def load_offsets():
    """
    JSONファイルからオフセットデータを読み込む

    Returns:
        dict: オフセットデータ、ファイルが存在しない場合は None
    """
    file_path = get_offset_file_path()
    if not os.path.exists(file_path):
        print(f"[animation_cut_positions] オフセットファイルが見つかりません: {file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[animation_cut_positions] オフセットを読み込みました: {file_path}")
        return data
    except Exception as e:
        print(f"[animation_cut_positions] オフセット読み込みに失敗しました: {e}")
        return None


def get_default_offsets():
    """
    デフォルトのオフセット値を返す（ファイルが存在しない場合のフォールバック）

    Returns:
        dict: デフォルトオフセットデータ
    """
    return {
        "offset_a": [0.0, 0.0],
        "offset_b": [0.0, 0.0],
        "grounded_z_a": 0.85,
        "grounded_z_b": 0.92,
        "rear_offset_y": 0.15,
        "car_a_center": [0.0, 0.0, 0.85],
        "car_b_center": [0.0, 0.0, 0.92]
    }


def get_car_positions():
    """
    車の位置情報を取得（JSONファイルから読み込み、存在しない場合はデフォルト使用）

    Returns:
        tuple: (car_a_center, car_b_center) の座標ペア
    """
    data = load_offsets() or get_default_offsets()
    car_a_center = tuple(data.get("car_a_center", [0.0, 0.0, 0.85]))
    car_b_center = tuple(data.get("car_b_center", [0.0, 0.0, 0.92]))
    return car_a_center, car_b_center


def get_ground_z_positions():
    """
    接地Z座標を取得（JSONファイルから読み込み、存在しない場合はデフォルト使用）

    Returns:
        dict: {'carA': z_value, 'carB': z_value}
    """
    data = load_offsets() or get_default_offsets()
    return {
        'carA': data.get("grounded_z_a", 0.85),
        'carB': data.get("grounded_z_b", 0.92)
    }


def get_rear_offset_y():
    """
    リアオフセットY値を取得（JSONファイルから読み込み、存在しない場合はデフォルト使用）

    Returns:
        float: rear_offset_y 値
    """
    data = load_offsets() or get_default_offsets()
    return data.get("rear_offset_y", 0.15)
