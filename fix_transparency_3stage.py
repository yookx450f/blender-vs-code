"""Fix _setup_short2_carb_transparency to support 3-stage transparency flow"""

file_path = "animation_common.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Change function signature - add final_restore_frame parameter
old_sig = "def _setup_short2_carb_transparency(car_object, end_frame=324, restore_frame=None, fade_again_frame=None):"
new_sig = "def _setup_short2_carb_transparency(car_object, end_frame=324, restore_frame=None, fade_again_frame=None, final_restore_frame=None):"
content = content.replace(old_sig, new_sig)

# 2. Update docstring to reflect the new 3-stage timeline
old_docstring = '''    """Carの透明度アニメーションをshort2専用ロジックで完全に再構築する

    すべてのキーフレームをCONSTANT補間で設定し、restore_frameでの瞬時不透明化を保証する。

    タイムライン (新しいカット1仕様):
    - fr0-29: Alpha=0.35 (半透明) — 最初は中央で重なり、carBは半透明
    - fr30-fade_again_frame: Alpha=1.0 (完全不透明) — CONSTANT補間でfr30で瞬時に不透明化
    - fade_again_frame-end_frame: Alpha=0.35 (半透明) — 再度半透明に

    Parameters:
        car_object: 対象車のオブジェクト
        end_frame: 終了フレーム (デフォルト324)
        restore_frame: 不透明化開始フレーム (None時はデフォルト30)
        fade_again_frame: 再度半透明にするフレーム (None時は設定しない)
    """'''

new_docstring = '''    """Carの透明度アニメーションをshort2専用ロジックで完全に再構築する

    すべてのキーフレームをCONSTANT補間で設定し、各転換点での瞬時切り替えを保証する。

    タイムライン (3段階透明度仕様):
    - fr0-fr29: Alpha=0.35 (半透明) — 最初は中央で重なり、carBは半透明
    - fr30-fr66: Alpha=1.0 (完全不透明) — CONSTANT補間でfr30で瞬時に不透明化
    - fr67-fr203: Alpha=0.35 (半透明) — スライドイン完了後、再び半透明に
    - fr204-end_frame: Alpha=1.0 (不透明) — フェーズA終了で最終不透明化

    Parameters:
        car_object: 対象車のオブジェクト
        end_frame: 終了フレーム (デフォルト324)
        restore_frame: 最初の不透明化開始フレーム (None時はデフォルト30)
        fade_again_frame: 再度半透明にするフレーム (None時は設定しない)
        final_restore_frame: 最終的な不透明化フレーム (None時は設定しない)
    """'''

content = content.replace(old_docstring, new_docstring)

# 3. Update the keyframe building logic
old_keyframes = '''            # CONSTANT補間でキーフレームを設定
            # 新しい流れ:
            #   fr0で半透明(0.35)、fr29まで維持、fr30で不透明化(1.0)
            #   fr67で再び半透明(0.35)に
            keyframes = [
                (0, 0.35),              # fr0: 半透明 (車が中央で重なる状態)
                (restore_frame - 1, 0.35),  # fr29: 半透明維持
                (restore_frame, 1.0),       # fr30: 瞬時不透明化
            ]

            if fade_again_frame is not None:
                keyframes.append((fade_again_frame - 1, 1.0))   # fr66: 不透明維持
                keyframes.append((fade_again_frame, 0.35))      # fr67: 再び半透明化
                keyframes.append((end_frame, 0.35))             # end_frame: 半透明維持
            else:
                keyframes.append((end_frame, 1.0))              # end_frame: 不透明維持'''

new_keyframes = '''            # CONSTANT補間でキーフレームを設定
            # 新しい流れ (3段階透明度):
            #   fr0で半透明(0.35)、fr29まで維持、fr30で不透明化(1.0)
            #   fr67で再び半透明(0.35)に
            #   fr204（final_restore_frame）で最終的に不透明化(1.0)
            keyframes = [
                (0, 0.35),              # fr0: 半透明 (車が中央で重なる状態)
                (restore_frame - 1, 0.35),  # fr29: 半透明維持
                (restore_frame, 1.0),       # fr30: 瞬時不透明化
            ]

            if fade_again_frame is not None:
                keyframes.append((fade_again_frame - 1, 1.0))   # fr66: 不透明維持
                keyframes.append((fade_again_frame, 0.35))      # fr67: 再び半透明化

                if final_restore_frame is not None:
                    keyframes.append((final_restore_frame - 1, 0.35))  # fr203: 半透明維持
                    keyframes.append((final_restore_frame, 1.0))      # fr204: 最終不透明化
                    keyframes.append((end_frame, 1.0))               # end_frame: 不透明維持
                else:
                    keyframes.append((end_frame, 0.35))             # end_frame: 半透明維持
            else:
                if final_restore_frame is not None:
                    keyframes.append((final_restore_frame - 1, 1.0))  # fr203: 不透明維持
                    keyframes.append((final_restore_frame, 0.35))      # fr204: 半透明化（リセット）
                    keyframes.append((end_frame, 0.35))               # end_frame: 半透明維持
                else:
                    keyframes.append((end_frame, 1.0))              # end_frame: 不透明維持'''

content = content.replace(old_keyframes, new_keyframes)

# 4. Update the print statement at the end
old_print = '''    bpy.context.scene.frame_set(0)
    if fade_again_frame is not None:
        print(f"  Car透明度(short2専用): fr0=0.35, fr{restore_frame}=1.0, fr{fade_again_frame}=0.35 [CONSTANT補間]")
    else:
        print(f"  Car透明度(short2専用): fr0=0.35, fr{restore_frame-1}=0.35, fr{restore_frame}=1.0 [CONSTANT補間]")'''

new_print = '''    bpy.context.scene.frame_set(0)
    if fade_again_frame is not None and final_restore_frame is not None:
        print(f"  Car透明度(short2専用-3段階): fr0=0.35, fr{restore_frame}=1.0, fr{fade_again_frame}=0.35, fr{final_restore_frame}=1.0 [CONSTANT補間]")
    elif fade_again_frame is not None:
        print(f"  Car透明度(short2専用-2段階): fr0=0.35, fr{restore_frame}=1.0, fr{fade_again_frame}=0.35 [CONSTANT補間]")
    else:
        print(f"  Car透明度(short2専用): fr0=0.35, fr{restore_frame-1}=0.35, fr{restore_frame}=1.0 [CONSTANT補間]")'''

content = content.replace(old_print, new_print)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ animation_common.py 修正完了")