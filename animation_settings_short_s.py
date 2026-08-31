import bpy
import math
import os
from mathutils import Vector, Matrix

SS_FPS = 24.0
SS_LAUNCH_FRAME = int(SS_FPS * 3.0)       # フレーム72: 発车时刻（その前=停止中）
SS_GOAL_Y = -100.0
SS_V_MAX = (100.0 / 3.6)                  # m/s、100km/hの速度上限

def _ss_clamp_accel(s):
    return max(float(s), 0.5)


def ss_distance(t, accel_s):
    if t <= 0.0:
        return 0.0
    T = _ss_clamp_accel(accel_s)
    a = SS_V_MAX / T
    dmax = 0.5 * a * T * T               # (=SS_V_MAX*T/2)
    if t <= T:
        return 0.5 * a * t * t
    return dmax + SS_V_MAX * (t - T)


def ss_arrival_frame(start_y, accel_s):
    D = max(float(start_y) - SS_GOAL_Y, 1e-6)
    T = _ss_clamp_accel(accel_s)
    a = SS_V_MAX / T
    dmax = 0.5 * a * T * T
    if D <= dmax:
        ta = math.sqrt((2.0 * D) / a)
    else:
        ta = T + (D - dmax) / SS_V_MAX
    return int(round(SS_LAUNCH_FRAME + ta * SS_FPS))


def ss_anim_end_frame(ay, by, aa, ba):
    fmax = max(ss_arrival_frame(ay, aa), ss_arrival_frame(by, ba))
    return max(int(fmax + SS_FPS * 3.0), int(SS_LAUNCH_FRAME + SS_FPS * 5.0))


_SS_TIMERS = []         # タイマー管理（_ss_frame_update毎フレーム参照）
_CD_STATE = {}          # カウントダウン（両車共通の大きな表示・1つ）
def _ss_car_info(co):
    # update_tag のみで view_layer.update() はスキップ（depsgraph競合回避）
    co.update_tag()
    cs = [co.matrix_world @ Vector(c) for c in co.bound_box]
    cx=(min(v.x for v in cs)+max(v.x for v in cs))/2.0
    cy=(min(v.y for v in cs)+max(v.y for v in cs))/2.0
    return cx, cy, max(c.z for c in cs)

def _ss_bold_font():
    p=r'C:\Windows\Fonts\mebold.ttc'
    if os.path.exists(p):
        for fd in bpy.data.fonts:
            if (fd.name or '').lower().startswith('mebold'): return fd
        try: return bpy.data.fonts.load(p)
        except RuntimeError: pass
    return None

def _make_emission_mat(name, color_rgba, strength):
    if name in bpy.data.materials:
        m=bpy.data.materials[name]
        n=next((x for x in m.node_tree.nodes if getattr(x,'type','')=='EMISSION'),None)
        if n is not None: return m,n
    m=bpy.data.materials.new(name=name); m.use_nodes=True
    nd=m.node_tree.nodes; lk=m.node_tree.links
    for o in list(nd): nd.remove(o)
    out=nd.new(type='ShaderNodeOutputMaterial')
    emi=nd.new(type='ShaderNodeEmission')
    emi.inputs['Color'].default_value=color_rgba
    emi.inputs['Strength'].default_value=strength
    lk.new(emi.outputs[0],out.inputs['Surface'])
    return m,emi


def _make_smoke_material(name, color_rgb, strength, alpha):
    """スモーク用マテリアル。Mix Shader + Principled BSDF(Alpha) + Emission を組み合わせる。
    半透明の白い煙表現のために Principled BSDF の Alpha を使用し、
    発光感のために Emission を Mix する。
    Returns (material, emission_node, principled_node) タプル"""
    if name in bpy.data.materials:
        m = bpy.data.materials[name]
        if m.use_nodes:
            emi = next((x for x in m.node_tree.nodes if getattr(x,'type','')=='EMISSION'), None)
            pr  = next((x for x in m.node_tree.nodes if getattr(x,'name','')=='Principled BSDF'), None)
            if emi is not None and pr is not None:
                return m, emi, pr

    m = bpy.data.materials.new(name=name)
    m.use_nodes = True
    if hasattr(m, 'blend_method'): m.blend_method = 'BLEND'     # 半透明描画有効化 (EEVEE/Blend4.x)
    if hasattr(m, 'shadow_method'): m.shadow_method = 'NONE'   # スモークはシャドウ不要

    nd = m.node_tree.nodes
    lk = m.node_tree.links
    for o in list(nd):
        nd.remove(o)

    out = nd.new(type='ShaderNodeOutputMaterial')
    mix = nd.new(type='ShaderNodeMixShader')
    emi = nd.new(type='ShaderNodeEmission')
    pr  = nd.new(type='ShaderNodeBsdfPrincipled')

    # Blenderのノード入力はRGBA (4要素) を要求するので RGB → RGBA に変換
    color_rgba = list(color_rgb) + [1.0]

    # Emission ノード設定
    emi.inputs['Color'].default_value = color_rgba
    emi.inputs['Strength'].default_value = strength

    # Principled BSDF - Alpha で透明度制御
    pr.inputs['Base Color'].default_value = color_rgba
    pr.inputs['Alpha'].default_value = alpha
    pr.inputs['Roughness'].default_value = 1.0   # 完全な拡散（鏡面反射なし）

    # Mix Shader の因子 = Emission のウェイト
    # Factor=0 -> Principled BSDFのみ(より半透明)、Factor=1 -> Emissionのみ(不透明)
    # 0.3 に設定して Principled BSDF(Apha=0.2)を主体にし、Emissionは僅かな発光感にとどめる
    mix.inputs['Fac'].default_value = 0.3
    lk.new(mix.outputs['Shader'], out.inputs['Surface'])
    lk.new(pr.outputs['BSDF'], mix.inputs[1])     # A = Principled BSDF
    lk.new(emi.outputs['Emission'], mix.inputs[2]) # B = Emission

    return m, emi, pr


def _ss_frame_update(scene):
    """毎フレーム呼び出されるハンドラ。
    レンダリング中はdepsgraph競合を避けるためスキップする。"""
    # レンダリング中/バックグラウンドモードではスキップ（クラッシュ回避）
    if bpy.app.background:
        return
    try:
        f = scene.frame_current
        if not _SS_TIMERS:
            return
        for ti in _SS_TIMERS:
            oname = ti['obj_name']
            if oname not in bpy.data.objects:
                continue
            tobj = bpy.data.objects[oname]
            ef = f - ti['launch_frame']
            tmat = ti.get('tmat')
            gmat = ti.get('gmat')
            goal_passed = ti.get('goal_passed', False)
            show_threshold = -999999  # 最初（フレーム0）から常に表示
            
            if not goal_passed:
                # ゴール位置到達チェック (車のY < SS_GOAL_Y ?)
                car_name = ti.get('car_ref', '')
                start_y = ti.get('start_y', 0.0)
                accel_s = ti.get('accel_s', 9.4)
                current_dist = ss_distance(ef / SS_FPS if ef > 0 else 0.0, accel_s)
                car_y = start_y - current_dist
                
                if car_y <= SS_GOAL_Y and ef > 0:
                    # ゴール位置通過！親を外して固定表示
                    ti['goal_passed'] = True
                    es = round(ef / SS_FPS * 10) / 10.0
                    ti['final_time'] = "{:.1f}s".format(es)
                    
                    car_key = ti.get('car_key', 'carB')
                    goal_x = -1.5 if car_key == 'carA' else 1.5
                    
                    # タイマー: 親を解除してゴール位置に移動
                    if tobj.parent:
                        world_mat = tobj.matrix_world.copy()
                        tobj.parent = None
                        tobj.matrix_world = world_mat
                    
                    tobj.location.y = SS_GOAL_Y + 2.0
                    tobj.location.x = goal_x
                    timer_z = tobj.location.z
                    
                    # 車名テキスト: 親を解除して可視化、ゴール位置に移動
                    name_obj_name = ti.get('name_obj_name')
                    if name_obj_name and name_obj_name in bpy.data.objects:
                        nobj = bpy.data.objects[name_obj_name]
                        if nobj.parent:
                            nworld_mat = nobj.matrix_world.copy()
                            nobj.parent = None
                            nobj.matrix_world = nworld_mat
                        nobj.location.y = SS_GOAL_Y + 2.0
                        nobj.location.x = goal_x
                        # 車名のZ位置（フォントを下げて、Z方向に上げる）
                        name_z_offset = 1.0 if car_key == 'carA' else 1.6
                        nobj.location.z = timer_z + name_z_offset
                        # マテリアルを可視化
                        nmat_name = "emission_name_" + car_key
                        if nmat_name in bpy.data.materials:
                            mat = bpy.data.materials[nmat_name]
                            if hasattr(mat, 'node_tree'):
                                nodes = mat.node_tree.nodes
                                emi = next((n for n in nodes if getattr(n,'type','')=='EMISSION'), None)
                                if emi and hasattr(emi, 'inputs'):
                                    emi.inputs['Strength'].default_value = 6.0
                                    # CarBは青に光らせる
                                    if car_key == 'carB':
                                        emi.inputs['Color'].default_value = (0.0, 0.7, 1.0, 1.0)
                
                # タイマー表示更新
                if ef < show_threshold:
                    tobj.data.body = ""
                    if tmat and hasattr(tmat, 'node_tree'):
                        nodes = tmat.node_tree.nodes
                        emi = next((n for n in nodes if getattr(n,'type','')=='EMISSION'), None)
                        if emi and hasattr(emi, 'inputs'):
                            emi.inputs['Strength'].default_value = 0.0
                else:
                    if ef < 0:
                        tobj.data.body = "0.0s"
                    else:
                        es = round(ef / SS_FPS * 10) / 10.0
                        tobj.data.body = "{:.1f}s".format(es)
                    if tmat and hasattr(tmat, 'node_tree'):
                        nodes = tmat.node_tree.nodes
                        emi = next((n for n in nodes if getattr(n,'type','')=='EMISSION'), None)
                        if emi and hasattr(emi, 'inputs'):
                            emi.inputs['Strength'].default_value = 6.0
            else:
                # ゴール通過後: 秒数を固定表示
                tobj.data.body = ti.get('final_time', '')
        # カウントダウン演出の更新（_CD_STATEから）
        cd = _CD_STATE
        if not cd or 'obj' not in cd:
            return
        cob = cd.get('obj')
        if cob and cob in bpy.data.objects:
            txt = bpy.data.objects[cob]
            phase = cd.get('phase', 'countdown')       # countdown | start_fade | faded
            base_strength = cd.get('base_strength', 8.0)
            node = cd.get('node')
            
            if phase == 'countdown':
                remain = SS_LAUNCH_FRAME - f
                if remain > 48:
                    txt.data.body = "3"
                elif remain > 24:
                    txt.data.body = "2"
                elif remain > 0:
                    txt.data.body = "1"
                else:
                    _CD_STATE['phase'] = 'start_fade'
                    txt.data.body = "START"
            elif phase == 'start_fade':
                # STARTから2秒後(72フレーム)でフェードアウト開始
                elapsed = f - SS_LAUNCH_FRAME
                if elapsed < 72:
                    # 2秒間 START を表示
                    pass
                else:
                    # フェードアウト (約1秒=24フレームで消える)
                    fade_elapsed = elapsed - 72
                    fade_duration = 24  # 1秒
                    if fade_elapsed < fade_duration:
                        alpha = max(0.0, 1.0 - fade_elapsed / fade_duration)
                        if node and hasattr(node, 'inputs'):
                            node.inputs['Strength'].default_value = base_strength * alpha
                    else:
                        # 完全に表示なし（スケールを0に）
                        if node and hasattr(node, 'inputs'):
                            node.inputs['Strength'].default_value = 0.0
    except Exception:
        pass



def _ss_smoke_cluster(car_obj, car_key):
    """仕様2-2-1: タイヤと地面の摩擦で白い煙が巻き上がる。
    半透明表示。スタート直後に表示開始、1秒(24fr)で30倍に拡大、その後2秒(48fr)かけて透明になる。"""
    co = _ss_car_info(car_obj)
    cx, cy, top_z = co[0], co[1], co[2]
    
    # 車の全長・全幅を取得
    world_ys = [v.y for v in [car_obj.matrix_world @ Vector(b) for b in car_obj.bound_box]]
    world_xs = [v.x for v in [car_obj.matrix_world @ Vector(b) for b in car_obj.bound_box]]
    car_length = max(world_ys) - min(world_ys)
    car_width = max(world_xs) - min(world_xs)
    
    # 後輪位置（Y+側=車の後方）
    rear_y = max(world_ys) + 0.5
    
    _SMOKE_NODES = getattr(_ss_smoke_cluster, '_smoke_nodes', [])
    
    def _add_smoke(idx, sx, sy, sz):
        """スモーク球を追加し、Mix Shader(Principled BSDF+Emission)で半透明煙を生成"""
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(sx, sy, sz))
        sp = bpy.context.active_object
        sp.name = f"smoke_{car_key}_{idx}"
        mat_nm = "smoke_mat_%s_%d" % (car_key, idx)
        smat, snode_emi, snode_pr = _make_smoke_material(mat_nm, (1.0, 1.0, 1.0), 3.0, 0.2)
        sp.data.materials.clear()
        sp.data.materials.append(smat)
        
        # 初期スケール=小さい（スタートから表示開始）
        base_scale = 0.12 + idx * 0.01
        sp.scale = (0.001, 0.001, 0.001)  # スタート前は不可視
        sp.keyframe_insert("scale", index=-1, frame=SS_LAUNCH_FRAME - 1)
        
        sp.scale = (base_scale, base_scale, base_scale)  # スタート直後に小さく表示
        sp.keyframe_insert("scale", index=-1, frame=SS_LAUNCH_FRAME)
        
        # 1秒(24fr)で30倍に拡大
        big_scale = base_scale * 30.0
        sp.scale = (big_scale, big_scale, big_scale)
        sp.keyframe_insert("scale", index=-1, frame=SS_LAUNCH_FRAME + 24)
        
        # さらに24fr後に小さくなる
        sp.scale = (base_scale * 0.3, base_scale * 0.3, base_scale * 0.3)
        sp.keyframe_insert("scale", index=-1, frame=SS_LAUNCH_FRAME + 72)
        sp.scale = (base_scale, base_scale, base_scale)
        
        # Emissionノード + Principled BSDFノードをリストに登録（ハンドラで両方制御）
        _SMOKE_NODES.append({'node_emi': snode_emi, 'node_pr': snode_pr, 'obj_name': sp.name})
    
    smoke_idx = 0
    
    # === 後方に6個のクラスター ===
    for i in range(6):
        angle = math.radians(i * 60)
        off_x = 0.4 * math.cos(angle)
        off_z = 0.1 + 0.15 * max(0, math.sin(angle))
        sx = cx + off_x
        sy = rear_y + (i % 3 - 1) * 0.2
        sz = car_obj.location.z + off_z
        _add_smoke(smoke_idx, sx, sy, sz)
        smoke_idx += 1
    
    # === 左側輪の近くに3個（車に0.5m近づける + 進行方向に1mずらす）===
    left_x = min(world_xs) - 0.8   # 車の左側（X-方向）外側に0.8m
    for i in range(3):
        off_y = rear_y - 1.0 - (i * 0.25)   # 進行方向(Y-)に1mずらす + 前後分散
        off_z = 0.1 + i * 0.08
        sx = left_x
        sy = off_y
        sz = car_obj.location.z + off_z
        _add_smoke(smoke_idx, sx, sy, sz)
        smoke_idx += 1
    
    # === 右側輪の近くに3個（車に0.5m近づける + 進行方向に1mずらす）===
    right_x = max(world_xs) + 0.8   # 車の右側（X+方向）外側に0.8m
    for i in range(3):
        off_y = rear_y - 1.0 - (i * 0.25)
        off_z = 0.1 + i * 0.08
        sx = right_x
        sy = off_y
        sz = car_obj.location.z + off_z
        _add_smoke(smoke_idx, sx, sy, sz)
        smoke_idx += 1
    
    _ss_smoke_cluster._smoke_nodes = _SMOKE_NODES

def _ss_attach_lights(car_a, car_b):
    for co in (car_a, car_b):
        if hasattr(co, 'name') and co.name:
            nm = co.name + "_Light"
            bpy.ops.object.light_add(type='AREA', location=(0, 0, 0))
            li = bpy.context.active_object; li.name = nm
            li.data.energy = 200; li.data.size = 3
            if hasattr(li.data, 'distance'): li.data.distance = 0
            if hasattr(li.data, 'use_custom_distance'): li.data.use_custom_distance = False
            co.select_set(True); bpy.context.view_layer.objects.active = co
            li.parent = co; li.location = (0.0, 0.0, 3.0)
            li.rotation_euler = (-math.pi / 4, 0.0, 0.0)

def _ss_create_goal_text(rear_offset_y, gz):
    bpy.ops.object.text_add(location=(0.0, SS_GOAL_Y, 2.0))
    gt = bpy.context.active_object; gt.name = "GoalText"
    gt.data.body = "GOAL"; gt.data.size = 1.5; gt.scale = (2.0, 2.0, 2.0)
    gt.data.align_x = 'CENTER'
    gt.location = (0.0, SS_GOAL_Y, 0.01)
    mat_nm = "emission_goal"
    gmat, gnode = _make_emission_mat(mat_nm, (1.0, 1.0, 1.0, 1.0), 10.0)
    gt.data.materials.clear(); gt.data.materials.append(gmat)

def _ss_create_timer(car_obj, car_key, sy, accel_s, gz, anim_end):
    cx, cy, top_z = _ss_car_info(car_obj)
    goal_f = ss_arrival_frame(sy, accel_s)
    tz = top_z + (0.4 if car_key == "carA" else 0.6)
    tmat, tnode = _make_emission_mat("emission_timer_" + car_key, (1.0, 1.0, 0.0, 1.0), 6.0)
    gmat, gnode = _make_emission_mat("emission_timer_" + car_key + "_goal", (0.2, 1.0, 0.2, 1.0), 5.0)
    fd = _ss_bold_font()
    
    # タイマーテキスト
    bpy.ops.object.text_add(location=(0, 0, 0))
    tobj = bpy.context.active_object; tobj.name = "timer_" + car_key
    tobj.data.body = "0.0s"; tobj.data.size = 0.5; tobj.data.extrude = 0.03
    tobj.data.align_x = 'CENTER'; tobj.data.align_y = 'CENTER'
    if fd: tobj.data.font = fd
    tobj.data.materials.clear(); tobj.data.materials.append(tmat)
    tobj.parent = car_obj
    rx = Matrix.Rotation(math.pi / 2, 4, 'X')
    tx = Matrix.Translation((cx, cy, tz))
    tobj.matrix_world = tx @ rx
    
    # 車名テキスト（事前に作成、初期は不可視）
    car_name_text = car_obj.name.split('_', 1)[-1] if '_' in car_obj.name else car_obj.name
    name_obj_name = "name_" + car_key
    bpy.ops.object.text_add(location=(0, 0, 0))
    nobj = bpy.context.active_object; nobj.name = name_obj_name
    nobj.data.body = car_name_text; nobj.data.size = 0.3; nobj.data.extrude = 0.02
    nobj.data.align_x = 'CENTER'; nobj.data.align_y = 'CENTER'
    if fd: nobj.data.font = fd
    # タイマーと同じ向き（X軸で90度回転）に設定
    nrx = Matrix.Rotation(math.pi / 2, 4, 'X')
    mtx = Matrix.Translation((cx, cy, tz + 1.0))
    nobj.matrix_world = mtx @ nrx
    # マテリアル
    nmat, nnode = _make_emission_mat("emission_name_" + car_key, (1.0, 0.95, 0.75, 1.0), 6.0)
    nobj.data.materials.clear(); nobj.data.materials.append(nmat)
    # 初期は不可視（Strength=0）
    nnode.inputs['Strength'].default_value = 0.0
    nobj.parent = car_obj  # 親として車に追従させる
    
    _SS_TIMERS.append({
        'obj_name': tobj.name,
        'launch_frame': SS_LAUNCH_FRAME,
        'goal_frame': goal_f,
        'tmat': tmat,
        'gmat': gmat,
        'car_key': car_key,  # "carA" or "carB"
        'car_name': car_name_text,
        'car_ref': car_obj.name,
        'goal_passed': False,
        'final_time': '',
        'start_y': sy,
        'accel_s': accel_s,
        'name_obj_name': name_obj_name,
    })

def _ss_create_countdown(car_a, car_b):
    """カウントダウンテキストを固定位置に配置（親なし）
    ※ frame=0で車の初期位置を確認した直後に呼び出すこと"""
    # 「0-100加速対決」テキストをカウントダウンの上に配置
    title_x = 0.25756   # カウントダウンと同じX位置
    title_y = 1.0       # カウントダウンと同じY位置
    title_z = 6.3       # カウントダウンより上
    
    title_mat_nm = "emission_countdown_title"
    title_mat, title_node = _make_emission_mat(title_mat_nm, (1.0, 0.95, 0.75, 1.0), 8.0)
    fd = _ss_bold_font()
    bpy.ops.object.text_add(location=(0, 0, 0))
    title_txt = bpy.context.active_object; title_txt.name = "countdown_title"
    title_txt.data.body = "0-100加速対決"; title_txt.data.size = 1.2; title_txt.data.extrude = 0.08
    title_txt.data.align_x = 'CENTER'; title_txt.data.align_y = 'TOP'
    if fd: title_txt.data.font = fd
    trx = Matrix.Rotation(math.pi / 2, 4, 'X')
    ttx = Matrix.Translation((title_x, title_y, title_z))
    title_txt.matrix_world = ttx @ trx
    title_txt.data.materials.clear(); title_txt.data.materials.append(title_mat)
    
    # カウントダウンは両車の前方・手前に大きく配置
    cd_x = 0.25756   # 両車の中央寄り
    cd_y = 1.0       # 車の手前
    cd_z = 4.5       # 高位置
    
    mat_nm = "emission_countdown_main"
    cmat, cnode = _make_emission_mat(mat_nm, (0.0, 0.7, 1.0, 1.0), 8.0)
    fd = _ss_bold_font()
    bpy.ops.object.text_add(location=(0, 0, 0))
    txt = bpy.context.active_object; txt.name = "countdown_main"
    txt.data.body = "3"; txt.data.size = 1.8; txt.data.extrude = 0.15
    txt.data.align_x = 'CENTER'; txt.data.align_y = 'TOP'
    if fd: txt.data.font = fd
    rx = Matrix.Rotation(math.pi / 2, 4, 'X')
    tx = Matrix.Translation((cd_x, cd_y, cd_z))
    txt.matrix_world = tx @ rx
    # 親を設定しない → スタート位置に固定配置（車と一緒に移動しない）
    txt.data.materials.clear(); txt.data.materials.append(cmat)
    _CD_STATE['obj'] = txt.name; _CD_STATE['node'] = cnode; _CD_STATE['base_strength'] = 8.0
    _CD_STATE['phase'] = 'countdown'




def setup_short_s_animations(scene, camera, imported_cars, rear_offset_y, grounded_z_positions, car_dimensions=None):
    print("\n=== short-s アニメーション設定(仕様「２．構成」準拠) ===")
    car_a = imported_cars.get("carA")
    car_b = imported_cars.get("carB")
    if not car_a or not car_b:
        print("エラー: carA/carB が見つかりません")
        return None
    gz_a = grounded_z_positions.get(car_a.name, car_a.location.z)
    gz_b = grounded_z_positions.get(car_b.name, car_b.location.z)
    acd = {} if not car_dimensions else (car_dimensions.get("carA") or {})
    bcd = {} if not car_dimensions else (car_dimensions.get("carB") or {})
    aa = acd.get("acceleration_0_to_100_km_h", 9.4)
    ba = bcd.get("acceleration_0_to_100_km_h", 6.7)
    anim_end = ss_anim_end_frame(0, rear_offset_y, aa, ba)
    print(f"  anim_end={anim_end} (車A加速{aa}s/車B加速{ba}s)")

    cam_loc = (0.0, -8.0, 10.0)
    camera.location = cam_loc
    if hasattr(camera.data, 'lens'):
        camera.data.lens = 35
    sa = (-1.5, rear_offset_y, gz_a)
    sb = (1.5, 0.0, gz_b)
    car_a.location = sa
    car_b.location = sb
    car_a.rotation_euler = (0.0, 0.0, -math.pi / 2)
    car_b.rotation_euler = (0.0, 0.0, -math.pi / 2)

    scene.frame_set(0)
    bpy.context.view_layer.update()
    
    # ★ 演出オブジェクトはframe=0（車の初期位置）の直後に作成
    # これにより bound_box が正しい初期座標を指す（ゴール位置にならない）
    _ss_create_countdown(car_a, car_b)
    _ss_attach_lights(car_a, car_b)
    _ss_smoke_cluster(car_a, "carA")
    _ss_smoke_cluster(car_b, "carB")
    _ss_create_timer(car_a, "carA", sa[1], aa, gz_a, anim_end)
    _ss_create_timer(car_b, "carB", sb[1], ba, gz_b, anim_end)

    car_a.keyframe_insert("location", frame=0)
    car_b.keyframe_insert("location", frame=0)
    car_a.keyframe_insert("rotation_euler", frame=0)
    car_b.keyframe_insert("rotation_euler", frame=0)

    # --- カメラ構成 (仕様「３．カメラ構成」準拠) ---
    # Blenderのカメラは前方=-Z, 上=Y なので to_track_quat('-Z', 'Y') を使用する
    avg_y_init = (sa[1] + sb[1]) / 2.0

    # カメラ初期位置: Z=8m、両車の中央
    cam_x_start = 0.0
    cam_y_start = avg_y_init - 8.0
    cam_z_start = 8.0
    camera.location = Vector((cam_x_start, cam_y_start, cam_z_start))
    target_init = Vector((0.0, avg_y_init - 3.0, 1.5))
    dir_to_target = (target_init - camera.location).normalized()
    rot_q_init = dir_to_target.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_q_init.to_euler()
    camera.keyframe_insert("location", frame=0)
    camera.keyframe_insert("rotation_euler", frame=0)

    bpy.ops.object.select_all(action='DESELECT')
    for en in ("CarA_TurnPivot", "CarB_TurnPivot"):
        if en in bpy.data.objects:
            o = bpy.data.objects[en]
            o.select_set(True)
            bpy.ops.object.delete()
    bpy.ops.object.select_all(action='DESELECT')

    # idle期(0-71): 停止中はフレーム0と発车直前の2点で位置固定
    car_a.location = sa
    car_b.location = sb
    car_a.keyframe_insert("location", frame=SS_LAUNCH_FRAME - 1)
    car_b.keyframe_insert("location", frame=SS_LAUNCH_FRAME - 1)

    # 【3-1】フレーム71: Z=2mまで下げる、Yを-5m移動、Xを-5m移動
    cam_z_p1 = 2.0
    cam_y_p1 = cam_y_start - 5.0   # Y方向に-5m
    cam_x_p1 = cam_x_start - 5.0   # X方向に-5m
    camera.location = Vector((cam_x_p1, cam_y_p1, cam_z_p1))
    center_idle = Vector(((sa[0]+sb[0])/2.0, avg_y_init, 1.5))
    dir_idle = (center_idle - camera.location).normalized()
    rot_q_idle = dir_idle.to_track_quat('-Z', 'Y')
    camera.rotation_euler = rot_q_idle.to_euler()
    # カメラの移動を1秒遅らせる（Frame84までゆっくり移動）
    cam_delay_frames = int(1.0 * SS_FPS)  # 12フレーム = 1秒
    camera.keyframe_insert("location", frame=SS_LAUNCH_FRAME + cam_delay_frames - 1)
    camera.keyframe_insert("rotation_euler", frame=SS_LAUNCH_FRAME + cam_delay_frames - 1)

    # 走行期(72-anim_end): 定加速度モデルで位置を計算・キーフレーム設定
    nframes = anim_end - SS_LAUNCH_FRAME + 1
    for i in range(nframes):
        fr = SS_LAUNCH_FRAME + i
        t_s = i / SS_FPS
        da = ss_distance(t_s, aa)
        db = ss_distance(t_s, ba)
        car_a.location = (sa[0], sa[1] - da, sa[2])
        car_b.location = (sb[0], sb[1] - db, sb[2])
        car_a.keyframe_insert("location", frame=fr)
        car_b.keyframe_insert("location", frame=fr)

    # ── カメラ速度計算用パラメータ ──
    T_a = _ss_clamp_accel(aa)  # 車Aの0-100加速時間[s]
    T_b = _ss_clamp_accel(ba)  # 車Bの0-100加速時間[s]
    a_max = SS_V_MAX / T_a     # 車Aの最大加速度[m/s²]
    b_max = SS_V_MAX / T_b     # 車Bの最大加速度[m/s²]

    def _car_speed(car_T, car_acc, t):
        """車の進行速度 (m/s)。"""
        if t <= car_T:
            return car_acc * t
        return SS_V_MAX

    # 遅い/早い判定 (加速時間が長い=遅い)
    slow_T = max(T_a, T_b)
    fast_T = min(T_a, T_b)

    # Phase時間の定義 (仕様「3-2」「3-3」準拠)
    phase2_dur = 3.0   # Phase 3-2: 遅い車と同じ速度で3秒間

    phase2_frames = int(phase2_dur * SS_FPS)   # 48 frames

    # Phase 3-4: 110mの道の中央(X=0)へ移動、Yはゴールライン(-110m)まで
    final_cam_x = 0.0     # X=0 = 道の中央
    final_cam_y = -110.0  # Y=-110m (道の終点側)
    final_cam_z = 2.0

    # カメラ位置追跡用変数 (Phase 3-1終了時の値からスタート)
    cam_x_prev = cam_x_p1   # X: -5m
    cam_y_prev = cam_y_p1   # Y: Y初期位置 -5m

    # Phase 2終了時のカメラY位置と車の平均Y位置を事前計算（Phase 3への補間に使用）
    phase2_end_cam_y = cam_y_prev
    for _pre_i in range(phase2_frames):
        t_s_pre = _pre_i / SS_FPS
        s = _car_speed(slow_T, SS_V_MAX / slow_T, t_s_pre)
        phase2_end_cam_y -= s / SS_FPS
    
    # Phase 2終了時の車の平均Y位置（回転補間の起点として固定値を使用）
    ca_y_end = sa[1] - ss_distance(phase2_dur, aa)
    cb_y_end = sb[1] - ss_distance(phase2_dur, ba)
    phase2_end_avg_car_y = (ca_y_end + cb_y_end) / 2.0

    # Phase 2開始時のtarget（Frame71終了時の向きと一致させる）
    phase2_start_target = Vector(((sa[0]+sb[0])/2.0, avg_y_init, 1.5))

    for i in range(nframes):
        fr = SS_LAUNCH_FRAME + i
        t_s_i = i / SS_FPS  # 走行開始からの経過時間[s]

        ca_y = sa[1] - ss_distance(t_s_i, aa)
        cb_y = sb[1] - ss_distance(t_s_i, ba)
        avg_car_y = (ca_y + cb_y) / 2.0

        if i < phase2_frames:
            # ── 【3-2】遅いほうの車と同じ速度でY軸を移動 (2秒間) ──
            cam_speed = _car_speed(slow_T, SS_V_MAX / slow_T, t_s_i)
            dt = 1.0 / SS_FPS
            cam_y_prev -= cam_speed * dt
            
            # Phase 2開始時はFrame71終了時の向きと一致させる（スムーズ遷移）
            target_car = Vector((0.0, avg_car_y - 3.0, 1.5))
            blend_frames = 12  # 約0.5秒 (12フレーム) で完全に車の前方を見るように遷移
            blend = min(i / max(blend_frames - 1, 1), 1.0)
            target_pt = phase2_start_target * (1.0 - blend) + target_car * blend

        else:
            # ── 【3-3】110mの道の中央まで移動してSTART側を向いて固定 ──
            i_in_phase3 = i - phase2_frames
            phase3_transition = int(4.0 * SS_FPS)  # 遷移期間: 4秒 (96フレーム)
            
            if i_in_phase3 < phase3_transition:
                # 遷移中: スムーズにX=0, Y=-110mへ移動 + 向きもSTART側へスムーズ回転
                phase3_denom = max(phase3_transition - 1, 1)
                progress = i_in_phase3 / phase3_denom
                
                # スムーズな補間 (ease-in-out cosine)
                smooth = 0.5 - 0.5 * math.cos(math.pi * progress)
                
                cam_x_prev = cam_x_p1 * (1.0 - smooth)   # -5 → 0
                cam_y_prev = phase2_end_cam_y * (1.0 - smooth) + final_cam_y * smooth
                
                # カメラの向きもスムーズにSTART側へ回転
                target_car = Vector((0.0, phase2_end_avg_car_y - 3.0, 1.5))  # Phase 3-2終了時の向きを固定値で維持
                target_start = Vector((0.0, 10.0, 1.5))   # START側(Y正方向)
                target_pt = target_car * (1.0 - smooth) + target_start * smooth
            else:
                # 遷移完了後: 完全に固定
                cam_x_prev = final_cam_x   # X=0
                cam_y_prev = final_cam_y   # Y=-110m
                target_pt = Vector((0.0, 10.0, 1.5))   # START側(Y+)を向く

        camera.location = Vector((cam_x_prev, cam_y_prev, final_cam_z))

        dir_to_target_pt = (target_pt - camera.location).normalized()
        rot_q_cam = dir_to_target_pt.to_track_quat('-Z', 'Y')
        camera.rotation_euler = rot_q_cam.to_euler()
        camera.keyframe_insert("location", frame=fr)
        camera.keyframe_insert("rotation_euler", frame=fr)

    # 演出オブジェクト(GOALのみ - その他はframe=0直後に作成済み)
    _ss_create_goal_text(rear_offset_y, gz_a)

    # ハンドラは frame_change_post に変更（depsgraph評価完了後に実行）
    existing = [h for h in bpy.app.handlers.frame_change_post if getattr(h, '__name__', '') == '_ss_frame_update']
    if not existing:
        bpy.app.handlers.frame_change_post.append(_ss_frame_update)
        print("  [ハンドラ] _ss_frame_update を登録しました (frame_change_post)")

    scene.frame_start = 0
    scene.frame_end = anim_end
    print(f"  scene.frame_range=[{scene.frame_start}, {scene.frame_end}]")
    scene.frame_set(0)
    bpy.context.view_layer.update()
    print("=== short-s アニメーション完了 ===")
    return {"car_a_loc": car_a.location, "car_b_loc": car_b.location}
