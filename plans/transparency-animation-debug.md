# 半透明化アニメーション問題 - 試行履歴と解決策

## 概要
CarBの半透明化を徐々に効かせるアニメーションが動作しない問題を記録する。

## 環境
- Blender 5.2
- EEVEEレンダリングエンジン（レイトレーシング有効）
- Python API (bpy)

---

## 試行履歴

### 試行 #1: ドライバー式方式（animation_common.py `_setup_transparency_animation`）
**日付**: 2026-08-20
**方法**: Principled BSDFのAlpha入力にドライバーを追加し、フレーム番号からAlpha値を計算
**結果**: ❌ 失敗 - 半透明化が効かない

**原因分析**:
- Blender 5.xでNodeTreeのアニメーションが正しく評価されない
- ドライバー式がレンダリング時に無視される可能性

### 試行 #2: キーフレーム直接設定方式（animation_common.py `_setup_transparency_keyframe_animation` v1）
**日付**: 2026-08-20
**方法**: Alpha値を直接書き換えて`keyframe_insert`でキーフレームを挿入
**結果**: ❌ 失敗 - フレーム40ですでに半透明になっているが、徐々に変化しない

**原因分析**:
- `blend_scene_creator.py:1082-1092` でテキストラベル作成時に `_apply_clay_to_all_meshes` がマテリアルを再適用
- キーフレームが上書きされる
- NodeTreeのアニメーションデータがBlender 5.xで正しく動作しない

### 試行 #3: Mix Shader Fac方式 v1（animation_common.py `_setup_transparency_keyframe_animation` v2）
**日付**: 2026-08-20
**方法**:
- マテリアルノードをMix Shader + Transparent BSDF + Principled BSDFの構成に再構築
- Mix ShaderのFac（混合比率）にキーフレームを設定
- Fac = 1.0で完全不透明、Fac = 0.0で完全透明

**結果**: ❌ 失敗 - CarBが消える
**原因分析**:
- Mix Shaderの接続順序が逆になっていた
- input[1] = Principled BSDF（車）、input[2] = Transparent BSDF（透明）
- Fac = 1.0 で Transparent BSDF が効いてしまい、CarBが消える

### 試行 #4: Mix Shader Fac方式 v2（接続順序修正）
**日付**: 2026-08-20
**方法**:
- Mix Shaderの接続順序を逆に変更
- input[1] = Transparent BSDF（透明）、input[2] = Principled BSDF（車）
- Fac = 1.0 で完全不透明、Fac = 0.35 で半透明

**結果**: ⚠️ CarBは表示されるが、急に半透明になる（徐々に変化しない）

### 試行 #5: Mix Shader Fac方式 v3（フレーム0キーフレーム+LINEAR）
**日付**: 2026-08-20
**方法**:
- フレーム0に完全不透明のキーフレームを追加
- インターポレーションをLINEARに設定

**結果**: ❌ 失敗 - いきなり半透明になる（レンダリング出力でも同じ）

---

## 根本原因の特定

### Blender 5.x の NodeTree アニメーション問題
Blender 5.x では、マテリアルノードツリーのアニメーションデータがビューポートで正しく評価されない。

- `keyframe_insert(data_path="default_value", frame=frame)` でキーフレームは挿入される
- しかしビューポート再生時にキーフレームが interpolation されず、最初の値のまま表示される
- **レンダリング出力でも急に半透明になる** → キーフレーム自体が正しく設定されていない

### 検証方法
Blender のシェーダーエディタで Mix Shader ノードを選択し、プロパティパネルで Fac の F-Curve が存在するか確認する必要がある。

---

## 技術的制約

### Blender 5.x のNodeTreeアニメーション問題
1. `alpha_input.keyframe_insert(data_path="default_value", frame=frame)` が正しく動作しない
2. ドライバー式がレンダリング時に評価されない
3. `_apply_clay_to_all_meshes` がマテリアルを再適用するとキーフレームが消える

### 実行順序の問題
`blend_scene_creator.py` の実行順序:
1. アニメーション設定（半透明化キーフレーム設置）
2. テキストラベル作成（`_apply_clay_to_all_meshes`でマテリアル上書き）→ **ここが問題**

### 重要な確認事項
- **ユーザーは常にレンダリング出力（MP4）で確認している**
- ビューポートだけでなく、レンダリングでも急に半透明になる
- つまり、キーフレーム自体が正しく設定されていない、または interpolation が効いていない

### 新たな仮説
1. Mix Shader の Fac にキーフレームが挿入されているが、何らかの理由で interpolation されない
2. `bpy.context.scene.frame_set()` が NodeTree のアニメーション評価に影響している
3. 同じマテリアルを複数のメッシュで共有している場合、キーフレームが競合している可能性
4. Blender 5.x の NodeTree アニメーションは `keyframe_insert` では正しく動作しない可能性がある

---

## 次のアプローチ

### 試すべきこと
1. オブジェクトのカスタムプロパティに値を持たせ、それを Mix Shader の Fac にドライバーで接続する
2. または、スクリプトで毎フレーム評価される方式に変更する
3. ドライバー式をオブジェクトレベルのプロパティに接続し、ノードツリー経由ではなく直接制御する

---

## 更新履歴
| 日付 | 変更内容 | 状態 |
|------|---------|------|
| 2026-08-20 | ドライバー式方式を試す | ❌ 失敗 |
| 2026-08-20 | キーフレーム直接設定方式を試す | ❌ 失敗 |
| 2026-08-20 | Mix Shader Fac方式 v1（接続順序ミス） | ❌ 失敗 |
| 2026-08-20 | Mix Shader Fac方式 v2（接続順序修正） | ⚠️ CarB表示OKだが急に半透明 |
| 2026-08-20 | Mix Shader Fac方式 v3（フレーム0キーフレーム+LINEAR） | ❌ 失敗 - いきなり半透明 |
