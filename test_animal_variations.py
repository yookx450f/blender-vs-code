"""テスト: shortAnimalのバリエーション設定が正しく異なるクレイ色を生成するか確認"""
import sys
sys.path.insert(0, '.')

from short_animal_variations import generate_strategy_config, print_config_summary

# シード42でテスト
config = generate_strategy_config(seed=42)

print("\n=== 検証結果 ===")

color_a = config['clay_color_a']['color']
color_b = config['clay_color_b']['color']

print(f"動物Aの色: {config['clay_color_a']['name']} -> RGB{color_a}")
print(f"動物Bの色: {config['clay_color_b']['name']} -> RGB{color_b}")

if color_a == color_b:
    print("\n❌ エラー: 動物Aと動物Bの色が同じです！")
else:
    print("\n✅ OK: 動物Aと動物Bの色は異なります")

# 複数シードでテスト
print("\n=== 複数シードでのテスト ===")
for seed in [1, 2, 3, 4, 5]:
    cfg = generate_strategy_config(seed=seed)
    a = cfg['clay_color_a']['color']
    b = cfg['clay_color_b']['color']
    status = "❌ 同じ色" if a == b else "✅ 異なる色"
    print(f"  シード{seed}: A={cfg['clay_color_a']['name']}, B={cfg['clay_color_b']['name']} -> {status}")
