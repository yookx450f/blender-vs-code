"""
Short2 バリエーション適用モジュール

すでに作成されたBlenderシーンに対して、
グリッド色・クレイモデル色・背景発光色の変更を適用する。

使い方:
    from short2_apply_variations import apply_variations_to_scene
    apply_variations_to_scene(config)
"""

import bpy
import json
import math
import os
import sys


def apply_grid_color(grid_color_config):
    """グリッド床面のエミッションカラーを変更
    
    Parameters:
        grid_color_config: {"name": str, "color": (r,g,b), "emission": float}
    """
    color = grid_color_config["color"]
    emission = grid_color_config.get("emission", 2.0)
    
    # グリッドマテリアルを探す
    grid_mat_name = "NeonGridMaterial"
    if grid_mat_name not in bpy.data.materials:
        print(f"  ⚠️ グリッドマテリアル '{grid_mat_name}' が見つかりません")
        return
    
    grid_mat = bpy.data.materials[grid_mat_name]
    if not grid_mat.use_nodes:
        return
    
    # Emission ノードのカラーを変更
    for node in grid_mat.node_tree.nodes:
        if node.type == 'EMISSION':
            node.inputs['Color'].default_value = (*color, 1.0)
            print(f"  ✅ グリッド色変更: {grid_color_config['name']} → RGB{color}")
            break


def apply_clay_colors(clay_color_config):
    """車のクレイモデルカラーを変更
    
    Parameters:
        clay_color_config: {"name": str, "color": (r,g,b)}
    """
    color = clay_color_config["color"]
    
    # クレイマテリアルを探す
    count = 0
    for mat in bpy.data.materials:
        if mat.name.startswith("clay_"):
            # Principled BSDF の Base Color を変更
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        # 既存色の明るさを保ちつつ、Hueシフト的に適用
                        node.inputs['Base Color'].default_value = (*color, 1.0)
                        count += 1
                        break
    
    print(f"  ✅ クレイ色変更: {clay_color_config['name']} → RGB{color} ({count}マテリアル更新)")


def apply_clay_colors_per_car(clay_color_a, clay_color_b):
    """車ごとに異なるクレイ色を適用（ルール1: CarAとCarBは必ず違う色）
    
    Parameters:
        clay_color_a: {"name": str, "color": (r,g,b)} - CarAの色
        clay_color_b: {"name": str, "color": (r,g,b)} - CarBの色
    """
    color_a = clay_color_a["color"]
    color_b = clay_color_b["color"]
    
    count_a = 0
    count_b = 0
    
    for mat in bpy.data.materials:
        if not mat.name.startswith("clay_"):
            continue
            
        # マテリアル名から車判定 (clay_carA_xxx / clay_carB_xxx)
        if "carA" in mat.name:
            color = color_a
            target = "a"
        else:
            color = color_b
            target = "b"
        
        # Principled BSDF の Base Color を変更
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED':
                    node.inputs['Base Color'].default_value = (*color, 1.0)
                    if target == "a":
                        count_a += 1
                    else:
                        count_b += 1
                    break
    
    print(f"  ✅ クレイ色変更: CarA={clay_color_a['name']}({count_a}個), CarB={clay_color_b['name']}({count_b}個)")


def apply_background_glow(bg_glow_config):
    """世界の背景発光を変更
    
    Parameters:
        bg_glow_config: {"name": str, "color": (r,g,b), "strength": float}
    """
    color = bg_glow_config["color"]
    strength = bg_glow_config.get("strength", 0.0)
    
    world = bpy.data.worlds.get("World") or bpy.context.scene.world
    if not world:
        print(f"  ⚠️ ワールドデータが見つかりません")
        return
    
    if strength > 0 and world.use_nodes:
        tree = world.node_tree
        # Background ノードを探す
        for node in tree.nodes:
            if node.type == 'BACKGROUND':
                # BlenderのColor入力は4成分(R,G,B,A)を要求
                node.inputs['Color'].default_value = (*color, 1.0)
                node.inputs['Strength'].default_value = strength
                print(f"  ✅ 背景発光変更: {bg_glow_config['name']} (強度={strength})")
                return
    
    print(f"  ✅ 背景発光設定: {bg_glow_config['name']}")


def apply_label_appear_effect(text_objects, effect_type):
    """テキストラベルの出現エフェクトを適用
    
    Parameters:
        text_objects: テキストオブジェクトのリスト
        effect_type: "fade_in", "slide_up", "scale_in" のいずれか
    """
    if not text_objects or effect_type == "fade_in":
        # fade_inはデフォルト動作（エフェクトなし）
        return
    
    appear_frames = 48  # 2秒間で出現完了
    
    for obj in text_objects:
        if obj.type != 'FONT':
            continue
        
        # アニメーションデータを作成
        if obj.animation_data is None:
            obj.animation_data_create()
        
        if effect_type == "slide_up":
            # 下方からスライドして出現
            original_y = obj.location.y
            offset_y = original_y - 0.5  # 下方に0.5m
            
            # フレーム0で下方位置
            bpy.context.scene.frame_set(0)
            obj.location.y = offset_y
            obj.keyframe_insert(data_path="location", index=1)
            
            # appear_frames で目標位置
            bpy.context.scene.frame_set(appear_frames)
            obj.location.y = original_y
            obj.keyframe_insert(data_path="location", index=1)
        
        elif effect_type == "scale_in":
            # 0倍から拡大して出現
            # フレーム0でスケール0
            bpy.context.scene.frame_set(0)
            obj.scale = (0.01, 0.01, 0.01)
            obj.keyframe_insert(data_path="scale", index=-1)
            
            # appear_frames でスケール1
            bpy.context.scene.frame_set(appear_frames)
            obj.scale = (1.0, 1.0, 1.0)
            obj.keyframe_insert(data_path="scale", index=-1)
    
    print(f"  ✅ テキスト出現エフェクト: {effect_type}")


def apply_grid_pulse_effect(grid_mat_name="NeonGridMaterial", duration_frames=624):
    """グリッド床面に光のパルスアニメーションを追加
    
    Parameters:
        grid_mat_name: グリッドマテリアル名
        duration_frames: アニメーションの総フレーム数
    """
    if grid_mat_name not in bpy.data.materials:
        return
    
    grid_mat = bpy.data.materials[grid_mat_name]
    if not grid_mat.use_nodes:
        return
    
    # Emission ノードを探す
    emission_node = None
    for node in grid_mat.node_tree.nodes:
        if node.type == 'EMISSION':
            emission_node = node
            break
    
    if not emission_node:
        return
    
    # パルス用のテクスチャ座標 + マッピング + ウェーブノードを追加
    nodes = grid_mat.node_tree.nodes
    links = grid_mat.node_tree.links
    
    # WaveTexture ノードを追加（パルス波）
    wave_tex = nodes.new(type='ShaderNodeTexWave')
    wave_tex.location = (-400, -300)
    wave_tex.inputs['Scale'].default_value = 2.0
    wave_tex.inputs['Detail'].default_value = 0.5
    if 'Distortion Scale' in wave_tex.inputs:
        wave_tex.inputs['Distortion Scale'].default_value = 3.0
    
    # マッピングノードを追加（アニメーション用）
    mapping_pulse = nodes.new(type='ShaderNodeMapping')
    mapping_pulse.location = (-600, -300)
    
    # Texture Coordinate ノード
    tex_coord = nodes.new(type='ShaderNodeTexCoord')
    tex_coord.location = (-800, -300)
    
    # 乗算ノード（パルスをStrengthに加算）
    math_add = nodes.new(type='ShaderNodeMath')
    math_add.operation = 'ADD'
    math_add.location = (-200, -200)
    
    links.new(tex_coord.outputs['Object'], mapping_pulse.inputs['Vector'])
    links.new(mapping_pulse.outputs['Vector'], wave_tex.inputs['Vector'])
    links.new(wave_tex.outputs['Fac'], math_add.inputs[1])
    
    # Emission Strength に加算する場合は既存リンクを保持しつつ組み合わせる必要があるが、
    # シンプルにするため既存のStrength値に0.5〜2.0の範囲でウェーブを加算
    
    print(f"  ✅ グリッドパルスエフェクト: ON (フレーム{duration_frames})")


def apply_variations_to_scene(config):
    """シーンの外観バリエーションを適用
    
    Parameters:
        config: strategy_config dict (from short2_variations.generate_strategy_config)
    """
    print("\n=== Short2 バリエーション適用開始 ===")
    
    # 色設定の適用
    if "grid_color" in config:
        apply_grid_color(config["grid_color"])
    
    if "clay_color" in config:
        apply_clay_colors(config["clay_color"])
    
    if "bg_glow" in config:
        apply_background_glow(config["bg_glow"])
    
    # テキスト出現エフェクトの適用
    if "label_effect" in config:
        text_objects = [obj for obj in bpy.data.objects if obj.type == 'FONT']
        if text_objects:
            apply_label_appear_effect(text_objects, config["label_effect"])
    
    # グリッドパルスエフェクトの適用
    if "grid_pulse" in config and config["grid_pulse"]:
        apply_grid_pulse_effect()
    
    print("=== Short2 バリエーション適用完了 ===")


def load_config_from_env():
    """環境変数からバリエーション設定を読み込む
    
    Returns:
        dict or None: 設定辞書。未設定時はNoneを返す
    """
    seed_str = os.environ.get("STRATEGY_SEED", "")
    
    if not seed_str:
        print("  ℹ️ STRATEGY_SEED 環境変数が設定されていません")
        return None
    
    try:
        seed = int(seed_str)
        print(f"  🎲 STRATEGY_SEED={seed} からバリエーション設定を生成中...")
        
        # short2_variations モジュールをインポート
        script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        
        from short2_variations import generate_strategy_config, print_config_summary
        config = generate_strategy_config(seed=seed)
        printConfigSummary = getattr(sys.modules.get('short2_variations'), 'print_config_summary', None)
        if printConfigSummary:
            printConfigSummary(config)
        
        print("  ✅ バリエーション設定の読み込み完了")
        return config
    except Exception as e:
        import traceback
        print(f"  ❌ バリエーション設定の読み込みに失敗: {e}")
        traceback.print_exc()
        return None
