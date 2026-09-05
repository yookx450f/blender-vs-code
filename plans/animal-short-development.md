# 動物ショート動画開発進捗ドキュメント

## 概要

車の比較システムを基盤に、動物の比較向けショート動画を新規追加するプロジェクト。

**目標**: `animation_settings_short2.py` を元にして `animation_settings_shortAnimal.py` を作成し、以下の機能を持つ动物比较ショート動画パイプラインを構築する。

| 項目 | 現状 (車) | 目标 (动物) |
|------|-----------|-------------|
| アニメーション設定 | `animation_settings_short2.py` | `animation_settings_shortAnimal.py` (新規) |
| グリッド | 床面のみ | 床面 + 背面壁面 (後方Y负方向にグリッドを追加) |
| 比较マトリクス | `pages/02_比較マトリクス.py` (車専用) | `pages/02_动物比較マトリクス.py` (新規、车と分离) |
| 設定ファイル | `cars_config.json` | `animals_config.json` (新規) |
| データベース | `cars` テーブル, `comparisons` テーブル | `animals` テーブル, `animal_comparisons` テーブル (新規) |

## リポジトリ構造 (新规ファイル)

```
blend-vs-code/
├── animals_config.json              # 动物比较ペア设定文件
├── animation_settings_shortAnimal.py # 动物向けショート動画アニメーション設定
├── comparison_manager.py            # DB扩张: animals, animal_comparisons テーブル追加
├── blend_scene_creator.py           # 背面グリッドオプション、shortAnimal 分岐追加
├── run.py                           # shortAnimal カット定義追加
├── pages/
│   └── 02_动物比較マトリクス.py     # 动物专用比较マトリクス UI (Streamlit)
└── plans/
    └── animal-short-development.md  # このファイル
```

## 实装フェーズ

### フェーズ1: 基础设定 ✅ 完了
- [x] 进捗ドキュメント作成 → **本ファイル**
- [x] TODOリスト作成

### フェーズ2: グリッド拡張 ⏳ 未着手
- [ ] `blend_scene_creator.py` の `create_grid_floor()` に背面グリッドオプションを追加
  - 引数 `add_back_grid=True/False` を追加
  - Y负方向 (后面) に同じ1m间隔のネオン・シアン发光グリッドを配置
  - 床面と同じマテリアルを使用

### フェーズ3: データ层扩张 ✅ 完了
- [x] `animals_config.json` を新規作成
- [x] `comparison_manager.py` に animals / animal_comparisons テーブルを追加
- [x] DB读取函数の动物対応版を追加
  - `get_animal_comparison_by_ids`, `create_animal_comparison_if_not_exists`, `update_animal_comparison_full`, `delete_animal_comparison` 等

### フェーズ4: アニメーション设定 ✅ 完了
- [x] `animation_settings_short2.py` をコピーして `animation_settings_shortAnimal.py` を作成
- [x] `blend_scene_creator.py` の呼び出し侧に背面グリッド启用を追加

### フェーズ5: コマンドライン統合 ✅ 完了
- [x] `run.py` に `shortAnimal` を `CUTS` 定数に追加
- [x] `blend_scene_creator.py` の `main()` に `shortAnimal` 分岐を追加

### フェーズ6: 比较マトリクス UI ✅ 完了
- [x] `pages/02_動物比較マトリクス.py` を新規作成
  - `pages/02_比較マトリクス.py` を基准に动物データを参照する样修改
  - 动物タイプフィルタを追加

### フェーズ7: テスト验证 ⏳ 次のターゲット
- [ ] Blenderで实际レンダリング测试
  - 背面グリッドが正しく表示されるか确认
  - 动物モデルの导入、スケール、接地処理が正常动作するか确认
  - アニメーションが short2 と同様に再生されるか确认

## 决定事项

| 番号 | 项目 | 决定内容 | 决定日 |
|------|------|----------|--------|
| A-1 | 动物GLBモデルの格纳先 | `animals_glb/` を新创建、动物专用ディレクトリ | 2026-09-03 |
| A-2 | 比较マトリクスDB设计 | 车专用 `cars`/`comparisons` と动物专用 `animals`/`animal_comparisons` を完全分离 | 2026-09-03 |
| A-3 | 背面グリッド设计 | 垂直壁面として Y负方向(后面) に立ち上升る、床面と同じ1m间隔・シアン发光 | 2026-09-03 |
| A-4 | animal_type 详细分类 | mammals(哺乳类), birds(鸟类), reptiles(爬虫类), fish(鱼类), insects(昆虫类), other(其他) | 2026-09-03 |
| A-5 | テキストラベルのフォント | 车种名と同様の `mebold.ttc` (メイリオ太字)、Emissionマテリアルを共通利用 | 2026-09-03 |

## 实装注意事项

1. **cars_config.json は变更不可**: `.clinerules` で禁止されているため、动物は别ファイル (`animals_config.json`) を使用
2. **グリッドの背面追加**: 现有の `create_grid_floor()` の变更后向后互换性を保つこと (引数オプションで制御)
3. **比较マトリクスの分离**: 车用UIを变更せず、独立した页面として実装すること
4. **アニメーション设定の复用最适化**: short2と同じ构造を尽量再利用し、必要な部分のみ修正する

## 进捗记录

| 日付 | 内容 | 担当者 |
|------|------|--------|
| 2026-09-03 | プロジェクト开始、进捗ドキュメント作成 | LLM Agent |

