# カット独立ファイル保存・合成方式の設計

## 概要

各カットを独立したBlenderプロセスで実行し、個別の`.blend`ファイルに保存する方式。これにより、全カット実行時にも互いのアニメーションデータが干渉しない。

## 問題背景

- `run.py all` 実行時に後続カットの視覚効果オブジェクト（TireTrackなど）が累積
- カメラ位置やフレーム範囲の設定が上書きされる可能性
- 現在のコードでは全カットが同じBlenderセッションで連続実行されるため、状態が累積する

## アーキテクチャ

### 現状の問題点
```
run.py all → 単一Blenderプロセス
            → Cut1 → Cut2 → Cut3 → Cut4（連続実行）
            → オブジェクトが累積 → 画面偏移
```

### 修正後の構造
```
run.py all → 4つの独立プロセス
           → Cut1 → cut1_scene.blend
           → Cut2 → cut2_scene.blend
           → Cut3 → cut3_scene.blend
           → Cut4 → cut4_scene.blend
           → レンダリング合成 → 最終動画
```

## 実装計画

### 1. `blend_scene_creator.py` の修正
- 各カット実行後に `.blend` ファイルに保存するロジックを追加
- 環境変数 `CUT_NUMBER` に応じてファイル名を切り替え

### 2. `run.py` の修正
- `all` モードを4つの独立プロセスに分割
- 各プロセスが個別の`.blend`ファイルを生成
- オプションでレンダリング合成を実行

### 3. 新しいスクリプト: `merge_cuts.py`
- 各カットの`.blend`ファイルからレンダリングを合成
- フレーム範囲を連結して最終動画生成

## ファイル構成

```
c:/github/blender-vs-code/
├── cut1_scene.blend      # カット1（フレーム0-648）
├── cut2_scene.blend      # カット2（フレーム648-1224）
├── cut3_scene.blend      # カット3（フレーム1224-1584）
├── cut4_scene.blend      # カット4（フレーム1584-1992）
├── blend_scene_creator.py
├── run.py
└── merge_cuts.py         # 新規作成
```

## 実装ステップ

1. [ ] `blend_scene_creator.py` にシーン保存ロジックを追加
2. [ ] `run.py` を修正（独立プロセス実行）
3. [ ] `merge_cuts.py` を新規作成（レンダリング合成用）
4. [ ] テスト: 各カットを個別に実行して`.blend`生成を確認
5. [ ] テスト: `run.py all` で全カットを独立実行
6. [ ] テスト: レンダリング合成の確認

## 技術的注意点

- `CutState` の位置情報継承は維持（フレーム0の初期位置として使用）
- 各プロセスはクリーンなBlenderセッションから開始
- ファイル保存時は `bpy.ops.wm.save_as_mainfile(filepath=...)` を使用
- レンダリング合成はフレームオフセットを考慮して連結
