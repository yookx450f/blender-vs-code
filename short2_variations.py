"""
Short2 バリエーションモジュール

Short2の動画を毎回異なる見た目・動きにするために、
ランダム組み合わせ方式による変数化管理を行う。

使い方:
    from short2_variations import generate_strategy_config
    config = generate_strategy_config(seed=42)  # seed指定で再現可能
    config = generate_strategy_config()          # ランダムシード (毎回異なる)
"""

import math
import random


# ============================================================
# 1. 色パレットプリセット
# ============================================================

GRID_COLOR_PRESETS = [
    {"name": "cyan",         "color": (0.0, 0.8, 1.0),   "emission": 2.0},
    {"name": "orange",       "color": (1.0, 0.5, 0.0),   "emission": 2.0},
    {"name": "magenta",      "color": (1.0, 0.0, 0.8),   "emission": 2.0},
    {"name": "lime_green",   "color": (0.3, 1.0, 0.2),   "emission": 2.0},
    {"name": "purple",       "color": (0.6, 0.0, 1.0),   "emission": 2.0},
    {"name": "red",          "color": (1.0, 0.15, 0.15), "emission": 2.0},
]

CLAY_COLOR_PRESETS = [
    # --- 原有のニュアンス系 ---
    {"name": "white_gray",   "color": (0.85, 0.85, 0.87)},
    {"name": "warm_gray",    "color": (0.72, 0.68, 0.64)},
    {"name": "vivid_orange", "color": (0.95, 0.55, 0.25)},
    {"name": "clay_brown",   "color": (0.75, 0.58, 0.42)},
    {"name": "ice_blue",     "color": (0.65, 0.78, 0.90)},
    # --- 鮮やか色追加 ---
    {"name": "vivid_red",    "color": (0.95, 0.20, 0.20)},
    {"name": "vivid_green",  "color": (0.20, 0.85, 0.30)},
    {"name": "vivid_blue",   "color": (0.20, 0.40, 1.00)},
    {"name": "vivid_yellow", "color": (0.95, 0.85, 0.10)},
    {"name": "hot_pink",     "color": (1.00, 0.30, 0.60)},
    {"name": "electric_purple", "color": (0.70, 0.20, 1.00)},
]

BACKGROUND_GLOW_PRESETS = [
    {"name": "subtle_cyan",  "color": (0.0, 0.15, 0.2),  "strength": 0.3},
    {"name": "dark_orange",  "color": (0.15, 0.08, 0.0), "strength": 0.2},
    {"name": "none",         "color": (0.0, 0.0, 0.0),   "strength": 0.0},
]


def _color_distance(color_a, color_b):
    """2色のRGBユークリッド距離を計算（0〜1.73の範囲）"""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(color_a, color_b)))


def select_distinct_clay_colors(rng, presets, min_distance=0.35):
    """
    十分な距離を隔てた2つのクレイ色を選択。
    
    Parameters:
        rng: random.Randomインスタンス
        presets: クレイ色のプリセットリスト
        min_distance: RGB距離の最小閾値（デフォルト0.35）
    
    Returns:
        tuple: (clay_a, clay_b) のタプル
    """
    clay_a = rng.choice(presets)
    candidates = [c for c in presets if c["name"] != clay_a["name"]]
    
    # 距離条件を満たす候補を優先
    distant = [c for c in candidates if _color_distance(clay_a["color"], c["color"]) >= min_distance]
    
    if distant:
        clay_b = rng.choice(distant)
    else:
        # 閾値以下しかない場合は、最も距離の遠い色を選択
        clay_b = max(candidates, key=lambda c: _color_distance(clay_a["color"], c["color"]))
    
    return clay_a, clay_b


# ============================================================
# 2. カメラパターンプリセット
# ============================================================

CAMERA_PATTERNS = [
    {
        "name": "standard_arc_lr",       # 標準: 左→右円弧パン
        "pan_direction": 1,              # 1=左から右, -1=右から左
        "start_position": (-3.0, -6.0, 3.5),
        "total_rotation": -0.85,
    },
    {
        "name": "reverse_arc_rl",        # 逆方向: 右→左円弧パン
        "pan_direction": -1,
        "start_position": (3.0, -6.0, 3.5),
        "total_rotation": 0.85,
    },
    {
        "name": "wide_arc_lr",           # ワイド: より大きな円弧
        "pan_direction": 1,
        "start_position": (-4.0, -7.0, 4.0),
        "total_rotation": -1.1,
    },
    {
        "name": "close_arc_lr",          # クローズ: より近い位置からのパン
        "pan_direction": 1,
        "start_position": (-2.0, -4.5, 2.8),
        "total_rotation": -0.65,
    },
]

TOPDOWN_VARIATIONS = [
    {"name": "pure_topdown",     "position": (0.0, 0.0, 8.0)},   # 真上
    {"name": "angled_topdown",   "position": (1.5, -1.5, 6.0)},  # 斜め上
    {"name": "low_topdown",      "position": (0.0, 0.0, 5.0)},   #低い位置からの俯瞰
]

TRANSPARENCY_TARGET = ["carB", "carA"]  # 半透明化する車をランダム選択


# ============================================================
# 3. イージング関数プリセット
# ============================================================

def _ease_cubic(t):
    """Ease in-out cubic"""
    if t < 0.5:
        return 4.0 * t * t * t
    else:
        return 1.0 - (-2.0 * t + 2.0)**3 / 2.0


def _ease_quint(t):
    """Ease in-out quint — より強い緩急"""
    if t < 0.5:
        return 16.0 * t**5
    else:
        return 1.0 - (-2.0 * t + 2.0)**5 / 2.0


def _ease_sine(t):
    """Ease in-out sine — 滑らかな三角波"""
    return (1.0 - math.cos(math.pi * t)) / 2.0


def _ease_expo(t):
    """Ease in-out expo — 急激な加減速"""
    if t == 0.0 or t == 1.0:
        return t
    if t < 0.5:
        return (8.0 * t - 7.0)**4
    else:
        return 1.0 - (13.0 - 8.0 * t)**4 / 2.0


EASING_FUNCTIONS = {
    "cubic": _ease_cubic,
    "quint": _ease_quint,
    "sine":  _ease_sine,
    "expo":  _ease_expo,
}

SLIDE_SPEED_MULTIPLIERS = [0.85, 0.9, 1.0, 1.1, 1.15]  # ±15% の速度変動

TOTAL_FRAME_DURATION_MULTIPLIERS = [0.8, 0.9, 1.0, 1.1, 1.2]  # ±20% の動画長さ変動
BASE_TOTAL_FRAMES = 624  # 標準の総フレーム数（約26秒）


# ============================================================
# 4. 演出エフェクトプリセット
# ============================================================

LABEL_APPEAR_EFFECTS = [
    "fade_in",       # 透明度を0→1にフェード
    "slide_up",      # 下方からスライドして出現
    "scale_in",      # 0倍から拡大して出現
]

GRID_PULSE_ENABLED = [True, False]  # グリッド床面の光のパルスエフェクトの有無


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
    
    # ルール1: CarAとCarBは必ず異なるクレイ色を選択（且つRGB距離が離れている）
    clay_a, clay_b = select_distinct_clay_colors(rng, CLAY_COLOR_PRESETS, min_distance=0.35)
    
    config = {
        # 色設定
        "grid_color": rng.choice(GRID_COLOR_PRESETS),
        "clay_color_a": clay_a,
        "clay_color_b": clay_b,
        "bg_glow": rng.choice(BACKGROUND_GLOW_PRESETS),
        
        # カメラ設定
        "camera_pattern": rng.choice(CAMERA_PATTERNS),
        "topdown_variation": rng.choice(TOPDOWN_VARIATIONS),
        # ルール2: 半透明対象はランダムではなく、blend_scene_creator.pyで全高比較して動的判定
        
        # テンポ設定
        "easing_function": rng.choice(list(EASING_FUNCTIONS.keys())),
        "slide_speed": rng.choice(SLIDE_SPEED_MULTIPLIERS),
        "total_frames_multiplier": rng.choice(TOTAL_FRAME_DURATION_MULTIPLIERS),
        
        # 演出設定
        "label_effect": rng.choice(LABEL_APPEAR_EFFECTS),
        "grid_pulse": rng.choice(GRID_PULSE_ENABLED),
        
        # フェーズAの時間変動 (±10%)
        "phase_a_duration_modifier": round(rng.uniform(0.9, 1.1), 2),
    }
    
    # 総フレーム数を計算して追加
    multiplier = config["total_frames_multiplier"]
    total_frames = round(BASE_TOTAL_FRAMES * multiplier)
    # 24の倍数に丸める（秒数との整合性）
    total_frames = round(total_frames / 24) * 24
    if total_frames < 300:  # 最短12.5秒以下を防止
        total_frames = 300
    config["total_frames"] = total_frames
    
    return config


def get_easing_function(name):
    """名前でイージング関数を取得"""
    return EASING_FUNCTIONS.get(name, _ease_cubic)


def print_config_summary(config):
    """設定サマリーを出力（ログ用）"""
    print("\n" + "="*50)
    print("  Short2 バリエーション設定")
    print("="*50)
    print(f"  グリッド色:      {config['grid_color']['name']} ({config['grid_color']['color']})")
    print(f"  クレイ色A:       {config['clay_color_a']['name']} ({config['clay_color_a']['color']})")
    print(f"  クレイ色B:       {config['clay_color_b']['name']} ({config['clay_color_b']['color']})")
    print(f"  背景発光:        {config['bg_glow']['name']}")
    print(f"  カメラパターン:  {config['camera_pattern']['name']} (start={config['camera_pattern']['start_position']})")
    print(f"  トップダウン:     {config['topdown_variation']['name']} ({config['topdown_variation']['position']})")
    # ルール2: 半透明対象はblend_scene_creator.pyで全高比較して動的判定
    if "transparency_target" in config:
        print(f"  半透明対象:      {config['transparency_target']} (全高比較)")
    print(f"  イージング関数:   {config['easing_function']}")
    print(f"  スライド速度:     {config['slide_speed']}x")
    print(f"  テキスト効果:    {config['label_effect']}")
    print(f"  グリッドパルス:  {'ON' if config['grid_pulse'] else 'OFF'}")
    print(f"  フェーズA倍率:   {config['phase_a_duration_modifier']}x")
    print(f"  総フレーム数:    {config.get('total_frames', BASE_TOTAL_FRAMES)} (約{config.get('total_frames', BASE_TOTAL_FRAMES)/24:.1f}秒)")
    print("="*50)
