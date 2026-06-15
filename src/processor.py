"""
处理模块 - 负责调用generate.py进行文件转换
"""
import os
import sys
import subprocess
import traceback
from typing import Dict, Tuple, Optional


class FileProcessor:
    """文件处理器"""
    
    @staticmethod
    def process_file(params: Dict) -> Tuple[bool, str]:
        """
        处理文件转换
        
        参数:
            params: 包含以下键的字典
                - input_file: 输入文件路径
                - output_format: 输出格式 (rgb888, yuv420, yonly)
                - width: 输出宽度
                - height: 输出高度
                - output_dir: 输出目录
                - output_filename: 输出文件名(可选)
        
        返回:
            (success, message): 成功标志和消息
        """
        try:
            # 验证参数
            required_keys = ['input_file', 'output_format', 'width', 'height', 'output_dir']
            for key in required_keys:
                if key not in params:
                    return False, f"缺少必要参数: {key}"
            
            # 验证输入文件存在
            if not os.path.exists(params['input_file']):
                return False, f"输入文件不存在: {params['input_file']}"
            
            # 验证输出目录，如果不存在则创建
            if not os.path.exists(params['output_dir']):
                os.makedirs(params['output_dir'], exist_ok=True)
            
            # 调用generate.py的处理函数
            return FileProcessor._call_generate(params)
            
        except Exception as e:
            error_msg = f"处理过程中发生错误: {str(e)}\n\n详细错误:\n{traceback.format_exc()}"
            return False, error_msg
    
    @staticmethod
    def _call_generate(params: Dict) -> Tuple[bool, str]:
        """调用generate.py的处理函数"""
        try:
            # 兼容两种运行方式：
            # 1) 作为 src 包运行（打包/从 run.py 启动）
            # 2) 直接在 src 目录下脚本方式运行
            try:
                from .generator import process_image
            except ImportError:
                from generator import process_image
            
            # 调用处理函数
            result = process_image(
                input_path=params['input_file'],
                output_format=params['output_format'],
                width=params['width'],
                height=params['height'],
                output_dir=params['output_dir'],
                output_filename=params.get('output_filename'),
                packed_alpha_8=params.get('packed_alpha_8'),
            )
            
            if result.get('success', False):
                output_path = result.get('output_path', '')
                message = f"转换成功！\n输出文件: {os.path.basename(output_path)}"
                if output_path and os.path.exists(output_path):
                    message += f"\n文件大小: {os.path.getsize(output_path) / 1024:.2f} KB"
                return True, message
            else:
                return False, result.get('error', '转换失败')
                
        except ImportError as e:
            return False, f"无法加载转换模块: {e}"
        except Exception as e:
            return False, f"调用处理函数失败: {str(e)}"
    
    @staticmethod
    def _simulate_processing(params: Dict) -> Tuple[bool, str]:
        """模拟处理过程（用于测试）"""
        import time
        import random
        
        # 模拟处理时间
        time.sleep(2)
        
        # 生成输出文件名
        input_name = os.path.splitext(os.path.basename(params['input_file']))[0]
        
        # 根据格式确定扩展名
        format_ext = {
            'rgb888': '.rgb',
            'yuv420': '.yuv',
            'yonly': '.y'
        }
        ext = "." + params['output_format']
        
        # 生成输出路径
        output_filename = f"{input_name}_{params['width']}x{params['height']}{ext}"
        output_path = os.path.join(params['output_dir'], output_filename)
        
        # 模拟创建文件
        with open(output_path, 'wb') as f:
            # 写入一些模拟数据
            f.write(b"Simulated binary data for testing\n")
            f.write(f"Format: {params['output_format']}\n".encode())
            f.write(f"Resolution: {params['width']}x{params['height']}\n".encode())
            f.write(f"Original: {params['input_file']}\n".encode())
        
        # 模拟随机成功/失败
        if random.random() > 0.1:  # 90%成功率
            file_size = os.path.getsize(output_path)
            return True, f"模拟转换成功！\n输出文件: {output_filename}\n文件大小: {file_size} bytes"
        else:
            # 模拟失败
            if os.path.exists(output_path):
                os.remove(output_path)
            return False, "模拟转换失败：处理过程中出现错误"
    
    @staticmethod
    def validate_input_file(file_path: str) -> Tuple[bool, str]:
        """验证输入文件"""
        if not file_path:
            return False, "文件路径为空"
        
        if not os.path.exists(file_path):
            return False, f"文件不存在: {file_path}"
        
        # 检查文件扩展名（与界面提示保持一致）
        supported_extensions = ['.jpg', '.jpeg', '.bmp', '.png', '.webp']
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext not in supported_extensions:
            return False, f"不支持的文件格式: {file_ext}\n支持的格式: {', '.join(supported_extensions)}"
        
        return True, "文件验证通过"
    
    @staticmethod
    def generate_output_filename(params: Dict) -> str:
        """生成输出文件名"""
        input_name = os.path.splitext(os.path.basename(params['input_file']))[0]
        
        # 根据格式确定扩展名
        ext = "." + params['output_format']
        
        return f"{input_name}_{params['width']}x{params['height']}{ext}"


# 工具函数
def parse_resolution(resolution_str: str) -> Tuple[int, int, str]:
    """
    解析分辨率字符串
    
    返回:
        (width, height, error_message)
    """
    if not resolution_str:
        return 0, 0, "分辨率不能为空"
    
    # 兼容 1920X1080 / 1920 x 1080 / 1920×1080 等常见写法
    normalized = resolution_str.strip().lower().replace("×", "x")
    parts = [part.strip() for part in normalized.split('x')]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return 0, 0, f"分辨率格式不正确: {resolution_str}\n请使用 '宽度x高度' 格式，如 1920x1080"
    
    try:
        width = int(parts[0])
        height = int(parts[1])
        
        if width <= 0 or height <= 0:
            return 0, 0, f"分辨率必须为正数: {width}x{height}"
        
        return width, height, ""
        
    except ValueError:
        return 0, 0, f"分辨率包含非数字字符: {resolution_str}"