"""
Gallery BGM動画 - レンダリングスクリプト
シーンを生成した後、カメラアニメーションを設定してレンダリングする。

使い方:
    # まずシーン生成
    blender --background --python gallery_scene_creator.py
    # その後、レンダリング（別実行で読み込む必要がある）
"""

import bpy
import os
import json
import math


def load_gallery_config():
    """gallery_bgm_config.json を読み込んで戻す"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "gallery_bgm_config.json")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    return config


def setup_camera_animation(gallery_settings, max_frames=None):
    """カメラの移動アニメーションを設定
    
    Args:
        gallery_settings: ギャラリー設定辞書
        max_frames: フレーム数の上限（None=制限なし）
    """
    scene = bpy.context.scene
    
    # カメラオブジェクトを取得
    camera_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'CAMERA':
            camera_obj = obj
            break
    
    if camera_obj is None:
        print("エラー: カメラが見つかりません")
        return
    
    # アニメーションデータを作成（必要なら）
    if not camera_obj.animation_data:
        camera_obj.animation_data_create()
    
    # 設定値を取得
    start_z = gallery_settings.get("start_z", -45)
    end_z = gallery_settings.get("end_z", 45)
    camera_height = gallery_settings.get("camera_height", 1.7)
    fps = scene.render.fps
    
    # 人間の歩行速度: 2 km/h = 0.556 m/s（ゆっくりとしたウォーキング感覚）
    speed = 0.556  # m/s (2 km/h - ゆったりと歩く感覚)
    
    # max_frames が指定されていれば、移動距離を調整する
    if max_frames:
        duration_seconds = max_frames / fps
        total_distance = duration_seconds * speed
        actual_start = (start_z + end_z) / 2 - total_distance / 2
        actual_end = (start_z + end_z) / 2 + total_distance / 2
    else:
        total_distance = abs(end_z - start_z)
        duration_seconds = total_distance / speed
        actual_start = start_z
        actual_end = end_z
    
    # フレーム数に変換
    total_frames = int(duration_seconds * fps)
    
    scene.frame_start = 1
    scene.frame_end = total_frames
    
    print(f"アニメーション設定:")
    print(f"  開始位置: Y={start_z}")
    print(f"  終了位置: Y={end_z}")
    print(f"  カメラ高さ: {camera_height}m")
    print(f"  総フレーム数: {total_frames}")
    print(f"  再生時間: {duration_seconds:.1f}秒")
    
    # キーフレームを設定
    # 開始位置
    camera_obj.location.x = 0  # 通路中央
    camera_obj.location.y = actual_start
    camera_obj.location.z = camera_height
    
    # カメラの視線: 高さ1.7mで前方（進行方向+Y）を水平に見る
    # Blenderではカメラがデフォルトで-Z方向を見る
    # +Y方向を見るには、X軸で+90度回転させる（-Z → +Y に回転）
    camera_obj.rotation_euler.x = math.radians(90)  # -Z方向から+Y方向へ回転
    camera_obj.rotation_euler.y = 0
    camera_obj.rotation_euler.z = 0  # Y軸進行なのでZ回転不要
    
    camera_obj.keyframe_insert(data_path="location", index=0, frame=1)  # X
    camera_obj.keyframe_insert(data_path="location", index=1, frame=1)  # Y
    camera_obj.keyframe_insert(data_path="location", index=2, frame=1)  # Z
    camera_obj.keyframe_insert(data_path="rotation_euler", index=0, frame=1)  # X回転
    
    # 終了位置
    camera_obj.location.y = actual_end
    camera_obj.keyframe_insert(data_path="location", index=1, frame=total_frames)  # Y
    
    # インターポレーションをスムーズに（Ease in/out）
    # Blender 5.x では fcurves のアクセス方法が変更されているため、
    # animation_data から直接アクセスする
    try:
        action = camera_obj.animation_data.action
        if action:
            # Blender 5.x: fcurves は Action から scene.animation_data に移動している場合あり
            if hasattr(action, 'fcurves'):
                for fc in action.fcurves:
                    if fc.data_path == "location" and fc.array_index == 1:
                        for kf in fc.keyframe_points:
                            kf.interpolation = 'BEZIER'
                            kf.handle_type_left = 'AUTO'
                            kf.handle_type_right = 'AUTO'
    except AttributeError:
        pass  # fcurves アクセスに失敗しても続行
    
    print("カメラアニメーション設定完了")


def setup_background_black():
    """背景を真っ黒に設定"""
    scene = bpy.context.scene
    
    # 世界を設定
    world = bpy.data.worlds.new(name="BlackWorld")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    
    # Background ノード
    bg_node = nodes.new("ShaderNodeBackground")
    bg_node.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)  # 黒
    bg_node.inputs["Strength"].default_value = 0.0  # 背景光なし
    
    # Output ノード
    output = nodes.new("ShaderNodeOutputWorld")
    links.new(bg_node.outputs["Background"], output.inputs["Surface"])
    
    scene.world = world
    print("背景を真っ黒に設定しました")


def configure_render_settings():
    """レンダリング設定"""
    scene = bpy.context.scene
    
    # 出力先
    desktop_path = os.path.expanduser("~").replace("\\", "/") + "/Desktop"
    output_filepath = f"{desktop_path}/gallery_bgm"
    scene.render.filepath = output_filepath
    
    # FFMPEG動画出力設定
    scene.render.image_settings.media_type = 'VIDEO'
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    
    # フレーム番号サフィックスを無効化
    for prop_name in ['use_frame_number', 'frame_number', 'use_placeholder']:
        try:
            if hasattr(scene.render.ffmpeg, prop_name):
                setattr(scene.render.ffmpeg, prop_name, False)
        except:
            pass
    
    # 解像度確認
    print(f"レンダリング設定:")
    print(f"  出力先: {output_filepath}.mp4")
    print(f"  フレーム範囲: {scene.frame_start}-{scene.frame_end}")
    print(f"  解像度: {scene.render.resolution_x}x{scene.render.resolution_y}")


def render_gallery():
    """レンダリングを実行するメイン関数"""
    # 設定読み込み
    config = load_gallery_config()
    gallery_settings = config.get("gallery", {})
    
    # 背景設定
    setup_background_black()
    
    # カメラアニメーションを設定
    setup_camera_animation(gallery_settings)
    
    # レンダリング設定
    configure_render_settings()
    
    print("\n=== レンダリング開始 ===")
    bpy.ops.render.render(animation=True)
    print("=== レンダリング完了 ===")
    print(f"確認: Desktop/gallery_bgm.mp4 が生成されています")


if __name__ == "__main__":
    render_gallery()
