# 全幅ミラー包含補正 - 車種タイプ別アプローチ (C案)

## 問題

現在 [`blend_scene_creator.py:86`](blend_scene_creator.py:86) で全車種に固定+200mmを加算しているが、
車種によってミラーの突出量が異なるため不正確。

```python
# 現状 - 全車種に+200mm（不正確）
"width": width_raw + 200,
```

## 解決策: DBに `mirror_offset_mm` 列を追加

各車種に「片側ミラー突出量(mm)」を登録し、3Dスケール計算時に `width + mirror_offset_mm × 2` を使用する。

### 補正値テーブル

| 車種タイプ | 片側ミラー突出量 (mm) | 両側合計 (mm) | 代表車種 |
|-----------|---------------------|-------------|---------|
| kei (軽自動車) | 70 | 140 | ラッコ、サクラ、ミライース、ルーミー、スマート |
| sports (スポーツカー) | 90 | 180 | LFA、スープラ、GR86、BRZ、エスプリ、フェアレディZ |
| sedan (セダン/ハッチバック) | 95 | 190 | プリウス、アクア、クラウンスポーツ、シエンタ |
| suv_compact (コンパクトSUV) | 100 | 200 | RAV4、CX-5、カローラクロス、ハリアー |
| suv_fullsize (大型SUV) | 120 | 240 | ランドクルーザー系、タンドラ、ラングラー、ハイランダー |
| mpv (ミニバン) | 100 | 200 | アルファード、ヴェルファイア、エルグランド、セレナ、ノア、ステップワゴン、オデッセイ |
| truck (トラック/ピックアップ) | 110 | 220 | タコマ |
| van (商用バン) | 80 | 160 | ハイエース、キャンター、コースター |
| lexus_lm (大型MPV) | 105 | 210 | レクサス LM |
| tesla (テスラ) | 85 | 170 | Model Y / Model Y L（ミラーレス仕様） |

### 既存43車種の分類

| ID | 車名 | タイプ | mirror_offset_mm |
|----|------|-------|-----------------|
| 1 | 日産新型ムラーノ2027 | suv_compact | 100 |
| 2 | ランドクルーザー250 | suv_fullsize | 120 |
| 3 | ランドクルーザーFJ | suv_fullsize | 120 |
| 4 | マツダ CX-5 2026 | suv_compact | 100 |
| 5 | カローラクロス 2025 | suv_compact | 100 |
| 6 | カローラクロス 2026 | suv_compact | 100 |
| 7 | ハリアー 2025 | suv_compact | 100 |
| 8 | BYD ラッコ | kei | 70 |
| 9 | 日産 サクラ | kei | 70 |
| 10 | ハイランダー | suv_fullsize | 120 |
| 11 | アルファード 2023 | mpv | 100 |
| 12 | エルグランド 2026 | mpv | 100 |
| 13 | ランドクルーザー300 | suv_fullsize | 120 |
| 14 | TESLA MODEL Y | tesla | 85 |
| 15 | TESLA MODEL Y L | tesla | 85 |
| 16 | ランドクルーザー70 | suv_fullsize | 120 |
| 17 | シエンタ | sedan | 95 |
| 18 | LFA | sports | 90 |
| 19 | スープラA90 | sports | 90 |
| 20 | タコマ SR5 ダブルキャブ | truck | 110 |
| 21 | ラングラー4ドア | suv_fullsize | 120 |
| 22 | セレナ 2023 | mpv | 100 |
| 23 | エルグランド 2010 | mpv | 100 |
| 24 | レクサス LM | lexus_lm | 105 |
| 25 | GR86 | sports | 90 |
| 26 | BRZ | sports | 90 |
| 27 | ロータス エスプリ | sports | 90 |
| 28 | フェアレディZ32 | sports | 90 |
| 29 | ルーミー | kei | 70 |
| 30 | ノア 2022 | mpv | 100 |
| 31 | ステップワゴン 2017 | mpv | 100 |
| 32 | ヴェルファイア 2023 | mpv | 100 |
| 33 | オデッセイ | mpv | 100 |
| 34 | ミライース | kei | 70 |
| 35 | コースター | van | 80 |
| 36 | タンドラ | suv_fullsize | 120 |
| 37 | スマート フォーフォー | kei | 70 |
| 38 | 三菱ふそうキャンター | van | 80 |
| 39 | ハイエース | van | 80 |
| 40 | RAV4 2025 | suv_compact | 100 |
| 41 | クラウン スポーツ | sedan | 95 |
| 42 | プリウス | sedan | 95 |
| 43 | アクア | sedan | 95 |

## 変更対象ファイル

### 1. DBスキーマ変更
- `cars` テーブルに `mirror_offset_mm INTEGER DEFAULT 100` 列を追加
- 既存データはスクリプトで一括更新

### 2. [`blend_scene_creator.py`](blend_scene_creator.py) - `load_cars_db()` (79-87行目)
```python
# 変更前
"width": width_raw + 200,

# 変更後
mirror_offset = row.get("mirror_offset_mm", 100)  # デフォルト100mm(両側200mm)
"width": width_raw + (mirror_offset * 2),
```

### 3. [`web_manage_cars.py`](web_manage_cars.py) - UI変更
- 車種追加/編集フォームに「車種タイプ」ドロップダウンを追加
- タイプ選択時に `mirror_offset_mm` を自動設定
- 手動で数値修正も可能にする

### 4. [`manage_cars.py`](manage_cars.py) - CLI変更
- `--mirror-offset` オプション追加（デフォルト100）
- CSVインポート時に `mirror_offset_mm` カラム対応

### 5. [`cars.csv`](cars.csv) - ヘッダー更新
- `mirror_offset_mm` カラムを追加

## データフロー

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  web_manage  │────▶│   cars.db   │◀────│ blend_scene_     │
│   _cars.py   │     │             │     │   creator.py     │
│ (タイプ選択)  │     │ width       │     │                  │
│ ↓自動設定    │     │ mirror_offset│     │ width = width    │
│ mirror_offset│     │ _mm         │     │   + offset×2     │
└─────────────┘     └─────────────┘     └──────────────────┘
                              │                    │
                              ▼                    ▼
                     ┌─────────────┐    ┌──────────────────┐
                     │ animation_  │    │   3Dモデル        │
                     │ settings    │    │ スケール適用      │
                     │ (表示値)    │    │ (width_raw+offset)│
                     └─────────────┘    └──────────────────┘
```

## テキスト表示の整合性

動画で表示する全幅数値は **カタログ値 (`width_raw`)** のまま使用し続ける。
3Dモデルのスケールのみが `mirror_offset × 2` を加算した値になる。

これにより：
- 画面で見える車の幅 ≈ ミラー包含の実寸法
- テロップの数値 = カタログ記載の全幅（ボディのみ）
- 「全幅」というラベルはカタログ値を示すため矛盾しない
