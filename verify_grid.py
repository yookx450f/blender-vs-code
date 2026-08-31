"""すべての .blend の CyberGrid サイズを検証する（Blender --background 経由）
期待値（仕様確定 2026-08-29）:
  - short-s   : X幅 ±5m (span=10) × Y長 GOAL(Y=-100)まで → span≈240（道状グリッド、維持）
  - それ以外  : xy座標(原点)中心の20m四方正方形 → X幅 span=20 / Y長 span=20
"""
import subprocess

BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
CHECK_EXPR = (
    "import bpy; from mathutils import Vector as V; g=bpy.data.objects.get('CyberGrid'); "
    "xs=[(g.matrix_world @ V(c)).x for c in g.bound_box]; ys=[(g.matrix_world @ V(c)).y for c in g.bound_box]; "
    "print('GRIDRESULT', round(min(xs),1), round(max(xs),1), round(min(ys)), round(max(ys)))"
)

files = ["cut1_scene.blend", "cut2_scene.blend", "cut3_scene.blend",
         "cut4_scene.blend", "cut4b_scene.blend", "cut5_scene.blend",
         "short_scene.blend", "short2_scene.blend", "short_s_scene.blend"]

all_ok = True
for f in files:
    is_short_s = (f == "short_s_scene.blend")
    # short-s: 道幅±5m×Y長±120m / それ以外: xy座標中心の20m四方(±10m)
    expected_x_span = 10.0 if is_short_s else 20.0
    expected_y_span = 240.0 if is_short_s else 20.0
    r = subprocess.run([BLENDER, "--background", f, "--python-expr", CHECK_EXPR],
                       capture_output=True, text=True)
    out = (r.stdout or "") + "\n" + (r.stderr or "")
    lines = [l for l in out.splitlines() if "GRIDRESULT" in l]
    if not lines:
        print(f"  ✗ {f}: GRID情報を取得できませんでした")
        all_ok = False
        continue

    xmin, xmax, ymin, ymax = (float(v) for v in lines[0].replace("GRIDRESULT", "").split())
    x_span = round(xmax - xmin, 1)
    y_span = abs(ymax - ymin)
    x_ok = (abs(x_span - expected_x_span) < 1e-6)
    y_ok = (abs(y_span - expected_y_span) < 1e-6)
    ok = x_ok and y_ok
    all_ok &= ok
    label = "（期待: X=10, Y=240 / short-sの道状グリッド）" if is_short_s else "（期待: X=20, Y=20 / 20m四方グリッド）"
    print(f"  {'✓' if ok else '✗'} {f}: X幅={x_span:.1f}m [{xmin:+.1f},{xmax:+.1f}] / Y長={y_span:.1f}m [{ymin:+.0f},{ymax:+.0f}] {label}")

print()
if all_ok:
    print("=== 検証結果: 全カット PASS（short-s=道状X±5m×Y±120m / それ以外=原点中心の20m四方グリッド）===")
else:
    print("=== 検証結果: NGあり ===")
