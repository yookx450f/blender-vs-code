"""Fix animation_settings_short2.py to use 3-stage transparency parameters"""

file_path = "animation_settings_short2.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Change the call to _setup_short2_carb_transparency to include all 3 stages
old_call = '''    # カット2フェーズA終了時（fr204）でCarBを不透明化
    alpha_restore_frame = 204  # フェーズA終了フレーム
    _setup_short2_carb_transparency(target_car, end_frame=total_frames, restore_frame=alpha_restore_frame)
    print(f"  Alpha({transparency_target}): fr0で半透明(0.35), fr{alpha_restore_frame}で不透明化(1.0) [CONSTANT補間]")'''

new_call = '''    # 3段階透明度設定:
    #   fr0-fr29: Alpha=0.35 (半透明 - 車が中央で重なる状態)
    #   fr30-fr66: Alpha=1.0 (不透明 - スライドアウト後)
    #   fr67-fr203: Alpha=0.35 (半透明 - スライドイン完了後)
    #   fr204-end: Alpha=1.0 (不透明 - フェーズA終了時)
    first_restore_frame = 30       # fr30で一時的に不透明化
    fade_again_frame = 67          # fr67で再び半透明に
    final_restore_frame = 204      # fr204（フェーズA終了）で最終不透明化
    _setup_short2_carb_transparency(
        target_car, 
        end_frame=total_frames, 
        restore_frame=first_restore_frame,
        fade_again_frame=fade_again_frame,
        final_restore_frame=final_restore_frame
    )
    print(f"  Alpha({transparency_target}): fr0=0.35, fr{first_restore_frame}=1.0, fr{fade_again_frame}=0.35, fr{final_restore_frame}=1.0 [CONSTANT補間]")'''

content = content.replace(old_call, new_call)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ animation_settings_short2.py 修正完了")