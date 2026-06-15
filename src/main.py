import hashlib
import os
import re
import sys
import ctypes

import numpy as np
from PyQt5.QtCore import QEvent, QPoint, QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QFont, QIcon, QImage, QKeySequence, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QScrollArea,
    QShortcut,
    QSplitter,
    QSpinBox,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QAbstractItemView,
    QVBoxLayout,
    QWidget,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # 作为 src.main 被导入（如 PyInstaller）时优先相对导入
    from .processor import FileProcessor, parse_resolution
except ImportError:
    # 直接运行 src/main.py 时回退到绝对导入
    from processor import FileProcessor, parse_resolution

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_ICON_PATH = os.path.join(PROJECT_ROOT, "ui", "img_icon.png")
INFO_ICON_PATH = os.path.join(PROJECT_ROOT, "ui", "info_icon.png")
APP_TITLE = "图像显示与格式处理工具"
# 右侧图像区无内容时提示（启动、打开文件夹未选图、刷新后清空等需保持一致）
IMAGE_HINT_INITIAL = "请通过“文件 -> 打开文件/打开文件夹”选择图像，或通过拖拽选择图像"
ACTIVE_THEME = "dark"


def _path_for_status(path: str) -> str:
    """状态栏等展示用路径：统一为正斜杠，便于阅读与跨平台观感。"""
    if not path or path == "-":
        return path
    return path.replace("\\", "/")


def _file_md5_hex(path: str) -> str:
    """计算文件内容的 MD5（十六进制小写）。"""
    digest = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


SUPPORTED_RAW_FORMATS = [
    "rgbpack",
    "rgbplanar",
    "argb4444",
    "argb1555",
    "nv12",
    "nv21",
    "nv16",
    "nv61",
    "yuv422yuyv",
    "yuv422yvyu",
    "yuv422vyuy",
    "yuv422uyvy",
    "yuv444p",
    "yuv422p",
    "yuv420p",
    "yonly",
]

COMMON_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}

# 文件名中常见格式别名 -> 内部标准格式
FORMAT_ALIASES = {
    "yuv444": "yuv444p",
    "yuv422": "yuv422p",
    "yuv420": "yuv420p",
    "rgb888": "rgbpack",
    "rgbpacked": "rgbpack",
    "rgb": "rgbpack",
    "argb444": "argb4444",
    "argb155": "argb1555",
    "gray": "yonly",
}

APP_DARK_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #0b1118;
    color: #d7e3f4;
}

QMenuBar {
    background-color: #0e1621;
    color: #d7e3f4;
    border-bottom: 1px solid #1f3246;
}
QMenuBar::item {
    padding: 6px 10px;
    background: transparent;
}
QMenuBar::item:selected {
    background-color: #19324b;
}

QMenu {
    background-color: #0f1a27;
    color: #d7e3f4;
    border: 1px solid #28435f;
}
QMenu::item:selected {
    background-color: #1a3550;
}
QMenu::separator {
    height: 1px;
    background: #6aa9e9;
    margin: 4px 8px;
}

QStatusBar {
    background-color: #0e1621;
    color: #9fc7ff;
    border-top: 1px solid #1f3246;
}
QStatusBar QLabel {
    color: #9fc7ff;
}

QTreeWidget, QScrollArea {
    background-color: #0f1a27;
    color: #d7e3f4;
    border: 1px solid #28435f;
    show-decoration-selected: 0;
}
QTreeWidget::item:selected {
    background-color: #214366;
    color: #ffffff;
}

QLabel {
    color: #d7e3f4;
}

QLineEdit, QComboBox {
    background-color: #132131;
    color: #d7e3f4;
    border: 1px solid #2d4a67;
    border-radius: 4px;
    padding: 6px 8px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #4f8dc9;
}
QComboBox QAbstractItemView {
    background-color: #132131;
    color: #d7e3f4;
    border: 1px solid #2d4a67;
    selection-background-color: #214366;
}

QPushButton {
    background-color: #1b3b5a;
    color: #e8f3ff;
    border: 1px solid #33587a;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #25527b;
}
QPushButton:pressed {
    background-color: #17344e;
}
QPushButton:disabled {
    background-color: #24384c;
    color: #8ea8c5;
}

QSplitter::handle {
    background-color: #1b2b3b;
}

#imageHintLabel {
    color: #9fb3c8;
    background-color: #0f1a27;
    border: none;
}
"""

APP_LIGHT_QSS = """
QMainWindow, QDialog, QWidget {
    background-color: #f4f6f9;
    color: #2a3138;
}

QMenuBar {
    background-color: #ffffff;
    color: #2a3138;
    border-bottom: 1px solid #cfd7e2;
}
QMenuBar::item {
    padding: 6px 10px;
    background: transparent;
}
QMenuBar::item:selected {
    background-color: #e7eef7;
}

QMenu {
    background-color: #ffffff;
    color: #2a3138;
    border: 1px solid #cfd7e2;
}
QMenu::item:selected {
    background-color: #e7eef7;
}
QMenu::separator {
    height: 1px;
    background: #84b6ea;
    margin: 4px 8px;
}

QStatusBar {
    background-color: #ffffff;
    color: #3a4d63;
    border-top: 1px solid #cfd7e2;
}
QStatusBar QLabel {
    color: #3a4d63;
}

QTreeWidget, QScrollArea {
    background-color: #ffffff;
    color: #2a3138;
    border: 1px solid #cfd7e2;
    show-decoration-selected: 0;
}
QTreeWidget::item:selected {
    background-color: #d7e4f5;
    color: #1f2933;
}

QLabel {
    color: #2a3138;
}

/* 与深色主题一致：不自定义 QComboBox::drop-down，由 Fusion 绘制原生下三角 */
QLineEdit, QComboBox {
    background-color: #ffffff;
    color: #2a3138;
    border: 1px solid #b9c6d6;
    border-radius: 4px;
    padding: 6px 8px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #5b8fc5;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #2a3138;
    border: 1px solid #b9c6d6;
    selection-background-color: #d7e4f5;
}

QPushButton {
    background-color: #e5ebf3;
    color: #223041;
    border: 1px solid #b9c6d6;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #dce5f0;
}
QPushButton:pressed {
    background-color: #ccd9e8;
}
QPushButton:disabled {
    background-color: #f0f2f5;
    color: #8a95a3;
}

QSplitter::handle {
    background-color: #d5dde8;
}

#imageHintLabel {
    color: #5a6775;
    background-color: #ffffff;
    border: none;
}
"""


MESSAGE_BOX_QSS = """
QMessageBox {
    background-color: #0b1118;
}
QMessageBox QLabel {
    color: #d7e3f4;
}
QMessageBox QPushButton {
    min-width: 72px;
}
"""

MESSAGE_BOX_LIGHT_QSS = """
QMessageBox {
    background-color: #f4f6f9;
}
QMessageBox QLabel {
    color: #2a3138;
}
QMessageBox QPushButton {
    min-width: 72px;
}
"""


def apply_titlebar_theme(widget, dark=True):
    """在 Windows 上启用系统标题栏主题（若系统支持）。"""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_uint(attr),
                ctypes.byref(value),
                ctypes.sizeof(value),
            )

        # 显式设置标题栏颜色与文字颜色，避免某些系统仅在失焦/子窗口后才刷新
        DWMWA_BORDER_COLOR = 34
        DWMWA_CAPTION_COLOR = 35
        DWMWA_TEXT_COLOR = 36

        def to_colorref(r, g, b):
            # Windows COLORREF: 0x00bbggrr
            return ctypes.c_uint32((b << 16) | (g << 8) | r)

        if dark:
            border = to_colorref(0x1F, 0x32, 0x46)
            caption = to_colorref(0x0E, 0x16, 0x21)
            text = to_colorref(0xD7, 0xE3, 0xF4)
        else:
            border = to_colorref(0xCF, 0xD7, 0xE2)
            caption = to_colorref(0xF4, 0xF6, 0xF9)
            text = to_colorref(0x2A, 0x31, 0x38)

        for attr, color in (
            (DWMWA_BORDER_COLOR, border),
            (DWMWA_CAPTION_COLOR, caption),
            (DWMWA_TEXT_COLOR, text),
        ):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                ctypes.c_uint(attr),
                ctypes.byref(color),
                ctypes.sizeof(color),
            )

        # 强制刷新非客户区，确保标题栏主题立即生效
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_NOZORDER = 0x0004
        SWP_NOACTIVATE = 0x0010
        SWP_FRAMECHANGED = 0x0020
        ctypes.windll.user32.SetWindowPos(
            ctypes.c_void_p(hwnd),
            ctypes.c_void_p(0),
            0,
            0,
            0,
            0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )

        # 通知系统主题变化并强制立即重绘标题栏
        WM_THEMECHANGED = 0x031A
        RDW_INVALIDATE = 0x0001
        RDW_ALLCHILDREN = 0x0080
        RDW_UPDATENOW = 0x0100
        RDW_FRAME = 0x0400
        ctypes.windll.user32.SendMessageW(ctypes.c_void_p(hwnd), WM_THEMECHANGED, 0, 0)
        ctypes.windll.user32.RedrawWindow(
            ctypes.c_void_p(hwnd),
            ctypes.c_void_p(0),
            ctypes.c_void_p(0),
            RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_UPDATENOW | RDW_FRAME,
        )

        # 强制触发非客户区激活刷新，避免“必须弹子窗口后才变色”
        WM_NCACTIVATE = 0x0086
        ctypes.windll.user32.SendMessageW(ctypes.c_void_p(hwnd), WM_NCACTIVATE, 0, 0)
        ctypes.windll.user32.SendMessageW(ctypes.c_void_p(hwnd), WM_NCACTIVATE, 1, 0)
    except Exception:
        pass


def show_themed_message(parent, icon, title, text):
    box = QMessageBox(parent)
    _ = icon  # 保留参数签名，提示框内容区域不显示图标
    box.setIcon(QMessageBox.NoIcon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.Ok)
    box.setStyleSheet(MESSAGE_BOX_QSS if ACTIVE_THEME == "dark" else MESSAGE_BOX_LIGHT_QSS)
    if os.path.exists(INFO_ICON_PATH):
        info_icon = QIcon(INFO_ICON_PATH)
        box.setWindowIcon(info_icon)
    apply_titlebar_theme(box, dark=(ACTIVE_THEME == "dark"))
    box.exec_()


class ProcessingThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def run(self):
        success, message = FileProcessor.process_file(self.params)
        self.finished.emit(success, message)


class ImageCanvasLabel(QLabel):
    """图像区：左键选取图像像素（坐标相对图像左上角）；右键清除；绘制青绿色高亮框。"""

    pixel_picked = pyqtSignal(int, int)
    pick_cleared = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._pick_ix = None
        self._pick_iy = None
        self._src_w = 0
        self._src_h = 0
        self._pan_target = None
        self._is_shift_panning = False
        self._pan_last_global = None

    def clear_pick(self):
        self._pick_ix = None
        self._pick_iy = None
        self.update()

    def set_source_size(self, w: int, h: int):
        self._src_w = max(0, int(w))
        self._src_h = max(0, int(h))

    def set_pan_target(self, scroll_area: QScrollArea):
        self._pan_target = scroll_area

    def pick_image_xy(self):
        if self._pick_ix is None or self._pick_iy is None:
            return None
        return (self._pick_ix, self._pick_iy)

    def pixmap_rect_in_label(self):
        """当前绘制的 pixmap 在 label 内的位置 (off_x, off_y, pw, ph)；无 pixmap 返回 None。"""
        pm = self.pixmap()
        if pm is None or pm.isNull():
            return None
        pw, ph = pm.width(), pm.height()
        lw, lh = self.width(), self.height()
        off_x = max(0, (lw - pw) // 2)
        off_y = max(0, (lh - ph) // 2)
        return (off_x, off_y, pw, ph)

    def label_to_image_float(self, lx: float, ly: float):
        """label 内坐标对应到图像连续坐标 (ix,iy)；点在 pixmap 外返回 None。"""
        if self._src_w < 1 or self._src_h < 1:
            return None
        r = self.pixmap_rect_in_label()
        if r is None:
            return None
        off_x, off_y, pw, ph = r
        px = lx - off_x
        py = ly - off_y
        if px < 0 or py < 0 or px >= pw or py >= ph:
            return None
        return (px * self._src_w / pw, py * self._src_h / ph)

    def label_to_image_int_pixel(self, lx: int, ly: int):
        t = self.label_to_image_float(float(lx), float(ly))
        if t is None:
            return None
        ix_f, iy_f = t
        ix = int(max(0, min(self._src_w - 1, ix_f)))
        iy = int(max(0, min(self._src_h - 1, iy_f)))
        return (ix, iy)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ShiftModifier) and self._pan_target is not None:
            self._is_shift_panning = True
            self._pan_last_global = event.globalPos()
            self.setCursor(Qt.OpenHandCursor)
            return
        if event.button() == Qt.LeftButton:
            picked = self.label_to_image_int_pixel(event.x(), event.y())
            if picked is None:
                return
            ix, iy = picked
            self._pick_ix = ix
            self._pick_iy = iy
            self.update()
            self.pixel_picked.emit(ix, iy)
            return
        if event.button() == Qt.RightButton:
            self.clear_pick()
            self.pick_cleared.emit()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_shift_panning and self._pan_target is not None and self._pan_last_global is not None:
            delta = event.globalPos() - self._pan_last_global
            self._pan_last_global = event.globalPos()
            hbar = self._pan_target.horizontalScrollBar()
            vbar = self._pan_target.verticalScrollBar()
            hbar.setValue(hbar.value() - delta.x())
            vbar.setValue(vbar.value() - delta.y())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._is_shift_panning:
            self._is_shift_panning = False
            self._pan_last_global = None
            self.unsetCursor()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._pick_ix is None or self._pick_iy is None:
            return
        r = self.pixmap_rect_in_label()
        if r is None or self._src_w < 1 or self._src_h < 1:
            return
        off_x, off_y, dw, dh = r
        ix, iy = self._pick_ix, self._pick_iy
        x0 = int(ix * dw / self._src_w)
        y0 = int(iy * dh / self._src_h)
        rw = max(1, int(round(dw / self._src_w)))
        rh = max(1, int(round(dh / self._src_h)))
        painter = QPainter(self)
        pen = QPen(QColor(0, 220, 180))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(off_x + x0, off_y + y0, rw, rh)


class ZoomScrollArea(QScrollArea):
    """支持 Ctrl + 滚轮缩放的滚动区域。"""

    zoom_requested = pyqtSignal(float, QPoint)
    file_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.viewport():
            if event.type() == QEvent.DragEnter:
                if self._has_local_file(event):
                    event.acceptProposedAction()
                else:
                    event.ignore()
                return True
            if event.type() == QEvent.Drop:
                file_path = self._first_local_file(event)
                if file_path:
                    self.file_dropped.emit(file_path)
                    event.acceptProposedAction()
                else:
                    event.ignore()
                return True
        return super().eventFilter(obj, event)

    def wheelEvent(self, event):
        if QApplication.keyboardModifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            pos_vp = self.viewport().mapFrom(self, event.pos())
            self.zoom_requested.emit(1.1 if delta > 0 else 0.9, pos_vp)
            event.accept()
            return
        super().wheelEvent(event)

    @staticmethod
    def _has_local_file(event):
        mime = event.mimeData()
        if not mime or not mime.hasUrls():
            return False
        for url in mime.urls():
            if url.isLocalFile():
                return True
        return False

    @staticmethod
    def _first_local_file(event):
        mime = event.mimeData()
        if not mime or not mime.hasUrls():
            return ""
        for url in mime.urls():
            if url.isLocalFile():
                return url.toLocalFile()
        return ""


class FileConverterDialog(QDialog):
    """当前工程转换功能，以对话框方式展示。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.processing_thread = None
        self._titlebar_theme_applied = False
        self.setWindowTitle("转为格式")
        if os.path.exists(APP_ICON_PATH):
            self.setWindowIcon(QIcon(APP_ICON_PATH))
        self.setMinimumSize(760, 460)
        self._init_ui()
        self._setup_connections()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._titlebar_theme_applied:
            apply_titlebar_theme(self, dark=(ACTIVE_THEME == "dark"))
            self._titlebar_theme_applied = True

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("文件格式转换")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(14)

        self.input_text = QLineEdit()
        self.input_text.setPlaceholderText("请选择输入文件（jpg/png/bmp）")
        self.input_btn = QPushButton("选择文件")
        grid.addWidget(QLabel("输入文件:"), 0, 0)
        grid.addWidget(self.input_text, 0, 1)
        grid.addWidget(self.input_btn, 0, 2)

        self.format_combo = QComboBox()
        self.format_combo.addItems(SUPPORTED_RAW_FORMATS)
        self.format_display = QLabel(f"格式: {SUPPORTED_RAW_FORMATS[0]}")
        grid.addWidget(QLabel("输出格式:"), 1, 0)
        grid.addWidget(self.format_combo, 1, 1)
        grid.addWidget(self.format_display, 1, 2)

        self.alpha_label = QLabel("Alpha (0–255):")
        self.alpha_spin = QSpinBox()
        self.alpha_spin.setRange(0, 255)
        self.alpha_spin.setValue(255)
        self.alpha_spin.setToolTip("0 为全透明，255 为不透明。\nARGB1555 仅 1 位透明度：≥128 记为不透明，否则透明。")
        self.alpha_hint = QLabel("ARGB4444 量化为 4 位；ARGB1555 为 1 位（≥128 不透明）")
        self.alpha_hint.setWordWrap(True)
        self.alpha_hint.setStyleSheet("color: #8aa0b8; font-size: 11px;")
        grid.addWidget(self.alpha_label, 2, 0)
        grid.addWidget(self.alpha_spin, 2, 1)
        grid.addWidget(self.alpha_hint, 2, 2)

        self.resolution_combo = QComboBox()
        self.resolution_combo.setEditable(True)
        self.resolution_combo.addItems(
            ["64x64", "512x512", "1280x720", "1920x1080", "3840x2160", "4096x2160"]
        )
        self.resolution_display = QLabel("宽高: 64x64")
        grid.addWidget(QLabel("输出分辨率:"), 3, 0)
        grid.addWidget(self.resolution_combo, 3, 1)
        grid.addWidget(self.resolution_display, 3, 2)

        self.output_text = QLineEdit()
        self.output_text.setPlaceholderText("请选择输出目录")
        self.output_btn = QPushButton("选择目录")
        grid.addWidget(QLabel("输出路径:"), 4, 0)
        grid.addWidget(self.output_text, 4, 1)
        grid.addWidget(self.output_btn, 4, 2)

        layout.addLayout(grid)

        self.progress_label = QLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #3498db;")
        layout.addWidget(self.progress_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.reset_btn = QPushButton("重置")
        self.convert_btn = QPushButton("开始转换")
        btn_row.addWidget(self.reset_btn)
        btn_row.addWidget(self.convert_btn)
        layout.addLayout(btn_row)

    def _setup_connections(self):
        self.input_btn.clicked.connect(self.select_input_file)
        self.output_btn.clicked.connect(self.select_output_folder)
        self.reset_btn.clicked.connect(self.reset_form)
        self.convert_btn.clicked.connect(self.start_conversion)
        self.format_combo.currentTextChanged.connect(self._on_output_format_changed)
        self.resolution_combo.currentTextChanged.connect(self._update_resolution_display)
        self.resolution_combo.editTextChanged.connect(self._update_resolution_display)
        self._on_output_format_changed(self.format_combo.currentText())
        self._update_resolution_display(self.resolution_combo.currentText())

    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择输入文件",
            "",
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*.*)",
        )
        if not file_path:
            return
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in COMMON_IMAGE_EXTS:
            show_themed_message(self, QMessageBox.Warning, "格式不支持", "转换输入仅支持 png/jpg/jpeg/bmp/webp。")
            return
        self.input_text.setText(file_path)
        if not self.output_text.text():
            self.output_text.setText(os.path.dirname(file_path))

    def select_output_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择输出文件夹", "")
        if folder_path:
            self.output_text.setText(folder_path)

    def _update_format_display(self, text):
        self.format_display.setText(f"格式: {text}")

    def _on_output_format_changed(self, text: str):
        self._update_format_display(text)
        show_alpha = text in ("argb4444", "argb1555")
        self.alpha_label.setVisible(show_alpha)
        self.alpha_spin.setVisible(show_alpha)
        self.alpha_hint.setVisible(show_alpha)

    def _update_resolution_display(self, text):
        self.resolution_display.setText(f"宽高: {text}" if text else "宽高:")

    def reset_form(self):
        self.input_text.clear()
        self.output_text.clear()
        self.format_combo.setCurrentIndex(0)
        self.alpha_spin.setValue(255)
        self.resolution_combo.setCurrentIndex(0)

    def start_conversion(self):
        if not self.input_text.text():
            show_themed_message(self, QMessageBox.Warning, "警告", "请选择输入文件。")
            return
        if not self.output_text.text():
            show_themed_message(self, QMessageBox.Warning, "警告", "请选择输出路径。")
            return

        width, height, error_msg = parse_resolution(self.resolution_combo.currentText())
        if error_msg:
            show_themed_message(self, QMessageBox.Warning, "警告", error_msg)
            return

        params = {
            "input_file": self.input_text.text(),
            "output_format": self.format_combo.currentText(),
            "width": width,
            "height": height,
            "output_dir": self.output_text.text(),
        }
        fmt = params["output_format"]
        if fmt in ("argb4444", "argb1555"):
            params["packed_alpha_8"] = self.alpha_spin.value()
        params["output_filename"] = FileProcessor.generate_output_filename(params)

        self.set_buttons_enabled(False)
        self.progress_label.setText("转换中，请稍候...")
        self.processing_thread = ProcessingThread(params)
        self.processing_thread.finished.connect(self.on_processing_finished)
        self.processing_thread.start()

    def on_processing_finished(self, success, message):
        self.set_buttons_enabled(True)
        self.progress_label.setText("")
        if success:
            show_themed_message(self, QMessageBox.Information, "转换成功", message)
        else:
            show_themed_message(self, QMessageBox.Critical, "转换失败", message)

    def set_buttons_enabled(self, enabled):
        self.convert_btn.setEnabled(enabled)
        self.reset_btn.setEnabled(enabled)
        self.input_btn.setEnabled(enabled)
        self.output_btn.setEnabled(enabled)
        self.alpha_spin.setEnabled(enabled)


def _name_has_format_token(text: str, token: str) -> bool:
    """文件名/主干中是否包含独立格式词（前后为非字母数字或边界）。"""
    return bool(re.search(rf"(^|[^a-z0-9]){re.escape(token)}([^a-z0-9]|$)", text))


def _infer_format(path: str) -> str:
    name = os.path.basename(path).lower()
    stem = os.path.splitext(name)[0]
    ext = os.path.splitext(name)[1].lower().lstrip(".")
    if ext in SUPPORTED_RAW_FORMATS:
        return ext
    if ext == "rgb":
        return "rgbpack"

    # 优先按标准格式名在文件名中匹配（兼容 .bin 等扩展名）
    # 例如 512x256_nv21.bin、foo-yuv422yuyv.raw
    for fmt in sorted(SUPPORTED_RAW_FORMATS, key=len, reverse=True):
        if _name_has_format_token(name, fmt):
            return fmt

    # 再按常见别名匹配并映射到标准格式（长名优先，避免 rgb 误抢 rgb888）
    # 例如 64x64_yuv444.bin -> yuv444p；512x256_rgb.bin -> rgbpack
    for alias, mapped_fmt in sorted(FORMAT_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if _name_has_format_token(name, alias) or _name_has_format_token(stem, alias):
            return mapped_fmt

    # 最后按独立词元匹配简写（须先于泛化的 rgb，且不误匹配 srgb 等）
    if _name_has_format_token(stem, "rgbplanar") or _name_has_format_token(stem, "rgbp"):
        return "rgbplanar"
    if _name_has_format_token(stem, "rgbpack"):
        return "rgbpack"
    if _name_has_format_token(stem, "gray"):
        return "yonly"
    if _name_has_format_token(stem, "rgb888") or _name_has_format_token(stem, "rgb"):
        return "rgbpack"
    return ""


def _infer_resolution_from_name(path: str):
    name = os.path.basename(path)
    # 优先识别常见的“宽x高”写法（x/X/×），并取最后一组，避免文件名前缀数字干扰。
    # 例如: 2_640x480.yuv -> (640, 480)（而不是旧逻辑误判为 2x640）
    matches = re.findall(r"(\d+)\s*[xX×]\s*(\d+)", name)
    if not matches:
        return None, None
    w, h = matches[-1]
    return int(w), int(h)


def _rgb888_to_yuv_bt601_full_pixel(r: int, g: int, b: int) -> tuple:
    """与 generator._rgb_to_yuv_bt601_full_range 一致的单像素 BT.601 full range。"""
    rf = float(r)
    gf = float(g)
    bf = float(b)
    y = 0.299 * rf + 0.587 * gf + 0.114 * bf
    u = -0.168736 * rf - 0.331264 * gf + 0.5 * bf + 128.0
    v = 0.5 * rf - 0.418688 * gf - 0.081312 * bf + 128.0
    return (
        int(max(0, min(255, round(y)))),
        int(max(0, min(255, round(u)))),
        int(max(0, min(255, round(v)))),
    )


def _format_pixel_value_for_status(display_format: str, r: int, g: int, b: int) -> str:
    """按当前显示格式语义输出状态栏数值文案（基于屏幕上该像素的 RGB）。"""
    if display_format in ("普通图片", "rgbpack", "rgbplanar", "-"):
        return f"RGB({r},{g},{b})"
    if display_format == "argb4444":
        a4, r4, g4, b4 = 15, (r * 15 + 127) // 255, (g * 15 + 127) // 255, (b * 15 + 127) // 255
        packed = (a4 << 12) | (r4 << 8) | (g4 << 4) | b4
        return f"ARGB4444=0x{packed:04X} (A4,R4,G4,B4)=({a4},{r4},{g4},{b4})"
    if display_format == "argb1555":
        r5, g5, b5 = (r * 31 + 127) // 255, (g * 31 + 127) // 255, (b * 31 + 127) // 255
        packed = (1 << 15) | (r5 << 10) | (g5 << 5) | b5
        return f"ARGB1555=0x{packed:04X} (A1,R5,G5,B5)=(1,{r5},{g5},{b5})"
    if display_format == "yonly":
        return f"Y={r}"
    y, u, v = _rgb888_to_yuv_bt601_full_pixel(r, g, b)
    return f"YUV({y},{u},{v})"


def _yuv_to_rgb(y: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    yf = y.astype(np.float32)
    uf = u.astype(np.float32) - 128.0
    vf = v.astype(np.float32) - 128.0
    r = yf + 1.402 * vf
    g = yf - 0.344136 * uf - 0.714136 * vf
    b = yf + 1.772 * uf
    rgb = np.stack([r, g, b], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def _ensure_size(data: bytes, expected: int, fmt: str):
    if len(data) != expected:
        raise ValueError(f"{fmt} 数据大小不匹配，期望 {expected} 字节，实际 {len(data)} 字节")


def _decode_raw_to_rgb(path: str, fmt: str, width: int, height: int) -> np.ndarray:
    with open(path, "rb") as f:
        data = f.read()

    y_size = width * height

    if fmt == "rgbpack":
        _ensure_size(data, y_size * 3, fmt)
        return np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))

    if fmt == "rgbplanar":
        _ensure_size(data, y_size * 3, fmt)
        arr = np.frombuffer(data, dtype=np.uint8)
        r = arr[:y_size].reshape((height, width))
        g = arr[y_size : 2 * y_size].reshape((height, width))
        b = arr[2 * y_size :].reshape((height, width))
        return np.stack([r, g, b], axis=-1)

    if fmt == "argb4444":
        _ensure_size(data, y_size * 2, fmt)
        arr = np.frombuffer(data, dtype="<u2").reshape((height, width))
        r4 = (arr >> 8) & 0xF
        g4 = (arr >> 4) & 0xF
        b4 = arr & 0xF
        r = ((r4 * 255 + 7) // 15).astype(np.uint8)
        g = ((g4 * 255 + 7) // 15).astype(np.uint8)
        b = ((b4 * 255 + 7) // 15).astype(np.uint8)
        return np.stack([r, g, b], axis=-1)

    if fmt == "argb1555":
        _ensure_size(data, y_size * 2, fmt)
        arr = np.frombuffer(data, dtype="<u2").reshape((height, width))
        r5 = (arr >> 10) & 0x1F
        g5 = (arr >> 5) & 0x1F
        b5 = arr & 0x1F
        r = ((r5 * 255 + 15) // 31).astype(np.uint8)
        g = ((g5 * 255 + 15) // 31).astype(np.uint8)
        b = ((b5 * 255 + 15) // 31).astype(np.uint8)
        return np.stack([r, g, b], axis=-1)

    if fmt == "yonly":
        _ensure_size(data, y_size, fmt)
        y = np.frombuffer(data, dtype=np.uint8).reshape((height, width))
        return np.stack([y, y, y], axis=-1)

    if fmt == "yuv420p":
        uv_size = (width // 2) * (height // 2)
        _ensure_size(data, y_size + uv_size * 2, fmt)
        arr = np.frombuffer(data, dtype=np.uint8)
        y = arr[:y_size].reshape((height, width))
        u = arr[y_size : y_size + uv_size].reshape((height // 2, width // 2))
        v = arr[y_size + uv_size :].reshape((height // 2, width // 2))
        u444 = np.repeat(np.repeat(u, 2, axis=0), 2, axis=1)
        v444 = np.repeat(np.repeat(v, 2, axis=0), 2, axis=1)
        return _yuv_to_rgb(y, u444, v444)

    if fmt in {"nv12", "nv21"}:
        uv_size = (width // 2) * (height // 2) * 2
        _ensure_size(data, y_size + uv_size, fmt)
        arr = np.frombuffer(data, dtype=np.uint8)
        y = arr[:y_size].reshape((height, width))
        uv = arr[y_size:].reshape((height // 2, width))
        c0 = uv[:, 0::2]
        c1 = uv[:, 1::2]
        u = c0 if fmt == "nv12" else c1
        v = c1 if fmt == "nv12" else c0
        u444 = np.repeat(np.repeat(u, 2, axis=0), 2, axis=1)
        v444 = np.repeat(np.repeat(v, 2, axis=0), 2, axis=1)
        return _yuv_to_rgb(y, u444, v444)

    if fmt == "yuv422p":
        uv_size = (width // 2) * height
        _ensure_size(data, y_size + uv_size * 2, fmt)
        arr = np.frombuffer(data, dtype=np.uint8)
        y = arr[:y_size].reshape((height, width))
        u = arr[y_size : y_size + uv_size].reshape((height, width // 2))
        v = arr[y_size + uv_size :].reshape((height, width // 2))
        u444 = np.repeat(u, 2, axis=1)
        v444 = np.repeat(v, 2, axis=1)
        return _yuv_to_rgb(y, u444, v444)

    if fmt in {"nv16", "nv61"}:
        uv_size = width * height
        _ensure_size(data, y_size + uv_size, fmt)
        arr = np.frombuffer(data, dtype=np.uint8)
        y = arr[:y_size].reshape((height, width))
        uv = arr[y_size:].reshape((height, width))
        c0 = uv[:, 0::2]
        c1 = uv[:, 1::2]
        u = c0 if fmt == "nv16" else c1
        v = c1 if fmt == "nv16" else c0
        u444 = np.repeat(u, 2, axis=1)
        v444 = np.repeat(v, 2, axis=1)
        return _yuv_to_rgb(y, u444, v444)

    if fmt == "yuv444p":
        _ensure_size(data, y_size * 3, fmt)
        arr = np.frombuffer(data, dtype=np.uint8)
        y = arr[:y_size].reshape((height, width))
        u = arr[y_size : 2 * y_size].reshape((height, width))
        v = arr[2 * y_size :].reshape((height, width))
        return _yuv_to_rgb(y, u, v)

    if fmt in {"yuv422yuyv", "yuv422yvyu", "yuv422vyuy", "yuv422uyvy"}:
        _ensure_size(data, y_size * 2, fmt)
        row = np.frombuffer(data, dtype=np.uint8).reshape((height, width * 2))
        if fmt == "yuv422yuyv":
            y0, u, y1, v = row[:, 0::4], row[:, 1::4], row[:, 2::4], row[:, 3::4]
        elif fmt == "yuv422yvyu":
            y0, v, y1, u = row[:, 0::4], row[:, 1::4], row[:, 2::4], row[:, 3::4]
        elif fmt == "yuv422vyuy":
            v, y0, u, y1 = row[:, 0::4], row[:, 1::4], row[:, 2::4], row[:, 3::4]
        else:
            u, y0, v, y1 = row[:, 0::4], row[:, 1::4], row[:, 2::4], row[:, 3::4]

        y = np.empty((height, width), dtype=np.uint8)
        y[:, 0::2] = y0
        y[:, 1::2] = y1
        u444 = np.repeat(u, 2, axis=1)
        v444 = np.repeat(v, 2, axis=1)
        return _yuv_to_rgb(y, u444, v444)

    raise ValueError(f"暂不支持预览格式: {fmt}")


class ImageViewerMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = ""
        self.current_file_md5 = ""
        self.current_rgb = None
        self.base_pixmap = None
        self._display_image = None  # 与当前显示一致的 QImage，用于底部栏像素取样
        self.root_dir = ""
        self.selected_display_format = ""
        self.current_display_format = "-"
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 20.0
        self.fit_to_window = True
        self.image_smooth_scaling = False  # False=最近邻清晰像素；True=双线性平滑
        self._init_ui()
        self._init_menu()
        self._titlebar_theme_applied = False

    def _init_ui(self):
        self.setWindowTitle(APP_TITLE)
        if os.path.exists(APP_ICON_PATH):
            self.setWindowIcon(QIcon(APP_ICON_PATH))
        self.setMinimumSize(1120, 720)
        self.resize(1240, 820)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabel("目录结构")
        self.tree_widget.setMinimumWidth(280)
        self.tree_widget.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.tree_widget.itemClicked.connect(self.on_tree_item_clicked)
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.on_tree_context_menu)
        splitter.addWidget(self.tree_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = ZoomScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.zoom_requested.connect(lambda f, p: self.zoom_by(f, p))
        self.scroll_area.file_dropped.connect(self._handle_dropped_file)
        self.image_label = ImageCanvasLabel(IMAGE_HINT_INITIAL)
        self.image_label.setObjectName("imageHintLabel")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setAutoFillBackground(False)
        self.image_label.setMinimumSize(400, 300)
        self.image_label.set_pan_target(self.scroll_area)
        self.image_label.pixel_picked.connect(self._on_image_pixel_picked)
        self.image_label.pick_cleared.connect(self._update_status_footer)
        self.scroll_area.setWidget(self.image_label)
        right_layout.addWidget(self.scroll_area)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.status_summary_label = QLabel("文件: - | MD5: - | 格式: - | 缩放: 100.0%")
        self.statusBar().addPermanentWidget(self.status_summary_label, 1)
        self._esc_clear_pick = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._esc_clear_pick.setContext(Qt.WidgetWithChildrenShortcut)
        self._esc_clear_pick.activated.connect(self._clear_pixel_pick_shortcut)
        self._update_status_footer()

    def _init_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("文件")
        process_menu = menu_bar.addMenu("处理")
        view_menu = menu_bar.addMenu("查看")
        format_menu = menu_bar.addMenu("图像格式")
        theme_menu = menu_bar.addMenu("界面显示")
        help_menu = menu_bar.addMenu("使用说明")

        open_file_action = QAction("打开文件", self)
        open_file_action.triggered.connect(self.open_file)
        file_menu.addAction(open_file_action)

        open_folder_action = QAction("打开文件夹", self)
        open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_action)

        convert_action = QAction("转为格式", self)
        convert_action.triggered.connect(self.open_converter_dialog)
        process_menu.addAction(convert_action)

        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_dark_action = QAction("深色界面", self, checkable=True)
        self.theme_light_action = QAction("浅色界面", self, checkable=True)
        self.theme_dark_action.setChecked(True)
        self.theme_dark_action.triggered.connect(lambda: self._set_theme("dark"))
        self.theme_light_action.triggered.connect(lambda: self._set_theme("light"))
        self.theme_group.addAction(self.theme_dark_action)
        self.theme_group.addAction(self.theme_light_action)
        theme_menu.addAction(self.theme_dark_action)
        theme_menu.addAction(self.theme_light_action)

        self.display_format_group = QActionGroup(self)
        self.display_format_group.setExclusive(True)
        self.display_format_actions = {}

        auto_action = QAction("自动识别", self, checkable=True)
        auto_action.setChecked(True)
        auto_action.triggered.connect(lambda: self._set_display_format(""))
        self.display_format_group.addAction(auto_action)
        self.display_format_actions[""] = auto_action
        format_menu.addAction(auto_action)
        format_menu.addSeparator()

        for fmt in SUPPORTED_RAW_FORMATS:
            action = QAction(fmt, self, checkable=True)
            action.triggered.connect(lambda checked, value=fmt: self._set_display_format(value))
            self.display_format_group.addAction(action)
            self.display_format_actions[fmt] = action
            format_menu.addAction(action)

        zoom_in_action = QAction("放大", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(lambda: self.zoom_by(1.25))
        view_menu.addAction(zoom_in_action)

        zoom_out_action = QAction("缩小", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(lambda: self.zoom_by(0.8))
        view_menu.addAction(zoom_out_action)

        reset_zoom_action = QAction("100%", self)
        reset_zoom_action.setShortcut("Ctrl+0")
        reset_zoom_action.triggered.connect(self.reset_zoom)
        view_menu.addAction(reset_zoom_action)

        fit_action = QAction("适应窗口", self)
        fit_action.setShortcut("Ctrl+9")
        fit_action.triggered.connect(self.enable_fit_to_window)
        view_menu.addAction(fit_action)

        view_menu.addSeparator()
        self.smooth_scale_group = QActionGroup(self)
        self.smooth_off_action = QAction("图像平滑：关（默认）", self, checkable=True)
        self.smooth_on_action = QAction("图像平滑：开", self, checkable=True)
        self.smooth_off_action.setChecked(True)
        self.smooth_scale_group.addAction(self.smooth_off_action)
        self.smooth_scale_group.addAction(self.smooth_on_action)
        self.smooth_scale_group.triggered.connect(self._on_smooth_scale_action)
        view_menu.addAction(self.smooth_off_action)
        view_menu.addAction(self.smooth_on_action)

        usage_action = QAction("查看使用说明", self)
        usage_action.triggered.connect(self.open_usage_dialog)
        help_menu.addAction(usage_action)

    def open_file(self):
        raw_filters = " ".join(f"*.{fmt}" for fmt in SUPPORTED_RAW_FORMATS)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "打开文件",
            "",
            f"支持格式 (*.png *.jpg *.jpeg *.bmp *.webp {raw_filters});;所有文件 (*.*)",
        )
        if not file_path:
            return

        self._open_file_in_context(file_path)

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "打开文件夹", "")
        if not folder_path:
            return
        self.root_dir = folder_path
        self._build_tree(folder_path)
        self.current_file = ""
        self.current_file_md5 = ""
        self.base_pixmap = None
        self._display_image = None
        self.image_label.clear_pick()
        self.image_label.set_source_size(0, 0)
        self.image_label.setMinimumSize(400, 300)
        self.current_display_format = "-"
        self.image_label.setText(IMAGE_HINT_INITIAL)
        self._update_status_footer()
        self.statusBar().showMessage(f"已打开文件夹: {folder_path}")

    def _build_tree(self, root_path: str):
        self.tree_widget.clear()
        root_name = os.path.basename(root_path.rstrip("\\/")) or root_path
        root_item = QTreeWidgetItem([root_name])
        root_item.setData(0, Qt.UserRole, root_path)
        self.tree_widget.addTopLevelItem(root_item)
        self._add_tree_children(root_item, root_path)
        root_item.setExpanded(True)

    def _add_tree_children(self, parent_item: QTreeWidgetItem, folder_path: str):
        try:
            entries = sorted(os.listdir(folder_path), key=lambda name: (not os.path.isdir(os.path.join(folder_path, name)), name.lower()))
        except Exception:
            return

        for name in entries:
            full_path = os.path.join(folder_path, name)
            child = QTreeWidgetItem([name])
            child.setData(0, Qt.UserRole, full_path)
            parent_item.addChild(child)
            if os.path.isdir(full_path):
                self._add_tree_children(child, full_path)

    def _select_path_in_tree(self, target_path: str):
        target_path = os.path.normcase(os.path.abspath(target_path))

        def dfs(item: QTreeWidgetItem):
            path = item.data(0, Qt.UserRole)
            if path and os.path.normcase(os.path.abspath(path)) == target_path:
                self.tree_widget.setCurrentItem(item)
                parent = item.parent()
                while parent is not None:
                    parent.setExpanded(True)
                    parent = parent.parent()
                return True
            for i in range(item.childCount()):
                if dfs(item.child(i)):
                    return True
            return False

        for i in range(self.tree_widget.topLevelItemCount()):
            if dfs(self.tree_widget.topLevelItem(i)):
                break

    def on_tree_item_clicked(self, item: QTreeWidgetItem):
        path = item.data(0, Qt.UserRole)
        if path and os.path.isfile(path):
            self.load_and_display_file(path)

    def on_tree_context_menu(self, pos):
        item = self.tree_widget.itemAt(pos)
        if item is None:
            return

        # 仅在顶级目录项上展示“刷新文件夹 / 关闭文件夹”
        if item.parent() is not None:
            return

        menu = QMenu(self)
        refresh_action = menu.addAction("刷新文件夹")
        close_action = menu.addAction("关闭文件夹")
        action = menu.exec_(self.tree_widget.viewport().mapToGlobal(pos))
        if action == refresh_action:
            self._refresh_folder_tree()
        elif action == close_action:
            self._close_current_folder()

    def _path_is_under_root(self, file_path: str, root_dir: str) -> bool:
        """判断 file_path 是否位于 root_dir 目录之下（含根目录内的直接文件）。"""
        try:
            root_abs = os.path.abspath(root_dir)
            file_abs = os.path.abspath(file_path)
            return os.path.commonpath([root_abs, file_abs]) == root_abs
        except (ValueError, OSError):
            return False

    def _refresh_folder_tree(self):
        """重建目录树；若当前显示的文件仍在目录内则重新加载，否则清空图像区。"""
        if not self.root_dir:
            return
        if not os.path.isdir(self.root_dir):
            self.statusBar().showMessage("无法刷新：根目录不存在或无法访问")
            return
        current = self.current_file
        self._build_tree(self.root_dir)
        if not current:
            self.image_label.clear_pick()
            self._update_status_footer()
            self.statusBar().showMessage("已刷新文件夹")
            return
        if not os.path.isfile(current) or not self._path_is_under_root(current, self.root_dir):
            self.current_file = ""
            self.current_file_md5 = ""
            self.base_pixmap = None
            self._display_image = None
            self.image_label.clear_pick()
            self.image_label.set_source_size(0, 0)
            self.image_label.setMinimumSize(400, 300)
            self.current_display_format = "-"
            self.image_label.clear()
            self.image_label.setText(IMAGE_HINT_INITIAL)
            self._update_status_footer()
            self.statusBar().showMessage("已刷新文件夹：当前文件已不在该目录或已被删除")
            return
        self._select_path_in_tree(current)
        self.load_and_display_file(current)
        self.statusBar().showMessage("已刷新文件夹")

    def _close_current_folder(self):
        self.tree_widget.clear()
        self.root_dir = ""
        self.current_file = ""
        self.current_file_md5 = ""
        self.base_pixmap = None
        self._display_image = None
        self.image_label.clear_pick()
        self.image_label.set_source_size(0, 0)
        self.image_label.setMinimumSize(400, 300)
        self.current_display_format = "-"
        self.zoom_factor = 1.0
        self.image_label.clear()
        self.image_label.setText(IMAGE_HINT_INITIAL)
        self._update_status_footer()
        self.statusBar().showMessage("已关闭文件夹")

    def _handle_dropped_file(self, file_path: str):
        if not file_path:
            return
        if not os.path.exists(file_path):
            show_themed_message(self, QMessageBox.Warning, "拖拽失败", "文件不存在。")
            return
        if os.path.isdir(file_path):
            show_themed_message(self, QMessageBox.Warning, "拖拽失败", "请拖拽文件到图像框，文件夹请使用“打开文件夹”。")
            return
        self._open_file_in_context(file_path)
        self.statusBar().showMessage(f"已拖拽打开: {file_path}")

    def _open_file_in_context(self, file_path: str):
        self.root_dir = os.path.dirname(file_path)
        self._build_tree(self.root_dir)
        self._select_path_in_tree(file_path)
        self.load_and_display_file(file_path)

    def _get_selected_display_format(self) -> str:
        return self.selected_display_format

    def _is_common_image_file(self, file_path: str) -> bool:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in COMMON_IMAGE_EXTS

    def on_display_format_changed(self):
        if not self.current_file:
            return
        if self._is_common_image_file(self.current_file):
            return
        self.load_and_display_file(self.current_file)

    def _set_display_format(self, fmt: str):
        self.selected_display_format = fmt
        self.on_display_format_changed()

    def load_and_display_file(self, file_path: str):
        try:
            if self._is_common_image_file(file_path):
                image = QImage(file_path)
                if image.isNull():
                    raise ValueError("无法解析该图片文件。")
                image = image.copy()
                self.current_display_format = "普通图片"
            else:
                fmt = self._get_selected_display_format() or _infer_format(file_path)
                if not fmt:
                    raise ValueError("无法识别 raw 格式，请在“显示格式”中手动选择。")
                width, height = _infer_resolution_from_name(file_path)
                if not width or not height:
                    resolution, ok = self._ask_resolution()
                    if not ok:
                        return
                    width, height = resolution
                rgb = _decode_raw_to_rgb(file_path, fmt, width, height)
                image = QImage(
                    rgb.data,
                    width,
                    height,
                    width * 3,
                    QImage.Format_RGB888,
                ).copy()
                self.current_display_format = fmt

            self.image_label.setMinimumSize(0, 0)
            self.image_label.clear_pick()
            self._display_image = image
            self.image_label.set_source_size(image.width(), image.height())
            self.base_pixmap = QPixmap.fromImage(image)
            self.enable_fit_to_window()
            self.current_file = file_path
            self.current_file_md5 = _file_md5_hex(file_path)
            self._update_status_footer()
            self.statusBar().showMessage(f"已打开: {file_path}")
        except Exception as e:
            show_themed_message(self, QMessageBox.Critical, "打开失败", str(e))
            self.statusBar().showMessage("打开失败")

    def _ask_resolution(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("输入分辨率")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("未从文件名识别分辨率，请输入宽高（例如 1920x1080）"))
        line = QLineEdit()
        line.setPlaceholderText("宽x高")
        layout.addWidget(line)
        row = QHBoxLayout()
        ok_btn = QPushButton("确定")
        cancel_btn = QPushButton("取消")
        row.addStretch()
        row.addWidget(cancel_btn)
        row.addWidget(ok_btn)
        layout.addLayout(row)

        result = {"ok": False, "value": (0, 0)}

        def on_ok():
            w, h, err = parse_resolution(line.text().strip())
            if err:
                show_themed_message(dialog, QMessageBox.Warning, "输入错误", err)
                return
            result["ok"] = True
            result["value"] = (w, h)
            dialog.accept()

        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(dialog.reject)
        dialog.exec_()
        return result["value"], result["ok"]

    def open_converter_dialog(self):
        dlg = FileConverterDialog(self)
        dlg.exec_()

    def open_usage_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("使用说明")
        if os.path.exists(APP_ICON_PATH):
            dlg.setWindowIcon(QIcon(APP_ICON_PATH))
        dlg.setMinimumSize(800, 620)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        content = QTextEdit()
        content.setReadOnly(True)
        content.setPlainText(
            "图像显示与格式处理工具 — 使用说明\n"
            "================================================================\n\n"
            "【界面布局】\n"
            "  左侧为目录树，右侧为图像显示区；底部状态栏显示文件、格式、缩放及选点信息。\n"
            "  启动后图像区提示：通过菜单打开文件/文件夹，或将文件拖拽到图像区。\n\n"
            "1. 文件\n"
            "   · 打开文件：选择单个图片或 raw 数据文件；自动以该文件所在目录重建左侧目录树并定位。\n"
            "   · 打开文件夹：将所选目录作为目录树根，点击子项即可在右侧显示。\n"
            "   · 打开对话框中的图片类型：png、jpg、jpeg、bmp、webp；另支持全部已列出的 raw 扩展名。\n"
            "   · 在目录树中点击 gif 等常见图片也可显示（与打开对话框筛选列表可能略有不同）。\n\n"
            "2. 目录树（顶级目录项右键）\n"
            "   · 刷新文件夹：重新扫描磁盘，更新树中文件列表。\n"
            "     — 若当前显示的文件仍在目录内：重新加载该文件。\n"
            "     — 若文件已删除或不在该目录下：清空右侧图像，恢复初始提示文案。\n"
            "   · 关闭文件夹：清空目录树与显示，回到未打开目录状态。\n\n"
            "3. 图像显示与交互\n"
            "   · 普通图片：由 Qt 直接解码显示，格式记为「普通图片」。\n"
            "   · Raw 数据：按所选或自动识别的格式解码为 RGB 预览（YUV 类经 BT.601 full range）。\n"
            "   · 支持格式：rgbpack、rgbplanar、argb4444、argb1555、nv12、nv21、nv16、nv61、\n"
            "     yuv422yuyv、yuv422yvyu、yuv422vyuy、yuv422uyvy、yuv444p、yuv422p、yuv420p、yonly。\n"
            "   · argb4444 / argb1555：每像素 16 位小端；4444 为 A4R4G4B4，1555 为 A1R5G5B5。\n"
            "   · 拖拽：将文件拖到右侧图像区即可打开（不支持拖入文件夹）。\n"
            "   · 大图出现滚动条；Shift+左键拖动可平移视图（小手光标，不选点）。\n"
            "   · 图像在视口内居中；像素坐标始终以图像左上角为 (0,0)，与滚动、居中无关。\n"
            "   · 小图加载时显示区域与图像同尺寸，避免留白导致取点坐标偏移。\n\n"
            "4. 图像格式（raw 解码）\n"
            "   · 「自动识别」（默认）：从文件名推断格式；推断失败时需手动选择后重新打开。\n"
            "   · 也可在菜单中固定为某一种 raw 格式；对 raw 文件切换后会按新格式重新解码显示。\n"
            "   · 分辨率：优先取文件名中最后一组「宽x高」（支持 x / X / ×，如 512x256_rgb.bin → 512×256）。\n"
            "     无法识别时弹出对话框，可输入 1920x1080 等形式（也支持 1920 x 1080）。\n"
            "   · 自动识别格式示例：\n"
            "     — 扩展名为格式名（如 .nv12、.argb4444）或 .rgb → rgbpack\n"
            "     — 文件名含独立词 rgb888 / rgb → rgbpack；rgbp / rgbplanar → rgbplanar\n"
            "     — yuv444 / yuv422 / yuv420、gray、argb444 / argb155 等别名\n"
            "     — 注意：仅含 rgb 词（如 512x256_rgb.bin）识别为 rgbpack，不含 rgbp 时不当作 planar\n"
            "     — srgb 等内嵌 rgb 字样不会误识别为 rgbpack\n"
            "   · 对普通图片切换「图像格式」菜单无效（始终按图片解码）。\n\n"
            "5. 查看（缩放与平滑）\n"
            "   · 放大 Ctrl++　缩小 Ctrl+-　100% Ctrl+0　适应窗口 Ctrl+9\n"
            "   · Ctrl+鼠标滚轮：以光标在视图内的位置为中心缩放（光标在视图外则用视口中心）。\n"
            "   · 图像平滑：关（默认）= 最近邻，放大后像素边界清晰；开 = 双线性平滑。切换后重绘当前图。\n"
            "   · 「适应窗口」会按窗口大小自动缩放并居中。\n\n"
            "6. 处理 → 转为格式\n"
            "   · 将常规图片转换为 raw 二进制文件（输入：png / jpg / jpeg / bmp / webp）。\n"
            "   · 输出格式与上文 raw 列表一致；输出文件名：输入名_宽x高.格式。\n"
            "   · 分辨率：下拉可选 64x64、512x512、1280x720、1920x1080、3840x2160、4096x2160，\n"
            "     也可手动编辑为任意「宽x高」；宽高须为正整数。\n"
            "   · yuv420p、nv12/nv21、nv16/nv61、yuv422 打包类等要求宽、高均为偶数。\n"
            "   · 输出目录可自选，不存在时自动创建。\n"
            "   · 选择 argb4444 或 argb1555 时，对话框会出现 Alpha（0–255）：\n"
            "     — 0 全透明，255 全不透明（整幅图统一 Alpha，非逐像素）\n"
            "     — 4444：Alpha 量化为 4 位写入高 nibble\n"
            "     — 1555：Alpha≥128 记为不透明位 1，否则为 0\n"
            "   · 转换在后台线程执行，期间可禁用相关按钮；完成后弹窗提示。\n\n"
            "7. 界面显示\n"
            "   · 深色界面 / 浅色界面：切换整体配色（含对话框标题栏主题）。\n\n"
            "8. 使用说明\n"
            "   · 本菜单 →「查看使用说明」打开本文档。\n\n"
            "9. 底部状态栏与取点\n"
            "   · 常驻：文件路径（\\ 显示为 /）| 当前文件 MD5 | 显示格式 | 缩放比例。\n"
            "   · 左键点击图像像素：追加坐标 (x,y) 及该点数值；未点击不显示坐标/数值。\n"
            "   · 选中像素以青绿色方框标出；右键或 Esc 取消选点。\n"
            "   · 数值规则：\n"
            "     — 普通图片、rgbpack、rgbplanar：RGB(r,g,b)\n"
            "     — argb4444 / argb1555：十六进制字与分量（由预览 RGB 反推量化值）\n"
            "     — yonly：Y=\n"
            "     — 其余 YUV 类 raw：由预览 RGB 按 BT.601 full range 换算 YUV(y,u,v)\n"
        )
        layout.addWidget(content)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        apply_titlebar_theme(dlg, dark=(ACTIVE_THEME == "dark"))
        dlg.exec_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit_to_window and self.base_pixmap is not None:
            self._apply_fit_zoom()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._titlebar_theme_applied:
            apply_titlebar_theme(self, dark=(ACTIVE_THEME == "dark"))
            self._titlebar_theme_applied = True

    def _render_pixmap(self):
        if self.base_pixmap is None:
            return
        base_w = self.base_pixmap.width()
        base_h = self.base_pixmap.height()
        target_w = max(1, int(base_w * self.zoom_factor))
        target_h = max(1, int(base_h * self.zoom_factor))
        scale_mode = Qt.SmoothTransformation if self.image_smooth_scaling else Qt.FastTransformation
        scaled = self.base_pixmap.scaled(
            target_w,
            target_h,
            Qt.KeepAspectRatio,
            scale_mode,
        )
        self.image_label.setPixmap(scaled)
        self.image_label.resize(scaled.size())
        self._update_status_footer()
        if self.fit_to_window:
            self._center_scroll_if_oversized()

    def _center_scroll_if_oversized(self):
        """适应窗口模式下：图像大于视口时把滚动条置于中间，使图像在视口居中（坐标仍相对图像左上角）。"""
        if self.base_pixmap is None:
            return
        vp = self.scroll_area.viewport()
        vw, vh = vp.width(), vp.height()
        if vw < 2 or vh < 2:
            return
        lw, lh = self.image_label.width(), self.image_label.height()
        hbar = self.scroll_area.horizontalScrollBar()
        vbar = self.scroll_area.verticalScrollBar()
        if lw > vw:
            hbar.setValue(max(hbar.minimum(), min(hbar.maximum(), (lw - vw) // 2)))
        else:
            hbar.setValue(hbar.minimum())
        if lh > vh:
            vbar.setValue(max(vbar.minimum(), min(vbar.maximum(), (lh - vh) // 2)))
        else:
            vbar.setValue(vbar.minimum())

    def _apply_fit_zoom(self):
        if self.base_pixmap is None:
            return
        viewport = self.scroll_area.viewport().size()
        if viewport.width() <= 2 or viewport.height() <= 2:
            return
        w_ratio = viewport.width() / self.base_pixmap.width()
        h_ratio = viewport.height() / self.base_pixmap.height()
        self.zoom_factor = max(self.min_zoom, min(self.max_zoom, min(w_ratio, h_ratio)))
        self._render_pixmap()

    def enable_fit_to_window(self):
        if self.base_pixmap is None:
            return
        self.fit_to_window = True
        self._apply_fit_zoom()

    def reset_zoom(self):
        if self.base_pixmap is None:
            return
        self.fit_to_window = False
        self.zoom_factor = 1.0
        self._render_pixmap()

    def _zoom_anchor_viewport_pos(self) -> QPoint:
        """菜单/快捷键缩放时：光标在视口内则用光标位置，否则用视口中心。"""
        vp = self.scroll_area.viewport()
        lp = vp.mapFromGlobal(QCursor.pos())
        if vp.rect().contains(lp):
            return lp
        return vp.rect().center()

    def _on_smooth_scale_action(self, action):
        smooth = action is self.smooth_on_action
        if self.image_smooth_scaling == smooth:
            return
        self.image_smooth_scaling = smooth
        if self.base_pixmap is not None:
            self._render_pixmap()
            if self.fit_to_window:
                self._center_scroll_if_oversized()

    def zoom_by(self, factor: float, anchor_viewport: QPoint = None):
        """以 anchor_viewport（视口坐标）为锚点缩放；未指定时取光标或视口中心。"""
        if self.base_pixmap is None:
            return
        vp = self.scroll_area.viewport()
        if anchor_viewport is None:
            anchor_viewport = self._zoom_anchor_viewport_pos()

        old_z = self.zoom_factor
        self.fit_to_window = False
        new_z = max(self.min_zoom, min(self.max_zoom, old_z * factor))
        if abs(new_z - old_z) < 1e-9:
            return

        pos_label = self.image_label.mapFrom(vp, anchor_viewport)
        ow = self.base_pixmap.width()
        oh = self.base_pixmap.height()
        t = self.image_label.label_to_image_float(float(pos_label.x()), float(pos_label.y()))

        self.zoom_factor = new_z
        self._render_pixmap()

        hbar = self.scroll_area.horizontalScrollBar()
        vbar = self.scroll_area.verticalScrollBar()
        if t is None:
            return
        ix, iy = t
        r = self.image_label.pixmap_rect_in_label()
        if r is None:
            return
        new_off_x, new_off_y, new_pw, new_ph = r
        new_px = ix * new_pw / ow
        new_py = iy * new_ph / oh
        new_lx = new_off_x + new_px
        new_ly = new_off_y + new_py

        hbar.setValue(int(round(new_lx - anchor_viewport.x())))
        vbar.setValue(int(round(new_ly - anchor_viewport.y())))
        hbar.setValue(max(hbar.minimum(), min(hbar.maximum(), hbar.value())))
        vbar.setValue(max(vbar.minimum(), min(vbar.maximum(), vbar.value())))

    def _on_image_pixel_picked(self, _ix: int, _iy: int):
        self._update_status_footer()

    def _clear_pixel_pick_shortcut(self):
        if self.image_label.pick_image_xy() is not None:
            self.image_label.clear_pick()
            self._update_status_footer()

    def _update_status_footer(self):
        if self.current_file:
            file_text = _path_for_status(self.current_file)
        elif self.root_dir:
            file_text = _path_for_status(self.root_dir)
        else:
            file_text = "-"
        md5_text = self.current_file_md5 if self.current_file_md5 else "-"
        base = (
            f"文件: {file_text} | MD5: {md5_text} | 格式: {self.current_display_format} "
            f"| 缩放: {self.zoom_factor * 100:.1f}%"
        )
        hover = ""
        picked = self.image_label.pick_image_xy()
        if picked is not None and self._display_image is not None and not self._display_image.isNull():
            ix, iy = picked
            c = QColor(self._display_image.pixel(ix, iy))
            r, g, b = c.red(), c.green(), c.blue()
            hover = f" | 坐标: ({ix}, {iy}) | {_format_pixel_value_for_status(self.current_display_format, r, g, b)}"
        self.status_summary_label.setText(base + hover)

    def _set_theme(self, theme: str):
        global ACTIVE_THEME
        ACTIVE_THEME = theme
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(APP_DARK_QSS if theme == "dark" else APP_LIGHT_QSS)
            app.processEvents()
        # 立即应用 + 延迟重试，覆盖不同系统的句柄刷新时机
        apply_titlebar_theme(self, dark=(theme == "dark"))
        QTimer.singleShot(0, lambda: apply_titlebar_theme(self, dark=(theme == "dark")))
        QTimer.singleShot(120, lambda: apply_titlebar_theme(self, dark=(theme == "dark")))
        self._titlebar_theme_applied = True
        self.theme_dark_action.setChecked(theme == "dark")
        self.theme_light_action.setChecked(theme == "light")

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_DARK_QSS if ACTIVE_THEME == "dark" else APP_LIGHT_QSS)
    if os.path.exists(APP_ICON_PATH):
        app.setWindowIcon(QIcon(APP_ICON_PATH))
    window = ImageViewerMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()