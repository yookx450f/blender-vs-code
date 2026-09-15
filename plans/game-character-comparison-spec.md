# ゲームキャラクターショート動画仕様

## 概要

ゲームキャラクターの3Dモデル（GLB）を比較する縦長ショート動画（9:16）を全自動生成するシステム。
Short2（車の縦型比較動画）と同じアニメーション構造をベースに、ゲームキャラクター向けに調整。

- **コマンド**: `python run.py shortGame`
- **GLBディレクトリ**: `glb_game/`
- **フォーマット**: 縦長 9:16
- **総フレーム数**: fr0-624（約26秒 @24fps）

---

## アニメーション構成

### カット構造

| カット | フレーム | 時間 | 内容 |
|--------|----------|------|------|
| カット1 | fr0-288 | 約12秒 | キャラクターが中央へスライド + 円弧パンニング |
| カット2A | fr289-456 | 約7秒 | トップダウンビューへの移動（イージング適用）+ キャラクターズスライド開始 |
| カット2B | fr457-624 | 約7秒 | カメラ復帰（イージング適用）+ CharB不透明化 + キャラクターズスライド完了 |

### カット1: キャラクター中央スライド + 円弧パンニング (fr0-288)

- **CharA**: (-1.25, rear_offset_y) → 中央集合位置
- **CharB**: (1.25, 0.0) → 中央集合位置
- キャラクターはカット1開始後約42%地点（5秒相当）で中央に到達し、その後は位置を維持
- カメラは円弧軌道上をパンニング（デフォルト半径6.5m、高度3.5m）
- パンニング終盤には最大35%のズームイン

### カット2A: トップダウンビューへ移動 (fr289-456)

- カメラは円弧軌道上から真上（高さ12m）へ移動
- 移動はイージング関数（デフォルト: cubic ease-in-out）を適用
- キャラクターは中央から ±0.6m ほど離れる位置へスライド開始

### カット2B: カメラ復帰 + CharB不透明化 (fr457-624)

- カメラはトップダウン位置から元の円弧軌道へ復帰
- CharBは fr30 で半透明化（alpha=0.35）、フェーズB開始で瞬時に不透明化（alpha=1.0）
- 透明度の遷移は**瞬時の切り替え**（CONSTANT補間）。漸進的な変化はしない
- キャラクターは中央から X=-1.5m (CharA)、X=+1.5m (CharB) へスライド復帰

---

## 半透明化のルール

**ゲームキャラクターの半透明化は「瞬時の切り替え」で行う。**

| フレーム範囲 | Alpha値 | 状態 |
|-------------|---------|------|
| fr0-30 | 1.0 | 不透明（開始時は両方見える） |
| fr30-cut2b_start | 0.35 | 半透明（重なり状態を区別するため） |
| cut2b_end以降 | 1.0 | 不透明（分離して元に戻る） |

**禁止事項:**
- clamp() や漸進的な式で透明度を徐々に変化させてはいけない
- 透明度は常に「不透明(1.0)」か「半透明(0.35)」の2つの値の間で瞬時に行き来するだけ

---

## カメラ・視点の連続性ルール

**各カット間のカメラ位置とターゲットは滑らかに接続する。**

- カット1終了位置からカット2Aが開始される
- カット2A終了位置（トップダウン）からカット2Bが開始される
- 瞬間移動は禁止。すべての遷移はイージング付きで補間

**ターゲットの向き:**

| カット | ターゲット |
|--------|-----------|
| カット1 | (0, 0, 1.0) — キャラクター中央付近 |
| カット2A | トップダウンへ移動中に真下を向く（X軸90度回転） |
| カット2B | 復帰中に X軸-30度（少し下を見る） |

---

## バリエーション設定

`strategy_config` を通じて以下の要素を変動可能:

| 項目 | 説明 | デフォルト |
|------|------|-----------|
| `total_frames` | 総フレーム数 | 624 |
| `phase_a_duration_modifier` | フェーズAの時間倍率 | 1.0 |
| `camera_pattern` | カメラ円弧パターン | start=(-3,-6,3.5), rotation=-0.85 |
| `easing_function` | イージング関数 | cubic ease-in-out |
| `transparency_target` | 半透明化対象キャラクター | gameB |

---

## データベーススキーマ

### games テーブル

| カラム名 | タイプ | 説明 |
|---------|--------|------|
| id | INTEGER PK | 自動採番 |
| name | TEXT NOT NULL | キャラクター名 |
| glb_filename | TEXT DEFAULT '' | GLBファイル名 |
| game_name | TEXT DEFAULT '' | 所属ゲームタイトル |
| height | REAL DEFAULT 0 | 全高 (mm) ※最大100m (100,000mm) |
| length | REAL DEFAULT 0 | 全長 (mm) ※最大100m (100,000mm) |
| rotation_direction | INTEGER DEFAULT 0 | 回転方向補正値 |
| color_name | TEXT DEFAULT 'グレー' | クレイモデル色名 |

### game_comparisons テーブル

| カラム名 | タイプ | 説明 |
|---------|--------|------|
| id | INTEGER PK | 自動採番 |
| game_a_id | INTEGER NOT NULL | FK → games.id |
| game_b_id | INTEGER NOT NULL | FK → games.id |
| short_status | INTEGER DEFAULT 0 | ショート動画制作状況 (0-5) |
| long_status | INTEGER DEFAULT 0 | 長尺動画制作状況 (0-3) |
| short_video_url | TEXT DEFAULT '' | YouTubeショートURL |
| long_video_url | TEXT DEFAULT '' | YouTube長尺URL |
| short_views | INTEGER DEFAULT 0 | ショート視聴数 |
| long_views | INTEGER DEFAULT 0 | 長尺視聴数 |
| notes | TEXT DEFAULT '' | メモ |
| created_at | TIMESTAMP | 作成日時 |
| updated_at | TIMESTAMP | 更新日時 |

---

## games_config.json の仕様

```json
{
  "glb_dir": "C:/github/blender-vs-code/glb_game",
  "gameA": {
    "id": "1",
    "color": [1.0, 0.2, 0.2],
    "position": [2.0, 0.0, 0]
  },
  "gameB": {
    "id": "2",
    "color": [0.0, 0.7, 1.0],
    "position": [-2.0, 0.0, 0]
  }
}
```

- `glb_dir`: GLBモデルの配置ディレクトリ
- `gameA/gameB.id`: gamesテーブルのIDを参照
- `gameA/gameB.color`: クレイモデルのエミッション色 (RGB, 0.0-1.0)
- `gameA/gameB.position`: 初期配置位置 (X, Y, Z)

---

## 実装ファイル構成

| ファイル | 役割 |
|----------|------|
| [`animation_settings_shortGame.py`](animation_settings_shortGame.py) | メインエントリーポイント（全体フローの調整） |
| [`short_game_cuts.py`](short_game_cuts.py) | カット1-2Bの位置アニメーションキーフレーム設定 |
| [`short_game_utils.py`](short_game_utils.py) | キーフレーム設定、イージング関数、視覚的中心計算などの共通ツール |
| [`comparison_manager.py`](comparison_manager.py) | games/game_comparisons テーブルのCRUD関数 |
| [`games_config.json`](games_config.json) | 比較ペアID・色・位置の設定ファイル |
| [`pages/01_ゲームキャラ一覧.py`](pages/01_ゲームキャラ一覧.py) | Web管理画面（キャラクターの追加・編集・削除） |
| [`pages/02_ゲーム比較マトリクス.py`](pages/02_ゲーム比較マトリクス.py) | Web管理画面（比較ペアの状況管理） |

---

## Web管理画面仕様

### pages/01_ゲームキャラ一覧.py

- **タイトル**: 🎮 ゲームキャラ一覧
- **ページアイコン**: 🎮
- **テーマカラー**: 紫系 (#AB47BC)
- **入力項目**: キャラ名、GLBファイル名、ゲーム名、全高(mm)、全長(mm)、Z軸回転角度(度)、クレイモデルの色
- **数値範囲**: 全高/全長は 0〜100,000mm（最大100m）
- **操作**: 新規追加・編集・削除・検索・CSVエクスポート

---

## 実行コマンド

```bash
# シーン生成 + レンダリング
python run.py shortGame

# 特定ペアで実行（games_config.json に設定されたIDペアを使用）
python run.py shortGame --seed 42
```
