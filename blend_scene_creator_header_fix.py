"""
Blenderスタンドアロンスクリプト - コマンドラインから直接実行可能

使い方:
    blender --background --python blend_scene_creator.py
    python run.py
"""

import bpy
import csv
import os
import math
import sys
import struct
import json
import time
import sqlite3
from mathutils import Vector, Matrix

# ★重要: BlenderのPythonパスにスクリプトディレクトリを追加
# これにより short2_apply_variations などのローカルモジュールをインポート可能にする
_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

# ============================================================
# グローバル変数（内部用 - 通常は変更不要）
# ============================================================
grounded_z_positions = {}  # 接地後のZ位置を保存する辞書
