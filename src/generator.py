"""
generate.py - 实际的文件转换处理函数
"""
import os
from typing import Dict, Optional, Tuple

import numpy as np
from PIL import Image


SUPPORTED_FORMATS = {
    "yuv420p",
    "yuv422p",
    "yuv444p",
    "nv12",
    "nv21",
    "nv16",
    "nv61",
    "yuv422yvyu",
    "yuv422yuyv",
    "yuv422vyuy",
    "yuv422uyvy",
    "rgbpack",
    "rgbplanar",
    "argb4444",
    "argb1555",
    "yonly",
}

REQUIRE_EVEN_WH = {
    "yuv420p",
    "yuv422p",
    "nv12",
    "nv21",
    "nv16",
    "nv61",
    "yuv422yvyu",
    "yuv422yuyv",
    "yuv422vyuy",
    "yuv422uyvy",
}


def _load_rgb_image(input_path: str, width: int, height: int) -> np.ndarray:
    """读取输入图像并转换为目标分辨率 RGB888 数组。"""
    with Image.open(input_path) as img:
        rgb_img = img.convert("RGB").resize((width, height), Image.Resampling.BILINEAR)
        return np.array(rgb_img, dtype=np.uint8)


def _rgb_to_yuv_bt601_full_range(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """RGB 转 YUV444（BT.601 full range）。"""
    rgbf = rgb.astype(np.float32)
    r = rgbf[:, :, 0]
    g = rgbf[:, :, 1]
    b = rgbf[:, :, 2]

    y = 0.299 * r + 0.587 * g + 0.114 * b
    u = -0.168736 * r - 0.331264 * g + 0.5 * b + 128.0
    v = 0.5 * r - 0.418688 * g - 0.081312 * b + 128.0

    y = np.clip(np.round(y), 0, 255).astype(np.uint8)
    u = np.clip(np.round(u), 0, 255).astype(np.uint8)
    v = np.clip(np.round(v), 0, 255).astype(np.uint8)
    return y, u, v


def _downsample_420_avg(u: np.ndarray, v: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """YUV444 的 U/V 2x2 块平均下采样为 YUV420。"""
    h, w = u.shape
    u00 = u[0:h:2, 0:w:2].astype(np.float32)
    u01 = u[0:h:2, 1:w:2].astype(np.float32)
    u10 = u[1:h:2, 0:w:2].astype(np.float32)
    u11 = u[1:h:2, 1:w:2].astype(np.float32)

    v00 = v[0:h:2, 0:w:2].astype(np.float32)
    v01 = v[0:h:2, 1:w:2].astype(np.float32)
    v10 = v[1:h:2, 0:w:2].astype(np.float32)
    v11 = v[1:h:2, 1:w:2].astype(np.float32)

    u420 = np.clip(np.round((u00 + u01 + u10 + u11) / 4.0), 0, 255).astype(np.uint8)
    v420 = np.clip(np.round((v00 + v01 + v10 + v11) / 4.0), 0, 255).astype(np.uint8)
    return u420, v420


def _upsample_420_to_422_vertical(u420: np.ndarray, v420: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """将 U/V 从 (H/2, W/2) 上采样为 (H, W/2)，仅垂直方向放大。"""
    h2, w2 = u420.shape
    h = h2 * 2

    u420f = u420.astype(np.float32)
    v420f = v420.astype(np.float32)
    u_out = np.empty((h, w2), dtype=np.float32)
    v_out = np.empty((h, w2), dtype=np.float32)

    for r in range(h):
        src_pos = r / 2.0
        r0 = int(np.floor(src_pos))
        r1 = min(r0 + 1, h2 - 1)
        alpha = src_pos - r0
        u_out[r, :] = (1 - alpha) * u420f[r0, :] + alpha * u420f[r1, :]
        v_out[r, :] = (1 - alpha) * v420f[r0, :] + alpha * v420f[r1, :]

    u_out = np.clip(u_out + 0.5, 0, 255).astype(np.uint8)
    v_out = np.clip(v_out + 0.5, 0, 255).astype(np.uint8)
    return u_out, v_out


def _pack_yuyv(y: np.ndarray, u422: np.ndarray, v422: np.ndarray) -> np.ndarray:
    out = np.empty((y.shape[0], y.shape[1] * 2), dtype=np.uint8)
    out[:, 0::4] = y[:, 0::2]
    out[:, 1::4] = u422
    out[:, 2::4] = y[:, 1::2]
    out[:, 3::4] = v422
    return out


def _pack_yvyu(y: np.ndarray, u422: np.ndarray, v422: np.ndarray) -> np.ndarray:
    out = np.empty((y.shape[0], y.shape[1] * 2), dtype=np.uint8)
    out[:, 0::4] = y[:, 0::2]
    out[:, 1::4] = v422
    out[:, 2::4] = y[:, 1::2]
    out[:, 3::4] = u422
    return out


def _pack_vyuy(y: np.ndarray, u422: np.ndarray, v422: np.ndarray) -> np.ndarray:
    out = np.empty((y.shape[0], y.shape[1] * 2), dtype=np.uint8)
    out[:, 0::4] = v422
    out[:, 1::4] = y[:, 0::2]
    out[:, 2::4] = u422
    out[:, 3::4] = y[:, 1::2]
    return out


def _pack_uyvy(y: np.ndarray, u422: np.ndarray, v422: np.ndarray) -> np.ndarray:
    out = np.empty((y.shape[0], y.shape[1] * 2), dtype=np.uint8)
    out[:, 0::4] = u422
    out[:, 1::4] = y[:, 0::2]
    out[:, 2::4] = v422
    out[:, 3::4] = y[:, 1::2]
    return out


def _interleave_uv(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """交错 U/V 到单平面（UVUV...）。"""
    uv = np.empty((u.shape[0], u.shape[1] * 2), dtype=np.uint8)
    uv[:, 0::2] = u
    uv[:, 1::2] = v
    return uv


def _interleave_vu(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """交错 V/U 到单平面（VUVU...）。"""
    vu = np.empty((u.shape[0], u.shape[1] * 2), dtype=np.uint8)
    vu[:, 0::2] = v
    vu[:, 1::2] = u
    return vu


def _to_nibble_4444(channel: np.ndarray) -> np.ndarray:
    """8 位通道量化为 4 位（0~15）。"""
    return np.clip(np.round(channel.astype(np.float32) / 255.0 * 15.0), 0, 15).astype(np.uint16)


def _to_bits_555(channel: np.ndarray) -> np.ndarray:
    """8 位通道量化为 5 位（0~31）。"""
    return np.clip(np.round(channel.astype(np.float32) / 255.0 * 31.0), 0, 31).astype(np.uint16)


def _pack_argb4444(rgb: np.ndarray, alpha_8: int = 255) -> np.ndarray:
    """ARGB4444：每像素 uint16，布局 A4 R4 G4 B4（高到低 nibble）。alpha_8：0–255。"""
    r = _to_nibble_4444(rgb[:, :, 0])
    g = _to_nibble_4444(rgb[:, :, 1])
    b = _to_nibble_4444(rgb[:, :, 2])
    a8 = int(np.clip(alpha_8, 0, 255))
    a4 = int(np.clip(np.round(a8 / 255.0 * 15.0), 0, 15))
    a = np.full(rgb.shape[:2], a4, dtype=np.uint16)
    return (a << 12) | (r << 8) | (g << 4) | b


def _pack_argb1555(rgb: np.ndarray, alpha_8: int = 255) -> np.ndarray:
    """ARGB1555：每像素 uint16，布局 A1 R5 G5 B5（A 在 bit15）。alpha_8≥128 为不透明。"""
    a8 = int(np.clip(alpha_8, 0, 255))
    a_bit = 1 if a8 >= 128 else 0
    a1 = np.full(rgb.shape[:2], a_bit, dtype=np.uint16)
    r5 = _to_bits_555(rgb[:, :, 0])
    g5 = _to_bits_555(rgb[:, :, 1])
    b5 = _to_bits_555(rgb[:, :, 2])
    return (a1 << 15) | (r5 << 10) | (g5 << 5) | b5


def _write_output(
    output_path: str,
    output_format: str,
    rgb: np.ndarray,
    y: np.ndarray,
    u420: np.ndarray,
    v420: np.ndarray,
    packed_alpha_8: int = 255,
) -> None:
    with open(output_path, "wb") as f:
        if output_format == "rgbpack":
            f.write(rgb.tobytes())
            return

        if output_format == "rgbplanar":
            f.write(rgb[:, :, 0].tobytes())
            f.write(rgb[:, :, 1].tobytes())
            f.write(rgb[:, :, 2].tobytes())
            return

        if output_format == "argb4444":
            packed = _pack_argb4444(rgb, packed_alpha_8).astype("<u2")
            f.write(packed.tobytes())
            return

        if output_format == "argb1555":
            packed = _pack_argb1555(rgb, packed_alpha_8).astype("<u2")
            f.write(packed.tobytes())
            return

        if output_format == "yonly":
            f.write(y.tobytes())
            return

        if output_format == "yuv420p":
            f.write(y.tobytes())
            f.write(u420.tobytes())
            f.write(v420.tobytes())
            return

        if output_format == "nv12":
            f.write(y.tobytes())
            f.write(_interleave_uv(u420, v420).tobytes())
            return

        if output_format == "nv21":
            f.write(y.tobytes())
            f.write(_interleave_vu(u420, v420).tobytes())
            return

        if output_format == "yuv444p":
            u444 = np.repeat(np.repeat(u420, 2, axis=0), 2, axis=1)
            v444 = np.repeat(np.repeat(v420, 2, axis=0), 2, axis=1)
            f.write(y.tobytes())
            f.write(u444.tobytes())
            f.write(v444.tobytes())
            return

        u422, v422 = _upsample_420_to_422_vertical(u420, v420)

        if output_format == "yuv422p":
            f.write(y.tobytes())
            f.write(u422.tobytes())
            f.write(v422.tobytes())
            return

        if output_format == "nv16":
            f.write(y.tobytes())
            f.write(_interleave_uv(u422, v422).tobytes())
            return

        if output_format == "nv61":
            f.write(y.tobytes())
            f.write(_interleave_vu(u422, v422).tobytes())
            return

        if output_format == "yuv422yuyv":
            f.write(_pack_yuyv(y, u422, v422).tobytes())
            return

        if output_format == "yuv422yvyu":
            f.write(_pack_yvyu(y, u422, v422).tobytes())
            return

        if output_format == "yuv422vyuy":
            f.write(_pack_vyuy(y, u422, v422).tobytes())
            return

        if output_format == "yuv422uyvy":
            f.write(_pack_uyvy(y, u422, v422).tobytes())
            return

        raise ValueError(f"暂不支持的输出格式: {output_format}")


def process_image(
    input_path: str,
    output_format: str,
    width: int,
    height: int,
    output_dir: str,
    output_filename: Optional[str] = None,
    packed_alpha_8: Optional[int] = None,
) -> Dict:
    """
    处理图像转换的主函数。
    """
    import time

    start_time = time.time()
    output_format = output_format.lower()

    try:
        if not os.path.exists(input_path):
            return {"success": False, "error": f"输入文件不存在: {input_path}"}

        if output_format not in SUPPORTED_FORMATS:
            return {
                "success": False,
                "error": f"不支持的输出格式: {output_format}\n支持格式: {', '.join(sorted(SUPPORTED_FORMATS))}",
            }

        if output_format in REQUIRE_EVEN_WH and (width % 2 != 0 or height % 2 != 0):
            return {
                "success": False,
                "error": f"{output_format} 需要偶数宽高，当前为 {width}x{height}",
            }

        os.makedirs(output_dir, exist_ok=True)

        if not output_filename:
            input_name = os.path.splitext(os.path.basename(input_path))[0]
            output_filename = f"{input_name}_{width}x{height}.{output_format}"
        output_path = os.path.join(output_dir, output_filename)

        if packed_alpha_8 is None:
            alpha8 = 255
        else:
            try:
                alpha8 = int(packed_alpha_8)
            except (TypeError, ValueError):
                return {"success": False, "error": f"Alpha 无效: {packed_alpha_8!r}，应为 0–255 的整数"}
            if alpha8 < 0 or alpha8 > 255:
                return {"success": False, "error": f"Alpha 超出范围: {alpha8}，应为 0–255"}

        rgb = _load_rgb_image(input_path, width, height)
        y, u, v = _rgb_to_yuv_bt601_full_range(rgb)

        if width % 2 == 0 and height % 2 == 0:
            u420, v420 = _downsample_420_avg(u, v)
        else:
            u420 = np.zeros((0, 0), dtype=np.uint8)
            v420 = np.zeros((0, 0), dtype=np.uint8)

        _write_output(output_path, output_format, rgb, y, u420, v420, alpha8)

        processing_time = time.time() - start_time
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return {
                "success": True,
                "output_path": output_path,
                "processing_time": processing_time,
                "message": f"转换完成，耗时 {processing_time:.2f} 秒",
            }
        return {"success": False, "error": "转换失败：输出文件创建失败"}

    except ImportError as e:
        return {
            "success": False,
            "error": f"缺少必要库: {e}\n请安装 Pillow 和 numpy。",
        }
    except Exception as e:
        import traceback

        return {
            "success": False,
            "error": f"处理过程中发生错误: {e}\n\n详细信息:\n{traceback.format_exc()}",
        }