import math

SS_FPS = 24.0
SS_V_MAX = 100.0 / 3.6  # 27.78 m/s

def _get_accel_params(T):
    T = max(float(T), 0.5)
    a_prime = 200.0 / (T * T)
    v_at_T = a_prime * T
    if v_at_T <= SS_V_MAX:
        return T, a_prime, 100.0
    else:
        t1 = 2.0 * (T - 100.0 / SS_V_MAX)
        if t1 > 0:
            a_fallback = SS_V_MAX / t1
            dmax_fallback = 0.5 * a_fallback * t1 * t1
            return t1, a_fallback, dmax_fallback
        return T, SS_V_MAX / T, 0.5 * SS_V_MAX * T

def ss_distance(t, accel_s):
    if t <= 0.0:
        return 0.0
    t1, a, dmax = _get_accel_params(accel_s)
    if t <= t1:
        return 0.5 * a * t * t
    return dmax + SS_V_MAX * (t - t1)

def ss_arrival_time(start_y, accel_s):
    D = max(float(start_y) + 100.0, 1e-6)  # goalは-100mなので start_y - (-100) = start_y+100
    t1, a, dmax = _get_accel_params(accel_s)
    if D <= dmax:
        ta = math.sqrt((2.0 * D) / a)
    else:
        ta = t1 + (D - dmax) / SS_V_MAX
    return ta

# テストケース
print('=== 修正後の計算結果 ===')
cars = [
    ('アルファードHV', 8.8),
    ('ハイランダー(仮)', 6.7),
    ('トヨタ車(早い)', 5.5),
]

for name, T in cars:
    t1, a, dmax = _get_accel_params(T)
    v_at_T = a * T
    arrival_time = ss_arrival_time(0, T)
    print(f'{name}:')
    print(f'  設定加速時間T = {T}s')
    print(f'  t1(加速到達時間) = {t1:.2f}s')
    print(f'  計算加速度a = {a:.4f} m/s²')
    print(f'  v(T) = {v_at_T:.2f} m/s ({v_at_T*3.6:.1f} km/h)')
    print(f'  dmax(加速距離) = {dmax:.1f}m')
    print(f'  100m到着タイム = {arrival_time:.2f}s')
    
    # 到着時の速度と距離も確認
    dist_at_T = ss_distance(T, T)
    vel_at_T_arrival = ss_distance(T + 0.01, T) - ss_distance(T, T) / 0.01 if t1 > T else a * T
    print(f'  [検証] d(T)={dist_at_T:.2f}m (T秒での距離)')
    print()

print('=== carA start_y=0.15 (rear_offset_yあり) ===')
for name, T in cars:
    arr_time = ss_arrival_time(0.15, T)
    dist_100p15 = ss_distance(arr_time, T)
    print(f'{name}: 到着タイム={arr_time:.2f}s, 距離={dist_100p15:.2f}m')
