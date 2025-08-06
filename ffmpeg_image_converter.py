#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高级图像格式转换工具
支持将JPEG、PNG、BMP、BIN等格式转换为指定格式的BIN文件
支持RGB、YUV等输出格式，支持任意尺寸的resize操作
支持批量处理和进度显示
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
import re
from typing import Tuple, Optional, List
import time

class ImageConverter:
    def __init__(self):
        self.supported_input_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.bin', '.tiff', '.tif']
        # 支持的输出格式：图像格式和原始数据格式
        self.supported_output_formats = {
            # 图像格式
            'png': 'png',
            'jpg': 'mjpeg',
            'jpeg': 'mjpeg', 
            'bmp': 'bmp',
            # 原始数据格式
            'rgb': 'rgb24',
            'yuv420': 'yuv420p', 
            'yuv422': 'yuv422p',
            'yuv444': 'yuv444p',
            'gray': 'gray',
            'bgr': 'bgr24',
            'rgba': 'rgba',
            'bgra': 'bgra'
        }
        
        # 图像格式的扩展名映射
        self.format_extensions = {
            'png': '.png',
            'jpg': '.jpg',
            'jpeg': '.jpg',
            'bmp': '.bmp',
            'rgb': '.bin',
            'yuv420': '.bin',
            'yuv422': '.bin',
            'yuv444': '.bin',
            'gray': '.bin',
            'bgr': '.bin',
            'rgba': '.bin',
            'bgra': '.bin'
        }
        
    def check_ffmpeg(self) -> bool:
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def get_image_info(self, input_file: str) -> Tuple[int, int, str]:
        """获取图像信息（宽度、高度、格式等）"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_streams', '-select_streams', 'v:0', input_file
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # 解析JSON输出
            data = json.loads(result.stdout)
            if 'streams' not in data or not data['streams']:
                raise ValueError("未找到视频流信息")
            
            stream = data['streams'][0]
            width = int(stream.get('width', 0))
            height = int(stream.get('height', 0))
            pix_fmt = stream.get('pix_fmt', 'unknown')
            
            if width == 0 or height == 0:
                raise ValueError("无法获取有效的图像尺寸")
                
            return width, height, pix_fmt
                
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError(f"无法获取图像信息: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"无法解析图像信息JSON: {e}")
    
    def calculate_file_size(self, width: int, height: int, format_name: str) -> Optional[int]:
        """计算输出文件大小（仅对原始数据格式有效）"""
        # 图像格式无法准确计算大小，返回None
        if format_name in ['png', 'jpg', 'jpeg', 'bmp']:
            return None
            
        format_sizes = {
            'rgb': 3,      # RGB24: 3 bytes per pixel
            'bgr': 3,      # BGR24: 3 bytes per pixel
            'rgba': 4,     # RGBA: 4 bytes per pixel
            'bgra': 4,     # BGRA: 4 bytes per pixel
            'yuv420': 1.5, # YUV420: 1.5 bytes per pixel
            'yuv422': 2,   # YUV422: 2 bytes per pixel
            'yuv444': 3,   # YUV444: 3 bytes per pixel
            'gray': 1      # Grayscale: 1 byte per pixel
        }
        
        bytes_per_pixel = format_sizes.get(format_name, 3)
        return int(width * height * bytes_per_pixel)
    
    def convert_image(self, input_file: str, output_format: str, 
                     output_width: Optional[int] = None, 
                     output_height: Optional[int] = None,
                     quality: int = 95) -> str:
        """转换图像格式"""
        if not self.check_ffmpeg():
            raise RuntimeError("FFmpeg未安装或不在PATH中")
        
        if output_format not in self.supported_output_formats:
            raise ValueError(f"不支持的输出格式: {output_format}")
        
        # 获取输入图像信息
        input_width, input_height, input_pix_fmt = self.get_image_info(input_file)
        
        # 确定输出尺寸
        if output_width is None:
            output_width = input_width
        if output_height is None:
            output_height = input_height
        
        # 构建输出文件名
        ext = self.format_extensions.get(output_format, '.bin')
        output_filename = f"{output_width}x{output_height}_{output_format}{ext}"
        
        # 构建FFmpeg命令
        cmd = ['ffmpeg', '-i', input_file, '-y']  # -y表示覆盖输出文件
        
        # 添加resize参数（如果需要）
        if output_width != input_width or output_height != input_height:
            cmd.extend(['-vf', f'scale={output_width}:{output_height}:flags=lanczos'])
        
        # 根据输出格式添加相应的参数
        if output_format in ['png', 'jpg', 'jpeg', 'bmp']:
            # 图像格式
            if output_format in ['jpg', 'jpeg']:
                cmd.extend(['-q:v', str(quality)])  # JPEG质量参数
            elif output_format == 'png':
                cmd.extend(['-compression_level', '6'])  # PNG压缩级别
        else:
            # 原始数据格式
            pix_fmt = self.supported_output_formats[output_format]
            cmd.extend(['-pix_fmt', pix_fmt])
            cmd.extend(['-f', 'rawvideo'])
        
        # 添加输出文件
        cmd.append(output_filename)
        
        print(f"转换信息:")
        print(f"  输入文件: {input_file} ({input_width}x{input_height})")
        print(f"  输出文件: {output_filename} ({output_width}x{output_height})")
        print(f"  输出格式: {output_format}")
        if output_format not in ['png', 'jpg', 'jpeg', 'bmp']:
            pix_fmt = self.supported_output_formats[output_format]
            print(f"  像素格式: {pix_fmt}")
            expected_size = self.calculate_file_size(output_width, output_height, output_format)
            if expected_size:
                print(f"  预计大小: {expected_size:,} bytes")
        print(f"  执行命令: {' '.join(cmd)}")
        
        # 执行转换
        start_time = time.time()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            end_time = time.time()
            
            # 验证输出文件
            if os.path.exists(output_filename):
                actual_size = os.path.getsize(output_filename)
                print(f"转换成功: {output_filename}")
                print(f"  实际大小: {actual_size:,} bytes")
                print(f"  转换时间: {end_time - start_time:.2f} 秒")
                
                # 对于原始数据格式，检查文件大小
                if output_format not in ['png', 'jpg', 'jpeg', 'bmp']:
                    expected_size = self.calculate_file_size(output_width, output_height, output_format)
                    if expected_size is not None and actual_size != expected_size:
                        print(f"  警告: 文件大小不匹配 (期望: {expected_size}, 实际: {actual_size})")
                
                return output_filename
            else:
                raise RuntimeError("输出文件未生成")
                
        except subprocess.CalledProcessError as e:
            print(f"转换失败: {e}")
            print(f"错误输出: {e.stderr}")
            raise
    
    def convert_bin_to_bin(self, input_file: str, input_format: str, 
                          input_width: int, input_height: int,
                          output_format: str, output_width: int, output_height: int) -> str:
        """将BIN文件转换为指定格式的文件（支持图像格式和原始数据格式）"""
        temp_image = f"temp_image_{int(time.time())}.png"
        
        try:
            # 将输入BIN文件转换为临时图像文件
            input_pix_fmt = self.supported_output_formats.get(input_format, 'rgb24')
            cmd1 = [
                'ffmpeg', '-f', 'rawvideo', '-pix_fmt', input_pix_fmt,
                '-s', f'{input_width}x{input_height}', '-i', input_file,
                '-y', temp_image
            ]
            print(f"步骤1: 将BIN转换为临时图像")
            subprocess.run(cmd1, capture_output=True, check=True)
            
            # 转换为目标格式
            print(f"步骤2: 转换为目标格式")
            return self.convert_image(temp_image, output_format, output_width, output_height)
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_image):
                os.remove(temp_image)
                print(f"清理临时文件: {temp_image}")
    
    def batch_convert(self, input_files: List[str], output_format: str,
                     output_width: Optional[int] = None, 
                     output_height: Optional[int] = None) -> List[str]:
        """批量转换文件"""
        results = []
        total_files = len(input_files)
        
        print(f"开始批量转换 {total_files} 个文件...")
        
        for i, input_file in enumerate(input_files, 1):
            try:
                print(f"\n[{i}/{total_files}] 处理文件: {input_file}")
                output_file = self.convert_image(input_file, output_format, output_width, output_height)
                results.append(output_file)
            except Exception as e:
                print(f"  错误: {e}")
                continue
        
        print(f"\n批量转换完成: {len(results)}/{total_files} 个文件成功转换")
        return results

def main():
    parser = argparse.ArgumentParser(description='高级图像格式转换工具')
    parser.add_argument('input_file', default="./input1.png", help='输入图像文件路径')
    parser.add_argument('output_format', 
                       choices=['png', 'jpg', 'jpeg', 'bmp', 'rgb', 'yuv420', 'yuv422', 'yuv444', 'gray', 'bgr', 'rgba', 'bgra'],
                       default='rgb', help='输出格式')
    parser.add_argument('-w', '--width', default=500, type=int, help='输出图像宽度')
    parser.add_argument('-H', '--height', default=500, type=int, help='输出图像高度')
    parser.add_argument('--input-format', choices=['rgb', 'yuv420', 'yuv422', 'yuv444', 'gray', 'bgr', 'rgba', 'bgra'],
                       default='rgb', help='输入BIN文件的格式（仅用于BIN文件）')
    parser.add_argument('--input-width', default=217, type=int, help='输入BIN文件的宽度（仅用于BIN文件）')
    parser.add_argument('--input-height', default=233, type=int, help='输入BIN文件的高度（仅用于BIN文件）')
    parser.add_argument('--batch', default=False, action='store_true', help='批量处理模式（输入文件为目录）')
    parser.add_argument('--recursive', default=False, action='store_true', help='递归处理子目录（批量模式）')
    
    args = parser.parse_args()
    
    converter = ImageConverter()
    
    # 检查FFmpeg
    if not converter.check_ffmpeg():
        print("错误: FFmpeg未安装或不在PATH中")
        print("请安装FFmpeg: https://ffmpeg.org/download.html")
        sys.exit(1)
    
    try:
        if args.batch:
            # 批量处理模式
            input_path = Path(args.input_file)
            if not input_path.exists():
                print(f"错误: 输入路径不存在: {args.input_file}")
                sys.exit(1)
            
            if input_path.is_file():
                # 单个文件
                input_files = [str(input_path)]
            else:
                # 目录
                pattern = "**/*" if args.recursive else "*"
                input_files = []
                for ext in converter.supported_input_formats:
                    input_files.extend(input_path.glob(pattern + ext))
                    input_files.extend(input_path.glob(pattern + ext.upper()))
                
                input_files = [str(f) for f in input_files if f.is_file()]
            
            if not input_files:
                print("错误: 未找到支持的图像文件")
                sys.exit(1)
            
            print(f"找到 {len(input_files)} 个文件")
            results = converter.batch_convert(input_files, args.output_format, args.width, args.height)
            
        else:
            # 单个文件处理
            if not os.path.exists(args.input_file):
                print(f"错误: 输入文件不存在: {args.input_file}")
                sys.exit(1)
            
            input_ext = Path(args.input_file).suffix.lower()
            
            if input_ext == '.bin':
                # 处理BIN文件
                if args.input_width is None or args.input_height is None:
                    print("错误: 对于BIN文件，必须指定输入宽度和高度")
                    sys.exit(1)
                
                if args.width is None or args.height is None:
                    print("错误: 对于BIN文件，必须指定输出宽度和高度")
                    sys.exit(1)
                
                output_file = converter.convert_bin_to_bin(
                    args.input_file, args.input_format,
                    args.input_width, args.input_height,
                    args.output_format, args.width, args.height
                )
            else:
                # 处理其他图像格式
                output_file = converter.convert_image(
                    args.input_file, args.output_format,
                    args.width, args.height
                )
            
            print(f"转换完成: {output_file}")
        
    except Exception as e:
        print(f"转换失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 