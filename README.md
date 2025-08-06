# FFMPEG_Image_Convert
use ffmpeg convert image from/to different types
图像格式转换工具，支持将JPEG、PNG、BMP、BIN等格式转换为PNG、JPEG、BMP、BIN等多种输出格式。支持RGB、YUV等原始数据格式，支持任意尺寸的resize操作。

## 功能特性

- **多格式支持**: 支持JPEG、PNG、BMP、BIN、TIFF等输入格式
- **多种输出格式**: 支持PNG、JPEG、BMP等图像格式，以及RGB、YUV420、YUV422、YUV444、灰度等原始数据格式
- **尺寸调整**: 支持任意尺寸的resize操作，保持图像质量
- **批量处理**: 支持批量转换多个文件
- **智能命名**: 输出文件名自动包含尺寸和格式信息
- **详细日志**: 提供详细的转换信息和进度显示

## 系统要求

- Python 3.6+
- FFmpeg (需要安装并添加到PATH)

### 安装FFmpeg

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install ffmpeg
```

#### CentOS/RHEL
```bash
sudo yum install ffmpeg
# 或者使用EPEL仓库
sudo yum install epel-release
sudo yum install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

#### Windows
1. 下载FFmpeg: https://ffmpeg.org/download.html
2. 解压到某个目录
3. 将bin目录添加到系统PATH

## 安装和使用

### 1. 下载工具

```bash
# 下载高级版本（推荐）
wget https://example.com/image_converter_advanced.py

# 或直接复制代码到本地文件
```

### 2. 设置执行权限

```bash
chmod +x image_converter_advanced.py
```

### 3. 基本使用

#### 转换单个文件
```bash
# 基本用法（使用默认参数）
python3 image_converter_advanced.py

# 指定输入文件和输出格式
python3 image_converter_advanced.py input.jpg rgb

# 转换为图像格式
python3 image_converter_advanced.py input.png jpg -w 1920 -H 1080
python3 image_converter_advanced.py input.jpg png -w 800 -H 600
python3 image_converter_advanced.py input.png bmp -w 640 -H 480

# 指定尺寸
python3 image_converter_advanced.py input.jpg rgb -w 1920 -H 1080
```

#### 转换BIN文件
```bash
# 使用默认参数
python3 image_converter_advanced.py input.bin rgb

# 指定输入和输出参数
python3 image_converter_advanced.py input.bin rgb --input-width 640 --input-height 480 --input-format rgb -w 1920 -H 1080
```

#### 批量转换
```bash
# 批量转换目录中的所有图像文件
python3 image_converter_advanced.py /path/to/images/ rgb -w 1280 -H 720 --batch

# 递归处理子目录
python3 image_converter_advanced.py /path/to/images/ yuv420 -w 640 -H 480 --batch --recursive
```

## 命令行参数

### 命令行参数

| 参数 | 说明 | 示例 | 默认值 |
|------|------|------|--------|
| `input_file` | 输入文件路径 | `image.jpg` | `./1.png` |
| `output_format` | 输出格式 | `png`, `jpg`, `jpeg`, `bmp`, `rgb`, `yuv420`, `yuv422`, `yuv444`, `gray`, `bgr`, `rgba`, `bgra` | `rgb` |
| `-w, --width` | 输出宽度 | `-w 1920` | `500` |
| `-H, --height` | 输出高度 | `-H 1080` | `500` |
| `--input-format` | 输入BIN文件格式 | `--input-format rgb` | `rgb` |
| `--input-width` | 输入BIN文件宽度 | `--input-width 640` | `568` |
| `--input-height` | 输入BIN文件高度 | `--input-height 480` | `346` |
| `--batch` | 批量处理模式 | `--batch` | `False` |
| `--recursive` | 递归处理子目录 | `--recursive` | `False` |

## 支持的格式

### 输入格式
- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)
- BIN (.bin) - 原始图像数据

### 输出格式

| 格式 | 说明 | 文件扩展名 | 典型用途 |
|------|------|-----------|----------|
| `png` | PNG图像格式 | .png | 无损压缩图像 |
| `jpg`, `jpeg` | JPEG图像格式 | .jpg | 有损压缩图像 |
| `bmp` | BMP图像格式 | .bmp | Windows位图格式 |
| `rgb` | RGB24原始数据 | .bin | 通用图像处理 |
| `bgr` | BGR24原始数据 | .bin | OpenCV兼容 |
| `yuv420` | YUV420P原始数据 | .bin | 视频编码 |
| `yuv422` | YUV422P原始数据 | .bin | 高质量视频 |
| `yuv444` | YUV444P原始数据 | .bin | 无损视频 |
| `gray` | 灰度原始数据 | .bin | 单通道处理 |
| `rgba` | RGBA原始数据 | .bin | 带透明通道 |
| `bgra` | BGRA原始数据 | .bin | OpenCV带透明通道 |

## 使用示例

### 1. 基本图像转换

```bash
# 使用默认参数（输入文件：./1.png，输出：500x500_rgb.bin）
python3 image_converter_advanced.py

# 将JPEG转换为RGB格式，调整尺寸为1920x1080
python3 image_converter_advanced.py photo.jpg rgb -w 1920 -H 1080

# 将PNG转换为JPEG格式，调整尺寸为800x600
python3 image_converter_advanced.py image.png jpg -w 800 -H 600

# 将JPEG转换为PNG格式，保持原尺寸
python3 image_converter_advanced.py photo.jpg png

# 将PNG转换为BMP格式，调整尺寸为640x480
python3 image_converter_advanced.py image.png bmp -w 640 -H 480

# 输出: 1920x1080_rgb.bin, 800x600_jpg.jpg, 640x480_bmp.bmp
```

### 2. 格式转换

```bash
# 将PNG转换为YUV420格式（保持原尺寸）
python3 image_converter_advanced.py image.png yuv420

# 将BIN文件转换为PNG图像
python3 image_converter_advanced.py input.bin png --input-width 640 --input-height 480 --input-format rgb -w 1280 -H 720

# 输出: 原始尺寸的YUV420格式文件, 1280x720_png.png
```

### 3. BIN文件处理

```bash
# 使用默认参数转换BIN文件
python3 image_converter_advanced.py input.bin rgb

# 将RGB格式的BIN文件转换为YUV420，并调整尺寸
python3 image_converter_advanced.py input.bin yuv420 --input-width 640 --input-height 480 --input-format rgb -w 1280 -H 720

# 输出: 1280x720_yuv420.bin
```

### 4. 批量处理

```bash
# 批量转换目录中的所有图像文件
python3 image_converter_advanced.py /path/to/images/ rgb -w 640 -H 480 --batch

# 递归处理子目录
python3 image_converter_advanced.py /path/to/images/ yuv420 -w 640 -H 480 --batch --recursive
```

### 5. 灰度图像处理

```bash
# 转换为灰度格式
python3 image_converter_advanced.py color_image.jpg gray -w 800 -H 600
```

## 输出文件命名规则

输出文件按照以下格式命名：
```
{宽度}x{高度}_{格式}.{扩展名}
```

例如：
- `1920x1080_rgb.bin` - 1920x1080分辨率的RGB原始数据
- `800x600_jpg.jpg` - 800x600分辨率的JPEG图像
- `640x480_png.png` - 640x480分辨率的PNG图像
- `1280x720_bmp.bmp` - 1280x720分辨率的BMP图像
- `640x480_yuv420.bin` - 640x480分辨率的YUV420原始数据
- `1280x720_gray.bin` - 1280x720分辨率的灰度原始数据

## 文件大小计算

不同格式的输出文件大小计算公式：

### 原始数据格式（可准确计算）

| 格式 | 计算公式 | 示例 (1920x1080) |
|------|----------|------------------|
| RGB/BGR | width × height × 3 | 6,220,800 bytes |
| YUV420 | width × height × 1.5 | 3,110,400 bytes |
| YUV422 | width × height × 2 | 4,147,200 bytes |
| YUV444 | width × height × 3 | 6,220,800 bytes |
| 灰度 | width × height × 1 | 2,073,600 bytes |
| RGBA/BGRA | width × height × 4 | 8,294,400 bytes |

### 图像格式（无法准确计算）

PNG、JPEG、BMP等图像格式由于使用压缩算法，文件大小取决于图像内容和压缩设置，无法准确计算。工具会显示实际生成的文件大小。

## 错误处理

工具提供详细的错误信息和处理：

### 常见错误及解决方案

1. **FFmpeg未安装**
   ```
   错误: FFmpeg未安装或不在PATH中
   解决方案: 安装FFmpeg并确保在PATH中
   ```

2. **输入文件不存在**
   ```
   错误: 输入文件不存在: image.jpg
   解决方案: 检查文件路径是否正确
   ```

3. **不支持的格式**
   ```
   错误: 不支持的输出格式: unknown
   解决方案: 使用支持的格式名称
   ```

4. **BIN文件参数缺失**
   ```
   错误: 对于BIN文件，必须指定输入宽度和高度
   解决方案: 使用 -i 和 -I 参数指定输入尺寸
   ```

## 性能优化

### 批量处理优化
- 使用 `--batch` 模式进行批量处理
- 对于大量文件，建议使用递归模式 `--recursive`

### 内存使用
- 大图像处理时，工具会自动管理内存
- 临时文件会在处理完成后自动清理

### 转换质量
- 使用Lanczos算法进行高质量缩放
- 支持多种像素格式的精确转换

## 故障排除

### 1. 检查FFmpeg安装
```bash
ffmpeg -version
```

### 2. 检查Python版本
```bash
python3 --version
```

### 3. 检查文件权限
```bash
ls -la image_converter_advanced.py
chmod +x image_converter_advanced.py
```

### 4. 测试基本功能
```bash
# 创建测试图像
convert -size 100x100 xc:red test.jpg

# 测试转换
python3 image_converter_advanced.py test.jpg rgb -w 200 -H 200

# 使用默认参数测试
python3 image_converter_advanced.py
```

## 高级功能

### 1. 自定义输出目录
```bash
# 可以修改代码中的输出路径
output_filename = f"output/{width}x{height}_{format}.bin"
```

### 2. 质量参数调整
```bash
# 在代码中可以调整FFmpeg参数
cmd.extend(['-q:v', '1'])  # 高质量
```

### 3. 进度显示
高级版本提供详细的进度信息：
- 文件处理进度
- 转换时间统计
- 文件大小验证

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

## 贡献

欢迎提交Issue和Pull Request来改进这个工具。

## 更新日志

### v2.0.0 (高级版本)
- 添加批量处理功能
- 改进错误处理
- 添加进度显示和转换时间统计
- 支持更多输出格式（RGB、YUV420、YUV422、YUV444、灰度、BGR、RGBA、BGRA）
- 智能文件大小验证
- 支持递归目录处理
- 详细的转换信息显示
- 自动临时文件清理

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至: support@example.com

---

**注意**: 使用前请确保已正确安装FFmpeg，并确保有足够的磁盘空间存储输出文件。 
