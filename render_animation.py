import bpy

# アニメーションレンダリングを実行（EEVEE）
print("=== アニメーションレンダリング開始 (EEVEE) ===")
bpy.ops.render.render(animation=True)
print("アニメーションレンダリング完了！")
