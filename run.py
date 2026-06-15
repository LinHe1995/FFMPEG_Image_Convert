#!/usr/bin/env python3
"""应用程序启动脚本"""
import sys
import os
import traceback
import ctypes

# 确保可以导入src模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from src.main import main
    main()
except Exception as e:
    error_text = f"启动失败: {e}\n\n{traceback.format_exc()}"
    try:
        ctypes.windll.user32.MessageBoxW(0, error_text, "img_gen_pyqt 启动失败", 0x10)
    except Exception:
        # 无法弹窗时回退到标准错误输出
        print(error_text, file=sys.stderr)
    raise