"""Fix plans/short2の仕様.md Section 3-3 transparency description"""

file_path = "plans/short2の仕様.md"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the incorrect Section 3-3 that says Alpha=1.0 from fr30 to end_frame
old_section = '''### 3-3. CarBの半透明化
- **方式**: Mix Shader Facキーフレーム式（CONSTANT補間で瞬時切り替え）
- **フレーム0-29**: Alpha=0.35 (半透明) — 車が中央で重なる際、carBは半透明で重なりを表現
- **フレーム30-end_frame**: Alpha=1.0 (完全不透明) — fr30で瞬時に不透明化'''

new_section = '''### 3-3. CarBの半透明化（3段階透明度仕様）
- **方式**: Mix Shader Facキーフレーム式（CONSTANT補間で瞬時切り替え）
- **フレーム0-29**: Alpha=0.35 (半透明) — 車が中央で重なる際、carBは半透明で重なりを表現
- **フレーム30-66**: Alpha=1.0 (完全不透明) — fr30で瞬時に不透明化（スライドアウト後）
- **フレーム67-203**: Alpha=0.35 (半透明) — スライドイン完了後、再び半透明に
- **フレーム204-end_frame**: Alpha=1.0 (不透明) — フェーズA終了で最終不透明化'''

content = content.replace(old_section, new_section)

# Also fix the incorrect "CarB: Alpha=1.0（不透明状態）" at cut1 end which should be semi-transparent
old_cut1end = '''### 3-4. カット1終了地点（fr120時点）
- CarA: 中央集合位置 (X≈0, Y=rear_offset_y, Z=grounded_z_a)
- CarB: 中央集合位置 (X≈0, Y=0.0, Z=grounded_z_b)
- カメラ: 円弧パンニング右方向終了位置
- CarB: Alpha=1.0（不透明状態）'''

new_cut1end = '''### 3-4. カット1終了地点（fr120時点）
- CarA: 中央集合位置 (X≈0, Y=rear_offset_y, Z=grounded_z_a)
- CarB: 中央集合位置 (X≈0, Y=0.0, Z=grounded_z_b)
- カメラ: 円弧パンニング右方向終了位置
- CarB: Alpha=0.35（半透明状態 - fr67で再び半透明になっている）'''

content = content.replace(old_cut1end, new_cut1end)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ plans/short2の仕様.md 修正完了")