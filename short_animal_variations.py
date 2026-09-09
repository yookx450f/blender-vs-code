"""
動物ショート動画 バリエーションモジュール

動物比較ショート動画の見た目を毎回ランダムに変化させるための
プリセット定義と戦略生成ロジックを一元管理する。

Short2 と同じプリセットを import で流用し、
動物特有のカメラパターン（固定位置 + 円軌道）を追加する。

使い方:
    from short_animal_variations import generate_strategy_config
    config = generate_strategy_config(seed=42)  # seed指定で再現可能
    config = generate_strategy_config()          # ランダムシード (毎回異なる)
"""

import math
import random
from short2_variations import (
    GRID_COLOR_PRESETS,
    CLAY_COLOR_PRESETS,
    BACKGROUND_GLOW_PRESETS,
    select_distinct_clay_colors,
    EASING_FUNCTIONS,
    get_easing_function,
    SLIDE_SPEED_MULTIPLIERS,
    LABEL_APPEAR_EFFECTS,
    GRID_PULSE_ENABLED,
)


# ============================================================
# 1. カメラパターンプリセット（動物用カスタム版）
# ============================================================

# カット1-2のカメラY固定値を ±1.5m の範囲で変動
CAMERA_Y_OFFSET_PRESETS = [
    {"name": "standard",   "y_offset": -11.0},  # 標準位置
    {"name": "closer",     "y_offset": -9.5},    # カメラを前に出す
    {"name": "further",    "y_offset": -12.0},   # カメラを後ろに引く
]

# カット1のZ始点/終点位置を変動
CAMERA_Z_PRESETS = [
    {"name": "standard",    "z_start": 0.5, "z_end": 7.0},
    {"name": "lower_start", "z_start": 0.3, "z_end": 6.0},
    {"name": "higher_end",  "z_start": 0.7, "z_end": 8.0},
]

# カット3の円軌道パラメータを変動
ORBIT_VARIATIONS = [
    {"name": "standard",    "radius": 11.0, "turns": 1.1},
    {"name": "wider",       "radius": 12.5, "turns": 1.1},
    {"name": "tighter",     "radius": 9.5,  "turns": 1.2},
    {"name": "slower",      "radius": 11.0, "turns": 1.0},
]

# カット3の開始角度を変動（切断接続位置をズラす）
ORBIT_START_ANGLE_VARIATIONS = [
    {"name": "south",       "angle_offset": 0.0},      # 南側から开始 (標準)
    {"name": "south_west",  "angle_offset": -0.3},     # 南西寄り
    {"name": "south_east",  "angle_offset": 0.3},      # 南東寄り
]


# ============================================================
# 2. テンポ設定
# ============================================================

BASE_TOTAL_FRAMES_ANIMAL = 936  # 約39秒 (標準)
TOTAL_FRAME_DURATION_MULTIPLIERS = [0.85, 0.9, 1.0, 1.1]  # ±15% の動画長さ変動


# ============================================================
# メイン選択関数
# ============================================================

def generate_strategy_config(seed=None):
    """
    ランダムに各プリセットを1つずつ選び、設定辞書を返す。
    
    Parameters:
        seed: int or None. 指定すると再現可能。None時はランダムシード。
    
    Returns:
        dict: 各色・カメラ・イージング・演出の設定を含む辞書
    """
    rng = random.Random(seed)
    
    # ルール: animalA と animalB は必ず異なるクレイ色を選択（且つRGB距離が離れている）
    clay_a, clay_b = select_distinct_clay_colors(rng, CLAY_COLOR_PRESETS, min_distance=0.35)
    
    config = {
        # 色設定
        "grid_color": rng.choice(GRID_COLOR_PRESETS),
        "clay_color_a": clay_a,
        "clay_color_b": clay_b,
        "bg_glow": rng.choice(BACKGROUND_GLOW_PRESETS),
        
        # カメラ設定
        "camera_y_offset": rng.choice(CAMERA_Y_OFFSET_PRESETS),
        "camera_z": rng.choice(CAMERA_Z_PRESETS),
        "orbit_variation": rng.choice(ORBIT_VARIATIONS),
        "orbit_start_angle": rng.choice(ORBIT_START_ANGLE_VARIATIONS),
        
        # テンポ設定
        "easing_function": rng.choice(list(EASING_FUNCTIONS.keys())),
        "slide_speed": rng.choice(SLIDE_SPEED_MULTIPLIERS),
        "total_frames_multiplier": rng.choice(TOTAL_FRAME_DURATION_MULTIPLIERS),
        
        # 演出設定
        "label_effect": rng.choice(LABEL_APPEAR_EFFECTS),
        "grid_pulse": rng.choice(GRID_PULSE_ENABLED),
    }
    
    # 総フレーム数を計算して追加（24の倍数に丸める）
    multiplier = config["total_frames_multiplier"]
    total_frames = round(BASE_TOTAL_FRAMES_ANIMAL * multiplier)
    total_frames = round(total_frames / 24) * 24
    if total_frames < 600:  # 最短25秒以下を防止
        total_frames = 600
    config["total_frames"] = total_frames
    
    return config


def print_config_summary(config):
    """設定サマリーを出力（ログ用）"""
    print("\n" + "="*50)
    print("  ShortAnimal バリエーション設定")
    print("="*50)
    print(f"  グリッド色:      {config['grid_color']['name']} ({config['grid_color']['color']})")
    print(f"  クレイ色A:       {config['clay_color_a']['name']} ({config['clay_color_a']['color']})")
    print(f"  クレイ色B:       {config['clay_color_b']['name']} ({config['clay_color_b']['color']})")
    print(f"  背景発光:        {config['bg_glow']['name']}")
    
    cam_y = config.get("camera_y_offset", {})
    print(f"  カメラYオフセット: {cam_y.get('name', 'standard')} (Y={cam_y.get('y_offset', -11.0)})")
    
    cam_z = config.get("camera_z", {})
    print(f"  カメラZ:         {cam_z.get('name', 'standard')} (start={cam_z.get('z_start', 0.5)}, end={cam_z.get('z_end', 7.0)})")
    
    orbit = config.get("orbit_variation", {})
    print(f"  円軌道:          {orbit.get('name', 'standard')} (radius={orbit.get('radius', 11.0)}m, turns={orbit.get('turns', 1.1)})")
    
    angle = config.get("orbit_start_angle", {})
    print(f"  開始角度オフセット: {angle.get('name', 'south')} (+{angle.get('angle_offset', 0.0)}rad)")
    
    print(f"  イージング関数:   {config['easing_function']}")
    print(f"  スライド速度:     {config['slide_speed']}x")
    print(f"  テキスト効果:    {config['label_effect']}")
    print(f"  グリッドパルス:  {'ON' if config['grid_pulse'] else 'OFF'}")
    print(f"  総フレーム数:    {config.get('total_frames', BASE_TOTAL_FRAMES_ANIMAL)} (約{config.get('total_frames', BASE_TOTAL_FRAMES_ANIMAL)/24:.1f}秒)")
    print("="*50)


def load_config_from_env():
    """環境変数からバリエーション設定を読み込む
    
    Returns:
        dict or None: 設定辞書。未設定時はNoneを返す
    """
    import os
    seed_str = os.environ.get("STRATEGY_SEED", "")
    
    if not seed_str:
        print("  ℹ️ STRATEGY_SEED 環境変数が設定されていません")
        return None
    
    try:
        seed = int(seed_str)
        print(f"  🎲 STRATEGY_SEED={seed} からバリエーション設定を生成中...")
        config = generate_strategy_config(seed=seed)
        print_config_summary(config)
        print("  ✅ バリエーション設定の読み込み完了")
        return config
    except Exception as e:
        import traceback
        print(f"  ❌ バリエーション設定の読み込みに失敗: {e}")
        traceback.print_exc()
        return None
