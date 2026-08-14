import bpy
import os

# アニメーションレンダリングを実行（EEVEE）
print("=== アニメーションレンダリング開始 (EEVEE) ===")

scene = bpy.context.scene

# 出力パスを再設定
desktop_path = os.path.expanduser("~").replace("\\", "/") + "/Desktop"
output_filepath = f"{desktop_path}/mp4"
scene.render.filepath = output_filepath

# フレーム番号サフィックスを無効化（Blender 5.x 対応）
suffix_disabled = False

# Blender 5.x では scene.render.use_filename_extension が関係する可能性あり
try:
    if hasattr(scene.render, 'use_file_extension'):
        scene.render.use_file_extension = True
        print("scene.render.use_file_extension = True")
except Exception as e:
    print(f"use_file_extension 設定失敗: {e}")

# FFMPEGのフレーム番号サフィックスを無効化（複数のプロパティ名を試す）
for prop_name in ['use_frame_number', 'frame_number', 'use_placeholder']:
    try:
        if hasattr(scene.render.ffmpeg, prop_name):
            setattr(scene.render.ffmpeg, prop_name, False)
            suffix_disabled = True
            print(f"scene.render.ffmpeg.{prop_name} = False (成功)")
    except Exception as e:
        print(f"scene.render.ffmpeg.{prop_name} 設定失敗: {e}")

# image_settings のフレーム番号サフィックスも確認
for prop_name in ['use_file_extension', 'color_mode']:
    try:
        if hasattr(scene.render.image_settings, prop_name):
            val = getattr(scene.render.image_settings, prop_name)
            print(f"scene.render.image_settings.{prop_name} = {val}")
    except Exception as e:
        pass

if not suffix_disabled:
    print("警告: フレーム番号サフィックスを無効化するプロパティが見つかりませんでした")
    print("  出力ファイル名にフレーム範囲が追加される可能性があります")

# FFMPEG動画出力設定を再確認
scene.render.image_settings.media_type = 'VIDEO'
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'

print(f"出力先: {output_filepath}.mp4")
print(f"フレーム範囲: {scene.frame_start}-{scene.frame_end}")

# レンダリング実行
bpy.ops.render.render(animation=True)
print("アニメーションレンダリング完了！")
print(f"確認: {output_filepath}.mp4 が生成されているか確認してください")
