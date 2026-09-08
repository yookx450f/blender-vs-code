"""Check blender output log for variation messages"""
import re

try:
    with open('blender_output.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print("=== First 50 lines ===")
    for line in lines[:50]:
        print(line, end='')
    
    print("\n=== Matching variation-related lines ===")
    patterns = ['バリエ', 'DEBUG', 'STRATEGY', 'grid_color', 'clay_color', '✅', '❌']
    matched = [l for l in lines if any(p in l for p in patterns)]
    
    if matched:
        for line in matched:
            print(line, end='')
    else:
        print("No matching lines found!")
        print(f"Total lines: {len(lines)}")
except Exception as e:
    print(f"Error: {e}")
