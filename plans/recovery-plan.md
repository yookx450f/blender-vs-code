# 回復計画 - スライドアニメーション破損の修正

## 根本原因
`animation_settings_cut4.py:257-260` の `animation_data_clear()` がカット1-3で設定された全アニメーションキーフレームを消去している。

## 実行フローの問題
```
setup_cut1_animations()    → キーフレーム設定 (フレーム0-648)
   ↓
setup_cut2_animations()    → キーフレーム継承・拡張
   ↓
setup_cut3_animations()    → キーフレーム継承・拡張
   ↓
setup_cut4_animations()    → animation_data_clear() 実行！！！全キーフレーム消去
```

---

## 段階1: カット分離による即座回復

### 変更ファイル: `animation_settings.py`
- `CUT_NUMBER` 環境変数を確認
- 指定されたカット番号に応じて必要なカットのみを実行
- `python run.py 1` → カット1のみ実行（カット4の破損処理がスキップ）

### 期待結果
- スライドアニメーションが回復
- フレーム0-96で車が正常に移動

---

## 段階2: オフセット計算ロジックの整理

### 変更ファイル: `animation_settings_cut1.py`
- `pivot_offset` 補正ロジックを簡素化
- カット1単独実行時は親オブジェクトが存在しないため、不要な補正を削除
- 画面が左側によれている問題を修正

---

## 段階3: 全カット実行時の対応（オプション）

### 変更ファイル: `animation_settings_cut4.py`
- `animation_data_clear()` の代わりに選択的キーフレーム削除を検討
- Empty親設定後に車のローカル座標でキーフレームを再設定

---

## テスト手順
1. `python run.py 1` でカット1単独実行 → スライドアニメーション確認
2. フレーム96で車がX=0に収束するか確認
3. 画面中央配置の確認
