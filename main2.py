import sys
import psutil
import platform
import collections
import time
import subprocess
import socket
import GPUtil
import cpuinfo
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QGridLayout, QSizePolicy, QScrollArea, QListWidget, QListWidgetItem,
    QStackedWidget, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, QPropertyAnimation, QTimer, pyqtSignal, QEvent, QParallelAnimationGroup

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import FuncFormatter
import qdarkstyle

BG_COLOR_DARK = "#1A202C"
BG_COLOR_MEDIUM = "#2D3748"
BG_COLOR_LIGHT = "#4A5568"
ACCENT_COLOR_BLUE = "#4299E1"
NOT_ACCENT_COLOR_BLUE = "#28445C"
ACCENT_COLOR_GREEN = "#48BB78"
ACCENT_COLOR_ORANGE = "#ED8936"
ACCENT_COLOR_RED = "#E53E3E"
TEXT_COLOR_LIGHT = "#E2E8F0"
TEXT_COLOR_MUTED = "#B3CACC"
TABLE_BORDER_COLOR= "#172D3F"


TABLE_CELL_STYLE = f"""
    QLabel {{
        background-color: {BG_COLOR_DARK};
        border: 1.5px solid {TABLE_BORDER_COLOR};
        border-radius: 0px;
        padding: 3px;
        min-width: 80px;
        min-height: 30px;
    }}
"""

TABLE_HEADER_STYLE = f"""
    QLabel {{
        background-color: {BG_COLOR_LIGHT};
        border: 1.5px solid {TABLE_BORDER_COLOR};
        border-radius: 0px;
        font-weight: bold;
        padding: 3px;
        min-width: 80px;
        min-height: 30px;
    }}
"""

def create_styled_back_button(slot_function):
    button = QPushButton("← Volver al Dashboard")
    button.setStyleSheet(f"""
        QPushButton {{
            background-color: {BG_COLOR_LIGHT};
            border: none;
            color: {TEXT_COLOR_LIGHT};
            padding: 10px 15px;
            text-align: center;
            font-size: 14px;
            border-radius: 5px;
        }}
        QPushButton:hover {{
            background-color: {ACCENT_COLOR_BLUE};
        }}
    """)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.clicked.connect(slot_function)
    return button

class LiveGraphWidget(QWidget):
    clicked = pyqtSignal()

    def __init__(self, title, y_label, maxlen=60, parent=None, shadow=True):
        super().__init__(parent)
        self.title = title
        self.y_label = y_label
        self.history = collections.deque(maxlen=maxlen)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)


        self.figure, self.ax = plt.subplots(facecolor=BG_COLOR_MEDIUM, figsize=(8, 5))
        self.canvas = FigureCanvas(self.figure)
        self.layout().addWidget(self.canvas)

        self.figure.subplots_adjust(bottom=0.19)

        self.canvas.installEventFilter(self)

        self.ax.set_title(self.title, color=TEXT_COLOR_LIGHT, fontsize=10)
        self.ax.set_facecolor(BG_COLOR_DARK)
        self.ax.tick_params(axis='x', colors=TEXT_COLOR_MUTED, labelsize=8)
        self.ax.tick_params(axis='y', colors=TEXT_COLOR_MUTED, labelsize=8)

        self.ax.spines['left'].set_color(TEXT_COLOR_MUTED)
        self.ax.spines['bottom'].set_color(TEXT_COLOR_MUTED)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['top'].set_visible(False)

        self.ax.grid(True, linestyle=':', alpha=0.5, color=TEXT_COLOR_MUTED)
        self.ax.set_ylabel(self.y_label, color=TEXT_COLOR_MUTED, fontsize=8)
        self.ax.set_xlabel("Tiempo (s)", color=TEXT_COLOR_MUTED, fontsize=10)

        self.line1, = self.ax.plot([], [], color=ACCENT_COLOR_GREEN)
        self.line2 = None
        self.fill_area = self.ax.fill_between([], [], [], color=ACCENT_COLOR_GREEN, alpha=0.2)

        if '%' in self.y_label:
            self.ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{int(y)}%'))

        if shadow:
            self.shadow = QGraphicsDropShadowEffect(self)
            self.shadow.setBlurRadius(0)
            self.shadow.setOffset(0, 0)
            self.shadow.setColor(QColor(0, 0, 0, 0))
            self.setGraphicsEffect(self.shadow)

            self.color_animation_enter = QPropertyAnimation(self.shadow, b"color")
            self.color_animation_enter.setStartValue(QColor(0, 0, 0, 0))
            self.color_animation_enter.setEndValue(QColor(ACCENT_COLOR_BLUE).lighter(100))
            self.color_animation_enter.setDuration(200)

            self.color_animation_leave = QPropertyAnimation(self.shadow, b"color")
            self.color_animation_leave.setStartValue(QColor(ACCENT_COLOR_BLUE).lighter(100))
            self.color_animation_leave.setEndValue(QColor(0, 0, 0, 0))
            self.color_animation_leave.setDuration(200)

            self.blur_animation_enter = QPropertyAnimation(self.shadow, b"blurRadius")
            self.blur_animation_enter.setStartValue(0)
            self.blur_animation_enter.setEndValue(15)
            self.blur_animation_enter.setDuration(200)

            self.blur_animation_leave = QPropertyAnimation(self.shadow, b"blurRadius")
            self.blur_animation_leave.setStartValue(15)
            self.blur_animation_leave.setEndValue(0)
            self.blur_animation_leave.setDuration(200)

            self.hover_group = QParallelAnimationGroup()
            self.hover_group.addAnimation(self.color_animation_enter)
            self.hover_group.addAnimation(self.blur_animation_enter)

            self.leave_group = QParallelAnimationGroup()
            self.leave_group.addAnimation(self.color_animation_leave)
            self.leave_group.addAnimation(self.blur_animation_leave)
        else:
            self.shadow = None
            self.hover_group = None
            self.leave_group = None

    def update_data(self, value):
        self.history.append(value)
        self.ax.clear()
        self.ax.set_title(self.title, color=TEXT_COLOR_LIGHT, fontsize=10)
        self.ax.set_facecolor(BG_COLOR_DARK)
        self.ax.tick_params(axis='x', colors=TEXT_COLOR_MUTED, labelsize=8)
        self.ax.tick_params(axis='y', colors=TEXT_COLOR_MUTED, labelsize=8)
        self.ax.spines['left'].set_color(TEXT_COLOR_MUTED)
        self.ax.spines['bottom'].set_color(TEXT_COLOR_MUTED)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['top'].set_visible(False)

        self.ax.grid(True, linestyle=':', alpha=0.5, color=TEXT_COLOR_MUTED)
        self.ax.set_ylabel(self.y_label, color=TEXT_COLOR_MUTED, fontsize=8)
        self.ax.set_xlabel("Tiempo (s)", color=TEXT_COLOR_MUTED, fontsize=10)

        if '%' in self.y_label:
            self.ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{int(y)}%'))

        x_data = list(range(len(self.history)))

        multi_line_titles = {"Uso de Red", "Velocidad del Disco", "Velocidad del Disco", "Uso de Red"}

        if self.title.strip() in multi_line_titles:
            if self.title.strip() == "Uso de Red" or self.title.strip() == "Uso de red":
                sent_bytes = [d[0] for d in self.history]
                recv_bytes = [d[1] for d in self.history]
                plot_label_1 = 'Enviado'
                plot_label_2 = 'Recibido'
                y_axis_label_prefix = "Datos"
            else:
                sent_bytes = [d[0] for d in self.history] # read_bytes
                recv_bytes = [d[1] for d in self.history] # write_bytes
                plot_label_1 = 'Lectura'
                plot_label_2 = 'Escritura'
                y_axis_label_prefix = "Velocidad"

            max_val = max(max(sent_bytes) if sent_bytes else 0, max(recv_bytes) if recv_bytes else 0)
            unit = "Bytes/s"
            if max_val > 1024 * 1024:
                sent_bytes = [b / (1024 * 1024) for b in sent_bytes]
                recv_bytes = [b / (1024 * 1024) for b in recv_bytes]
                unit = "MB/s"
            elif max_val > 1024:
                sent_bytes = [b / 1024 for b in sent_bytes]
                recv_bytes = [b / 1024 for b in recv_bytes]
                unit = "KB/s"

            self.ax.set_ylabel(f"{y_axis_label_prefix} ({unit})", color=TEXT_COLOR_MUTED, fontsize=8)

            self.ax.plot(x_data, sent_bytes, label=plot_label_1, color=ACCENT_COLOR_BLUE)
            self.ax.plot(x_data, recv_bytes, label=plot_label_2, color=ACCENT_COLOR_GREEN)
            self.ax.legend(loc='upper left', frameon=False, labelcolor=TEXT_COLOR_MUTED, fontsize=8)
            max_current_val = max(max(sent_bytes) if sent_bytes else 0, max(recv_bytes) if recv_bytes else 0)
            self.ax.set_ylim(0, max(0.1, max_current_val * 1.1))
        else:
            y_data = list(self.history)
            self.ax.plot(x_data, y_data, color=ACCENT_COLOR_GREEN)
            self.ax.fill_between(x_data, y_data, color=ACCENT_COLOR_GREEN, alpha=0.2)
            self.ax.set_ylabel(self.y_label, color=TEXT_COLOR_MUTED, fontsize=8)
            self.ax.set_ylim(0, 100)

        self.canvas.draw()
        self.canvas.flush_events()

    def eventFilter(self, obj, event):
        if obj == self.canvas and event.type() == QEvent.MouseButtonPress:
            self.clicked.emit()
            return False
        return super().eventFilter(obj, event)

    def enterEvent(self, event):
        if self.hover_group:
            self.leave_group.stop()
            self.hover_group.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.leave_group:
            self.hover_group.stop()
            self.leave_group.start()
        super().leaveEvent(event)


class CPUDetailWidget(QWidget):
    back_to_dashboard = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        back_button = create_styled_back_button(self.back_to_dashboard.emit)
        self.main_layout.addWidget(back_button, alignment=Qt.AlignLeft)

        self.cpu_detail_graph = LiveGraphWidget("Uso del CPU", "CPU (%)", maxlen=120, shadow=False)
        self.cpu_detail_graph.setMinimumHeight(250)
        self.main_layout.addWidget(self.cpu_detail_graph)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.scroll_content_widget = QWidget()
        self.info_h_layout = QHBoxLayout(self.scroll_content_widget)
        self.info_h_layout.setSpacing(0)
        self.info_h_layout.setContentsMargins(0, 0, 0, 0)

        self.dynamic_info_frame = QFrame()
        self.dynamic_info_frame.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-radius: 0px; padding: 10px;")
        self.dynamic_info_layout = QVBoxLayout(self.dynamic_info_frame)
        self.dynamic_info_layout.setContentsMargins(5, 5, 5, 5)
        self.dynamic_info_layout.setSpacing(2)

        dynamic_labels_grid = QGridLayout()
        dynamic_labels_grid.setContentsMargins(0, 0, 0, 0)
        dynamic_labels_grid.setSpacing(2)
        row = 0

        dynamic_labels_grid.addWidget(QLabel("Uso Total:"), row, 0)
        self.lbl_overall_usage = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_overall_usage, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Frecuencia Actual:"), row, 0)
        self.lbl_cpu_freq = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_cpu_freq, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Procesos:"), row, 0)
        self.lbl_processes = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_processes, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Hilos:"), row, 0)
        self.lbl_threads = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_threads, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Tiempo prendido:"), row, 0)
        self.lbl_uptime = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_uptime, row, 1)
        row += 1

        self.dynamic_info_layout.addLayout(dynamic_labels_grid)

        tables_container_h_layout = QHBoxLayout()
        tables_container_h_layout.setSpacing(20)

        temp_table_section_v_layout = QVBoxLayout()
        temp_table_section_v_layout.setContentsMargins(0, 0, 0, 0)
        temp_table_section_v_layout.setSpacing(5)

        lbl_temp_header = QLabel("<h3>Temperatura de los núcleos</h3>")
        lbl_temp_header.setAlignment(Qt.AlignCenter)
        temp_table_section_v_layout.addWidget(lbl_temp_header)

        self.temp_table_layout = QGridLayout()
        self.temp_table_layout.setContentsMargins(0, 0, 0, 0)
        self.temp_table_layout.setSpacing(0)

        lbl_temp_core_header = QLabel("<b>Núcleo</b>")
        lbl_temp_core_header.setStyleSheet(TABLE_HEADER_STYLE)
        lbl_temp_core_header.setAlignment(Qt.AlignCenter)
        self.temp_table_layout.addWidget(lbl_temp_core_header, 0, 0)

        lbl_temp_current_header = QLabel("<b>Actual (°C)</b>")
        lbl_temp_current_header.setStyleSheet(TABLE_HEADER_STYLE)
        lbl_temp_current_header.setAlignment(Qt.AlignCenter)
        self.temp_table_layout.addWidget(lbl_temp_current_header, 0, 1)

        temp_table_section_v_layout.addLayout(self.temp_table_layout)
        temp_table_section_v_layout.addStretch()
        tables_container_h_layout.addLayout(temp_table_section_v_layout)

        usage_table_section_v_layout = QVBoxLayout()
        usage_table_section_v_layout.setContentsMargins(0, 0, 0, 0)
        usage_table_section_v_layout.setSpacing(5)

        lbl_usage_header = QLabel("<h3>Uso por Núcleo</h3>")
        lbl_usage_header.setAlignment(Qt.AlignCenter)
        usage_table_section_v_layout.addWidget(lbl_usage_header)

        self.core_usage_table_layout = QGridLayout()
        self.core_usage_table_layout.setContentsMargins(0, 0, 0, 0)
        self.core_usage_table_layout.setSpacing(0)

        lbl_usage_core_header = QLabel("<b>Núcleo</b>")
        lbl_usage_core_header.setStyleSheet(TABLE_HEADER_STYLE)
        lbl_usage_core_header.setAlignment(Qt.AlignCenter)
        self.core_usage_table_layout.addWidget(lbl_usage_core_header, 0, 0)

        lbl_usage_percent_header = QLabel("<b>Uso (%)</b>")
        lbl_usage_percent_header.setStyleSheet(TABLE_HEADER_STYLE)
        lbl_usage_percent_header.setAlignment(Qt.AlignCenter)
        self.core_usage_table_layout.addWidget(lbl_usage_percent_header, 0, 1)

        usage_table_section_v_layout.addLayout(self.core_usage_table_layout)
        usage_table_section_v_layout.addStretch()
        tables_container_h_layout.addLayout(usage_table_section_v_layout)

        tables_container_h_layout.setStretch(0, 1)
        tables_container_h_layout.setStretch(1, 1)

        self.dynamic_info_layout.addLayout(tables_container_h_layout)

        self.dynamic_info_layout.addStretch()
        self.info_h_layout.addWidget(self.dynamic_info_frame)


        self.static_info_frame = QFrame()
        self.static_info_frame.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-radius: 0px; padding: 10px;")
        self.static_info_layout = QGridLayout(self.static_info_frame)
        self.static_info_layout.setContentsMargins(5, 5, 5, 5)
        self.static_info_layout.setSpacing(2)

        self.static_info_layout.addWidget(QLabel("<h2>Información del Hardware</h2>"), 0, 0, 1, 2)
        row = 1

        self.static_info_layout.addWidget(QLabel("Nombre del Procesador:"), row, 0)
        self.lbl_cpu_name = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_cpu_name, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("Núcleos (Físicos):"), row, 0)
        self.lbl_physical_cores = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_physical_cores, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("Hilos (Lógicos):"), row, 0)
        self.lbl_logical_cores = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_logical_cores, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("L1 cache:"), row, 0)
        self.lbl_l1_cache = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_l1_cache, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("L2 cache:"), row, 0)
        self.lbl_l2_cache = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_l2_cache, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("L3 cache:"), row, 0)
        self.lbl_l3_cache = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_l3_cache, row, 1)
        row += 1

        self.static_info_layout.setRowStretch(row, 1)

        self.info_h_layout.addWidget(self.static_info_frame)
        self.info_h_layout.setStretch(0, 2)
        self.info_h_layout.setStretch(1, 1)

        self.scroll_area.setWidget(self.scroll_content_widget)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addStretch()

        self.update_static_info()

    def update_static_info(self):
        if cpuinfo:
            info = cpuinfo.get_cpu_info()
            self.lbl_cpu_name.setText(info.get('brand_raw', 'N/A'))

            l1_data_cache_size = info.get('l1_data_cache_size')
            l1_instruction_cache_size = info.get('l1_instruction_cache_size')
            l2_cache_size = info.get('l2_cache_size')
            l3_cache_size = info.get('l3_cache_size')

            l1_total = 0
            if l1_data_cache_size:
                l1_total += l1_data_cache_size
            if l1_instruction_cache_size:
                l1_total += l1_instruction_cache_size

            if l1_total > 0:
                self.lbl_l1_cache.setText(f"{l1_total // 1024} KB")
            else:
                self.lbl_l1_cache.setText("N/A")

            self.lbl_l2_cache.setText(f"{l2_cache_size // 1024} KB" if l2_cache_size else "N/A")
            self.lbl_l3_cache.setText(f"{l3_cache_size // (1024*1024):.1f} MB" if l3_cache_size else "N/A")

        else:
            self.lbl_cpu_name.setText(platform.processor() + " (py-cpuinfo not found)")
            self.lbl_l1_cache.setText("N/A (py-cpuinfo not found)")
            self.lbl_l2_cache.setText("N/A (py-cpuinfo not found)")
            self.lbl_l3_cache.setText("N/A (py-cpuinfo not found)")


        self.lbl_physical_cores.setText(str(psutil.cpu_count(logical=False)))
        self.lbl_logical_cores.setText(str(psutil.cpu_count(logical=True)))

    def update_dynamic_info(self):
        overall_cpu_percent = psutil.cpu_percent(interval=None)
        self.lbl_overall_usage.setText(f"{overall_cpu_percent:.1f}%")
        self.cpu_detail_graph.update_data(overall_cpu_percent)

        cpu_freq = psutil.cpu_freq()
        if cpu_freq:
            self.lbl_cpu_freq.setText(f"{cpu_freq.current / 1000:.2f} GHz (Min: {cpu_freq.min / 1000:.2f} GHz, Max: {cpu_freq.max / 1000:.2f} GHz)")
        else:
            self.lbl_cpu_freq.setText("No disponible")

        self.lbl_processes.setText(str(len(psutil.pids())))
        total_threads = 0

        attrs_to_request = ['num_threads']

        for proc in psutil.process_iter(attrs_to_request):
            try:
                total_threads += proc.info.get('num_threads', 0)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        self.lbl_threads.setText(str(total_threads))

        boot_time_timestamp = psutil.boot_time()
        uptime_seconds = time.time() - boot_time_timestamp
        days = int(uptime_seconds // (24 * 3600))
        uptime_seconds %= (24 * 3600)
        hours = int(uptime_seconds // 3600)
        uptime_seconds %= 3600
        minutes = int(uptime_seconds // 60)
        seconds = int(uptime_seconds % 60)
        self.lbl_uptime.setText(f"{days}d {hours:02d}h {minutes:02d}m {seconds:02d}s")

        for i in reversed(range(1, self.temp_table_layout.rowCount())):
            for j in range(self.temp_table_layout.columnCount()):
                item = self.temp_table_layout.itemAtPosition(i, j)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                    self.temp_table_layout.removeItem(item)

        temps = psutil.sensors_temperatures()
        temp_row_idx = 1
        displayed_cores_count = 0
        max_cores_to_display = 4

        if temps:

            cpu_temps_found = False
            for sensor_name, entries in temps.items():
                if 'coretemp' in sensor_name.lower() or 'k10temp' in sensor_name.lower() or ('cpu' in sensor_name.lower() and 'package' not in (entry.label or '').lower()):
                    for i, entry in enumerate(entries):
                        if displayed_cores_count >= max_cores_to_display:
                            break

                        current_temp = entry.current

                        core_label = f"Core #{i}"
                        lbl_core = QLabel(core_label)
                        lbl_core.setAlignment(Qt.AlignCenter)
                        lbl_core.setStyleSheet(TABLE_CELL_STYLE)
                        self.temp_table_layout.addWidget(lbl_core, temp_row_idx, 0)

                        lbl_current_temp = QLabel(f"{current_temp:.1f}")
                        lbl_current_temp.setAlignment(Qt.AlignCenter)
                        lbl_current_temp.setStyleSheet(TABLE_CELL_STYLE)
                        self.temp_table_layout.addWidget(lbl_current_temp, temp_row_idx, 1)

                        temp_row_idx += 1
                        displayed_cores_count += 1
                        cpu_temps_found = True
                    if displayed_cores_count >= max_cores_to_display:
                        break

            if not cpu_temps_found:
                for sensor_name, entries in temps.items():
                    for i, entry in enumerate(entries):
                        if displayed_cores_count >= max_cores_to_display:
                            break
                        lbl_core = QLabel(entry.label or f"{sensor_name} {i}")
                        lbl_core.setAlignment(Qt.AlignCenter)
                        lbl_core.setStyleSheet(TABLE_CELL_STYLE)
                        self.temp_table_layout.addWidget(lbl_core, temp_row_idx, 0)

                        lbl_current_temp = QLabel(f"{entry.current:.1f}")
                        lbl_current_temp.setAlignment(Qt.AlignCenter)
                        lbl_current_temp.setStyleSheet(TABLE_CELL_STYLE)
                        self.temp_table_layout.addWidget(lbl_current_temp, temp_row_idx, 1)
                        temp_row_idx += 1
                        displayed_cores_count += 1
                    if displayed_cores_count >= max_cores_to_display:
                        break

            if displayed_cores_count == 0:
                no_temps_label = QLabel("No se detectaron temperaturas de núcleos específicos.")
                no_temps_label.setAlignment(Qt.AlignCenter)
                no_temps_label.setStyleSheet(TABLE_CELL_STYLE)
                self.temp_table_layout.addWidget(no_temps_label, temp_row_idx, 0, 1, 2)
                temp_row_idx += 1
        else:
            no_temps_label = QLabel("No disponible")
            no_temps_label.setAlignment(Qt.AlignCenter)
            no_temps_label.setStyleSheet(TABLE_CELL_STYLE)
            self.temp_table_layout.addWidget(no_temps_label, temp_row_idx, 0, 1, 2)
            temp_row_idx += 1

        for i in reversed(range(1, self.core_usage_table_layout.rowCount())):
            for j in range(self.core_usage_table_layout.columnCount()):
                item = self.core_usage_table_layout.itemAtPosition(i, j)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                    self.core_usage_table_layout.removeItem(item)

        per_cpu_percent = psutil.cpu_percent(interval=None, percpu=True)
        usage_row_idx = 1

        for i, usage in enumerate(per_cpu_percent):
            if i >= max_cores_to_display:
                break

            lbl_core_num = QLabel(f"Core #{i}")
            lbl_core_num.setAlignment(Qt.AlignCenter)
            lbl_core_num.setStyleSheet(TABLE_CELL_STYLE)
            self.core_usage_table_layout.addWidget(lbl_core_num, usage_row_idx, 0)

            lbl_usage_val = QLabel(f"{usage:.1f}%")
            lbl_usage_val.setAlignment(Qt.AlignCenter)
            lbl_usage_val.setStyleSheet(TABLE_CELL_STYLE)
            self.core_usage_table_layout.addWidget(lbl_usage_val, usage_row_idx, 1)
            usage_row_idx += 1

        if usage_row_idx == 1:
            no_usage_label = QLabel("No se detectó uso por núcleo.")
            no_usage_label.setAlignment(Qt.AlignCenter)
            no_usage_label.setStyleSheet(TABLE_CELL_STYLE)
            self.core_usage_table_layout.addWidget(no_usage_label, usage_row_idx, 0, 1, 2)


class RAMDetailedWidget(QWidget):
    back_to_dashboard = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        back_button = create_styled_back_button(self.back_to_dashboard.emit)
        self.main_layout.addWidget(back_button, alignment=Qt.AlignLeft)

        self.ram_detail_graph = LiveGraphWidget("Uso de RAM", "RAM (%)", maxlen=120, shadow=False)
        self.ram_detail_graph.setMinimumHeight(250)
        self.main_layout.addWidget(self.ram_detail_graph)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.scroll_content_widget = QWidget()
        self.info_h_layout = QHBoxLayout(self.scroll_content_widget)
        self.info_h_layout.setSpacing(20)
        self.info_h_layout.setContentsMargins(0, 0, 0, 0)

        # Dynamic RAM Information
        self.dynamic_info_frame = QFrame()
        self.dynamic_info_frame.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-radius: 0px; padding: 10px;")
        self.dynamic_info_layout = QVBoxLayout(self.dynamic_info_frame)
        self.dynamic_info_layout.setContentsMargins(5, 5, 5, 5)
        self.dynamic_info_layout.setSpacing(2)

        dynamic_labels_grid = QGridLayout()
        dynamic_labels_grid.setContentsMargins(0, 0, 0, 0)
        dynamic_labels_grid.setSpacing(2)
        row = 0

        dynamic_labels_grid.addWidget(QLabel("Uso Total:"), row, 0)
        self.lbl_overall_usage = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_overall_usage, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("En uso:"), row, 0)
        self.lbl_ram_used = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_ram_used, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Disponible:"), row, 0)
        self.lbl_ram_available = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_ram_available, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Porcentaje de uso:"), row, 0)
        self.lbl_ram_percent = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_ram_percent, row, 1)
        row += 1

        self.dynamic_info_layout.addLayout(dynamic_labels_grid)
        self.dynamic_info_layout.addStretch()
        self.info_h_layout.addWidget(self.dynamic_info_frame)

        # Static RAM Information
        self.static_info_frame = QFrame()
        self.static_info_frame.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-radius: 0px; padding: 10px;")
        self.static_info_layout = QGridLayout(self.static_info_frame)
        self.static_info_layout.setContentsMargins(5, 5, 5, 5)
        self.static_info_layout.setSpacing(2)

        self.static_info_layout.addWidget(QLabel("<h2>Información de la RAM</h2>"), 0, 0, 1, 2)
        row = 1

        self.static_info_layout.addWidget(QLabel("Tipo:"), row, 0)
        self.lbl_ram_type = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_ram_type, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("Velocidad:"), row, 0)
        self.lbl_ram_speed = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_ram_speed, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("Cantidad de Slots:"), row, 0)
        self.lbl_total_ram_slots = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_total_ram_slots, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("Slots Ocupados:"), row, 0)
        self.lbl_used_ram_slots = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_used_ram_slots, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("Módulos de Memoria:"), row, 0)
        self.lbl_memory_modules = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_memory_modules, row, 1)
        row += 1

        self.static_info_layout.setRowStretch(row, 1)
        self.info_h_layout.addWidget(self.static_info_frame)

        self.info_h_layout.setStretch(0, 1)
        self.info_h_layout.setStretch(1, 1)

        self.scroll_area.setWidget(self.scroll_content_widget)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addStretch()

        self.update_static_info()

    def _get_ram_slot_info(self):
        ram_info = {
            "total_slots": "N/A",
            "used_slots": 0,
            "modules": []
        }
        if platform.system() != "Linux":
            return ram_info

        try:
            result_type16 = subprocess.run(['sudo', 'dmidecode', '-t', '16'], capture_output=True, text=True, check=True)
            for line in result_type16.stdout.splitlines():
                if "Number Of Devices:" in line:
                    ram_info["total_slots"] = line.split(":")[1].strip()
                    break

            result_type17 = subprocess.run(['sudo', 'dmidecode', '-t', '17'], capture_output=True, text=True, check=True)
            current_module = {}
            for line in result_type17.stdout.splitlines():
                if "Memory Device" in line:
                    if current_module:
                        ram_info["modules"].append(current_module)
                    current_module = {}
                elif ":" in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key == "Locator":
                        current_module["slot"] = value
                    elif key == "Size" and value != "No Module Installed":
                        current_module["size"] = value
                        ram_info["used_slots"] += 1
            if current_module:
                ram_info["modules"].append(current_module)

        except subprocess.CalledProcessError as e:
            print(f"Error running dmidecode: {e}")
            print(f"Stderr: {e.stderr}")
            ram_info["total_slots"] = "Error (dmidecode)"
            ram_info["used_slots"] = "Error (dmidecode)"
            ram_info["modules"] = [{"slot": "Error", "size": "Error"}]
        except FileNotFoundError:
            ram_info["total_slots"] = "N/A (dmidecode not found)"
            ram_info["used_slots"] = "N/A (dmidecode not found)"
            ram_info["modules"] = [{"slot": "N/A", "size": "N/A"}]

        return ram_info

    def update_static_info(self):
        if platform.system() == "Linux":
            try:
                result_memory = subprocess.run(['sudo', 'dmidecode', '-t', 'memory'], capture_output=True, text=True, check=True)
                output_memory = result_memory.stdout

                ram_type = "N/A"
                ram_speed = "N/A"

                for line in output_memory.splitlines():
                    line = line.strip()
                    if "Type:" in line and "Unknown" not in line:
                        ram_type = line.split("Type:")[1].strip()
                        if " (unknown)" in ram_type:
                            ram_type = ram_type.replace(" (unknown)", "")
                    elif "Speed:" in line:
                        ram_speed = line.split("Speed:")[1].strip()
                        if "MHz" in ram_speed:
                            ram_speed = ram_speed
                        elif "MT/s" in ram_speed:
                            ram_speed = ram_speed.replace("MT/s", "MHz")
                    elif "Configured Clock Speed:" in line:
                        ram_speed = line.split("Configured Clock Speed:")[1].strip()
                        if "MHz" in ram_speed:
                            ram_speed = ram_speed
                        elif "MT/s" in ram_speed:
                            ram_speed = ram_speed.replace("MT/s", "MHz")
                self.lbl_ram_type.setText(ram_type)
                self.lbl_ram_speed.setText(ram_speed)

                ram_data = self._get_ram_slot_info()
                self.lbl_total_ram_slots.setText(str(ram_data["total_slots"]))
                self.lbl_used_ram_slots.setText(str(ram_data["used_slots"]))

                modules_text = ""
                if ram_data["modules"]:
                    for module in ram_data["modules"]:
                        slot = module.get("slot", "Desconocido")
                        size = module.get("size", "Desconocido")
                        if size != "No Module Installed":
                            modules_text += f"{slot}: {size}<br>"
                    if not modules_text:
                        modules_text = "No hay módulos de RAM instalados o detectables."
                else:
                    modules_text = "No se pudo obtener información de los módulos de RAM."
                self.lbl_memory_modules.setText(modules_text)

            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                self.lbl_ram_type.setText("N/A (Error)")
                self.lbl_ram_speed.setText("N/A (Error)")
                self.lbl_total_ram_slots.setText("N/A (Error)")
                self.lbl_used_ram_slots.setText("N/A (Error)")
                self.lbl_memory_modules.setText("N/A (Error)")
                print(f"Error executing dmidecode in update_static_info: {e}")
            except Exception as e:
                self.lbl_ram_type.setText("N/A (Error)")
                self.lbl_ram_speed.setText("N/A (Error)")
                self.lbl_total_ram_slots.setText("N/A (Error)")
                self.lbl_used_ram_slots.setText("N/A (Error)")
                self.lbl_memory_modules.setText("N/A (Error)")
                print(f"Unexpected error getting RAM info in update_static_info: {e}")
        else:
            self.lbl_ram_type.setText("N/A (Linux only)")
            self.lbl_ram_speed.setText("N/A (Linux only)")
            self.lbl_total_ram_slots.setText("N/A (Linux only)")
            self.lbl_used_ram_slots.setText("N/A (Linux only)")
            self.lbl_memory_modules.setText("N/A (Linux only)")


    def update_dynamic_info(self):
        ram_info = psutil.virtual_memory()

        total_gb = ram_info.total / (1024**3)
        used_gb = ram_info.used / (1024**3)
        available_gb = ram_info.available / (1024**3)
        percent_usage = ram_info.percent

        self.lbl_overall_usage.setText(f"{total_gb:.2f} GB")
        self.lbl_ram_used.setText(f"{used_gb:.2f} GB")
        self.lbl_ram_available.setText(f"{available_gb:.2f} GB")
        self.lbl_ram_percent.setText(f"{percent_usage:.1f}%")

        self.ram_detail_graph.update_data(percent_usage)


class DiskDetailWidget(QWidget):
    back_to_dashboard = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        back_button = create_styled_back_button(self.back_to_dashboard.emit)
        self.main_layout.addWidget(back_button, alignment=Qt.AlignLeft)

        self.disk_io_graph = LiveGraphWidget("Velocidad del Disco", "Velocidad (Bytes/s)", maxlen=120, shadow=False)
        self.disk_io_graph.setMinimumHeight(250)
        self.main_layout.addWidget(self.disk_io_graph)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.scroll_content_widget = QWidget()
        self.info_h_layout = QHBoxLayout(self.scroll_content_widget)
        self.info_h_layout.setSpacing(20)
        self.info_h_layout.setContentsMargins(0, 0, 0, 0)

        # Dynamic Disk Information
        self.dynamic_info_frame = QFrame()
        self.dynamic_info_frame.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-radius: 0px; padding: 10px;")
        self.dynamic_info_layout = QVBoxLayout(self.dynamic_info_frame)
        self.dynamic_info_layout.setContentsMargins(5, 5, 5, 5)
        self.dynamic_info_layout.setSpacing(2)

        dynamic_labels_grid = QGridLayout()
        dynamic_labels_grid.setContentsMargins(0, 0, 0, 0)
        dynamic_labels_grid.setSpacing(2)
        row = 0

        dynamic_labels_grid.addWidget(QLabel("Tamaño Total:"), row, 0)
        self.lbl_disk_total = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_disk_total, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Disponible:"), row, 0)
        self.lbl_disk_available = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_disk_available, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Usado:"), row, 0)
        self.lbl_disk_used = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_disk_used, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Porcentaje de uso:"), row, 0)
        self.lbl_disk_percent = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_disk_percent, row, 1)
        row += 1

        self.dynamic_info_layout.addLayout(dynamic_labels_grid)
        self.dynamic_info_layout.addStretch()
        self.info_h_layout.addWidget(self.dynamic_info_frame)

        # Static Disk Information
        self.static_info_frame = QFrame()
        self.static_info_frame.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-radius: 0px; padding: 10px;")
        self.static_info_layout = QGridLayout(self.static_info_frame)
        self.static_info_layout.setContentsMargins(5, 5, 5, 5)
        self.static_info_layout.setSpacing(2)

        self.static_info_layout.addWidget(QLabel("<h2>Información del Disco</h2>"), 0, 0, 1, 2)
        row = 1

        self.static_info_layout.addWidget(QLabel("Velocidad de Lectura:"), row, 0)
        self.lbl_disk_read_speed = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_disk_read_speed, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("Velocidad de Escritura:"), row, 0)
        self.lbl_disk_write_speed = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_disk_write_speed, row, 1)
        row += 1

        self.static_info_layout.setRowStretch(row, 1)
        self.info_h_layout.addWidget(self.static_info_frame)

        self.info_h_layout.setStretch(0, 1)
        self.info_h_layout.setStretch(1, 1)

        self.scroll_area.setWidget(self.scroll_content_widget)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addStretch()

        self.last_disk_io_counters = psutil.disk_io_counters(perdisk=False)


    def update_dynamic_info(self):
        disk_usage = psutil.disk_usage('/')
        total_gb = disk_usage.total / (1024**3)
        used_gb = disk_usage.used / (1024**3)
        available_gb = disk_usage.free / (1024**3)
        percent_usage = disk_usage.percent

        self.lbl_disk_total.setText(f"{total_gb:.2f} GB")
        self.lbl_disk_available.setText(f"{available_gb:.2f} GB")
        self.lbl_disk_used.setText(f"{used_gb:.2f} GB")
        self.lbl_disk_percent.setText(f"{percent_usage:.1f}%")

        current_disk_io = psutil.disk_io_counters(perdisk=False)
        read_bytes_diff = 0
        write_bytes_diff = 0

        if self.last_disk_io_counters:
            read_bytes_diff = current_disk_io.read_bytes - self.last_disk_io_counters.read_bytes
            write_bytes_diff = current_disk_io.write_bytes - self.last_disk_io_counters.write_bytes
            self.disk_io_graph.update_data((read_bytes_diff, write_bytes_diff))
        self.last_disk_io_counters = current_disk_io

        def format_bytes_per_second(bytes_val):
            if bytes_val >= (1024**3):
                return f"{bytes_val / (1024**3):.2f} GB/s"
            elif bytes_val >= (1024**2):
                return f"{bytes_val / (1024**2):.2f} MB/s"
            elif bytes_val >= 1024:
                return f"{bytes_val / 1024:.2f} KB/s"
            else:
                return f"{bytes_val:.2f} Bytes/s"

        self.lbl_disk_read_speed.setText(format_bytes_per_second(read_bytes_diff))
        self.lbl_disk_write_speed.setText(format_bytes_per_second(write_bytes_diff))


class NetworkDetailWidget(QWidget):
    back_to_dashboard = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        back_button = create_styled_back_button(self.back_to_dashboard.emit)
        self.main_layout.addWidget(back_button, alignment=Qt.AlignLeft)

        self.network_detail_graph = LiveGraphWidget("Uso de Red", "Datos (Bytes/s)", maxlen=120, shadow=False)
        self.network_detail_graph.setMinimumHeight(250)
        self.main_layout.addWidget(self.network_detail_graph)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.scroll_content_widget = QWidget()
        self.info_h_layout = QHBoxLayout(self.scroll_content_widget)
        self.info_h_layout.setSpacing(20)
        self.info_h_layout.setContentsMargins(0, 0, 0, 0)

        # Dynamic Network Information Frame
        self.dynamic_info_frame = QFrame()
        self.dynamic_info_frame.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-radius: 0px; padding: 10px;")
        self.dynamic_info_layout = QVBoxLayout(self.dynamic_info_frame)
        self.dynamic_info_layout.setContentsMargins(5, 5, 5, 5)
        self.dynamic_info_layout.setSpacing(2)

        dynamic_labels_grid = QGridLayout()
        dynamic_labels_grid.setContentsMargins(0, 0, 0, 0)
        dynamic_labels_grid.setSpacing(2)
        row = 0

        dynamic_labels_grid.addWidget(QLabel("Recibido:"), row, 0)
        self.lbl_net_received = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_net_received, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Enviado:"), row, 0)
        self.lbl_net_sent = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_net_sent, row, 1)
        row += 1

        self.dynamic_info_layout.addLayout(dynamic_labels_grid)
        self.dynamic_info_layout.addStretch()
        self.info_h_layout.addWidget(self.dynamic_info_frame)

        # Static Network Information
        self.static_info_frame = QFrame()
        self.static_info_frame.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-radius: 0px; padding: 10px;")
        self.static_info_layout = QGridLayout(self.static_info_frame)
        self.static_info_layout.setContentsMargins(5, 5, 5, 5)
        self.static_info_layout.setSpacing(2)

        self.static_info_layout.addWidget(QLabel("<h2>Información de Red</h2>"), 0, 0, 1, 2)
        row = 1

        self.static_info_layout.addWidget(QLabel("Dirección IP (IPv4):"), row, 0)
        self.lbl_net_ip = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_net_ip, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("Dirección MAC:"), row, 0)
        self.lbl_net_mac = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_net_mac, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("Velocidad Nominal:"), row, 0)
        self.lbl_net_speed = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_net_speed, row, 1)
        row += 1

        self.static_info_layout.setRowStretch(row, 1)
        self.info_h_layout.addWidget(self.static_info_frame)

        self.info_h_layout.setStretch(0, 1)
        self.info_h_layout.setStretch(1, 1)

        self.scroll_area.setWidget(self.scroll_content_widget)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addStretch()

        self.last_net_io_counters = psutil.net_io_counters()
        self.update_static_info()

    def update_dynamic_info(self):
        current_net_io = psutil.net_io_counters()
        bytes_sent_diff = current_net_io.bytes_sent - self.last_net_io_counters.bytes_sent
        bytes_recv_diff = current_net_io.bytes_recv - self.last_net_io_counters.bytes_recv
        self.last_net_io_counters = current_net_io

        self.network_detail_graph.update_data((bytes_sent_diff, bytes_recv_diff))

        def format_bytes_per_second(bytes_val):
            if bytes_val >= (1024**3):
                return f"{bytes_val / (1024**3):.2f} GB/s"
            elif bytes_val >= (1024**2):
                return f"{bytes_val / (1024**2):.2f} MB/s"
            elif bytes_val >= 1024:
                return f"{bytes_val / 1024:.2f} KB/s"
            else:
                return f"{bytes_val:.2f} Bytes/s"

        self.lbl_net_received.setText(format_bytes_per_second(bytes_recv_diff))
        self.lbl_net_sent.setText(format_bytes_per_second(bytes_sent_diff))

    def update_static_info(self):
        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        primary_ip = "N/A"
        primary_mac = "N/A"
        primary_speed = "N/A"

        active_interfaces = []
        for if_name, addrs in interfaces.items():
            if if_name in stats and stats[if_name].isup and \
               not (if_name == 'lo' or if_name.startswith('docker') or if_name.startswith('br-')):
                active_interfaces.append((if_name, addrs))

        active_interfaces.sort(key=lambda x: any(addr.family == socket.AF_INET for addr in x[1]), reverse=True)

        for if_name, addrs in active_interfaces:
            current_ip = "N/A"
            current_mac = "N/A"

            for addr in addrs:
                if addr.family == socket.AF_INET:
                    current_ip = addr.address
                elif addr.family == psutil.AF_LINK:
                    current_mac = addr.address

            if current_ip != "N/A" and current_mac != "N/A":
                primary_interface_name = if_name
                primary_ip = current_ip
                primary_mac = current_mac

                if if_name in stats and stats[if_name].speed != 0:
                    primary_speed = f"{stats[if_name].speed} Mbps"

                break

        self.lbl_net_ip.setText(primary_ip)
        self.lbl_net_mac.setText(primary_mac)
        self.lbl_net_speed.setText(primary_speed)


class GPUDetailWidget(QWidget):
    back_to_dashboard = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        back_button = create_styled_back_button(self.back_to_dashboard.emit)
        self.main_layout.addWidget(back_button, alignment=Qt.AlignLeft)

        self.gpu_detail_graph = LiveGraphWidget("GPU Usage (Detailed)", "GPU (%)", maxlen=120, shadow=False)
        self.gpu_detail_graph.setMinimumHeight(250)
        self.main_layout.addWidget(self.gpu_detail_graph)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.scroll_content_widget = QWidget()
        self.info_h_layout = QHBoxLayout(self.scroll_content_widget)
        self.info_h_layout.setSpacing(20)
        self.info_h_layout.setContentsMargins(0, 0, 0, 0)

        # Dynamic GPU Information
        self.dynamic_info_frame = QFrame()
        self.dynamic_info_frame.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-radius: 0px; padding: 10px;")
        self.dynamic_info_layout = QVBoxLayout(self.dynamic_info_frame)
        self.dynamic_info_layout.setContentsMargins(5, 5, 5, 5)
        self.dynamic_info_layout.setSpacing(2)

        dynamic_labels_grid = QGridLayout()
        dynamic_labels_grid.setContentsMargins(0, 0, 0, 0)
        dynamic_labels_grid.setSpacing(2)
        row = 0

        dynamic_labels_grid.addWidget(QLabel("Porcentaje de Uso:"), row, 0)
        self.lbl_gpu_usage = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_gpu_usage, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Temperatura:"), row, 0)
        self.lbl_gpu_temperature = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_gpu_temperature, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Memoria Usada:"), row, 0)
        self.lbl_gpu_memory_used = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_gpu_memory_used, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Memoria Disponible:"), row, 0)
        self.lbl_gpu_memory_free = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_gpu_memory_free, row, 1)
        row += 1

        dynamic_labels_grid.addWidget(QLabel("Porcentaje Memoria:"), row, 0)
        self.lbl_gpu_memory_percent = QLabel("N/A")
        dynamic_labels_grid.addWidget(self.lbl_gpu_memory_percent, row, 1)
        row += 1

        self.dynamic_info_layout.addLayout(dynamic_labels_grid)
        self.dynamic_info_layout.addStretch()
        self.info_h_layout.addWidget(self.dynamic_info_frame)

        # Static GPU Information
        self.static_info_frame = QFrame()
        self.static_info_frame.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-radius: 0px; padding: 10px;")
        self.static_info_layout = QGridLayout(self.static_info_frame)
        self.static_info_layout.setContentsMargins(5, 5, 5, 5)
        self.static_info_layout.setSpacing(2)

        self.static_info_layout.addWidget(QLabel("<h2>Información de la GPU</h2>"), 0, 0, 1, 2)
        row = 1

        self.static_info_layout.addWidget(QLabel("Nombre de la GPU:"), row, 0)
        self.lbl_gpu_name = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_gpu_name, row, 1)
        row += 1

        self.static_info_layout.addWidget(QLabel("Memoria Total:"), row, 0)
        self.lbl_gpu_total_memory = QLabel("N/A")
        self.static_info_layout.addWidget(self.lbl_gpu_total_memory, row, 1)
        row += 1

        self.static_info_layout.setRowStretch(row, 1)
        self.info_h_layout.addWidget(self.static_info_frame)

        self.info_h_layout.setStretch(0, 1)
        self.info_h_layout.setStretch(1, 1)

        self.scroll_area.setWidget(self.scroll_content_widget)
        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addStretch()

        self.update_static_info()

    def update_static_info(self):
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    self.lbl_gpu_name.setText(gpu.name)
                    self.lbl_gpu_total_memory.setText(f"{gpu.memoryTotal:.2f} MB")
                else:
                    self.lbl_gpu_name.setText("No GPU detectada.")
                    self.lbl_gpu_total_memory.setText("N/A")
            except Exception as e:
                self.lbl_gpu_name.setText("N/A (Error al obtener información de GPU)")
                self.lbl_gpu_total_memory.setText("N/A (Error al obtener información de GPU)")
                print(f"Error getting GPU static info: {e}")
        else:
            self.lbl_gpu_name.setText("N/A (GPUtil no encontrado)")
            self.lbl_gpu_total_memory.setText("N/A (GPUtil no encontrado)")


    def update_dynamic_info(self):
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    gpu_load_percent = gpu.load * 100
                    memory_used_mb = gpu.memoryUsed
                    memory_free_mb = gpu.memoryFree
                    memory_total_mb = gpu.memoryTotal
                    memory_util_percent = gpu.memoryUtil * 100
                    gpu_temperature = gpu.temperature

                    self.lbl_gpu_usage.setText(f"{gpu_load_percent:.1f}%")
                    self.lbl_gpu_temperature.setText(f"{gpu_temperature:.1f} °C")
                    self.lbl_gpu_memory_used.setText(f"{memory_used_mb / 1000:.2f} GB")
                    self.lbl_gpu_memory_free.setText(f"{memory_free_mb / 1000:.2f} GB")
                    self.lbl_gpu_memory_percent.setText(f"{memory_util_percent:.1f}%")

                    self.gpu_detail_graph.update_data(gpu_load_percent)
                else:
                    self.lbl_gpu_usage.setText("No GPU detectada.")
                    self.lbl_gpu_temperature.setText("N/A")
                    self.lbl_gpu_memory_used.setText("N/A")
                    self.lbl_gpu_memory_free.setText("N/A")
                    self.lbl_gpu_memory_percent.setText("N/A")

            except Exception as e:
                self.lbl_gpu_usage.setText("N/A (Error)")
                self.lbl_gpu_temperature.setText("N/A")
                self.lbl_gpu_memory_used.setText("N/A")
                self.lbl_gpu_memory_free.setText("N/A")
                self.lbl_gpu_memory_percent.setText("N/A")

                print(f"Error getting GPU dynamic info: {e}")
        else:
            self.lbl_gpu_usage.setText("N/A (GPUtil no encontrado)")
            self.lbl_gpu_temperature.setText("N/A")
            self.lbl_gpu_memory_used.setText("N/A")
            self.lbl_gpu_memory_free.setText("N/A")
            self.lbl_gpu_memory_percent.setText("N/A")


class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MonitorMoya")
        self.setGeometry(100, 100, 1400, 800)
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {BG_COLOR_DARK};
                font-family: 'Segoe UI', 'Open Sans', Arial, sans-serif;
                color: {TEXT_COLOR_LIGHT};
            }}
            QLabel {{
                color: {TEXT_COLOR_LIGHT};
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {TEXT_COLOR_LIGHT};
                padding: 10px;
                text-align: left;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {BG_COLOR_LIGHT};
                border-radius: 5px;
            }}
            QFrame {{
                background-color: {BG_COLOR_MEDIUM};
                border-radius: 8px;
            }}
            QProgressBar {{
                background: {BG_COLOR_DARK};
                border: 1px solid {ACCENT_COLOR_BLUE};
                border-radius: 4px;
                height: 15px;
                text-align: center;
                color: {TEXT_COLOR_LIGHT};
                font-size: 10px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {ACCENT_COLOR_BLUE}, stop:1 {ACCENT_COLOR_GREEN}
                );
                border-radius: 3px;
            }}
            QScrollArea {{
                border: none;
            }}
            QListWidget {{
                background-color: {BG_COLOR_MEDIUM};
                border: none;
                color: {TEXT_COLOR_LIGHT};
            }}
            QListWidget::item {{
                padding: 5px;
                border-bottom: 1px solid {BG_COLOR_DARK};
            }}
            QListWidget::item:hover {{
                background-color: {BG_COLOR_LIGHT};
            }}
            QHeaderView::section {{
                background-color: {BG_COLOR_MEDIUM};
                color: {TEXT_COLOR_LIGHT};
                padding: 4px;
                border: 1px solid {BG_COLOR_DARK};
            }}
            QStatusBar {{
                background-color: {BG_COLOR_MEDIUM};
                color: {TEXT_COLOR_MUTED};
                font-size: 12px;
                padding-left: 10px;
            }}
        """)

        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 5, 10, 5)
        header_layout.setSpacing(15)

        left_header_layout = QHBoxLayout()
        n_home_label = QLabel("Dashboard")
        n_home_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        n_home_label.setStyleSheet(f"color: {TEXT_COLOR_LIGHT};")
        n_home_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        left_header_layout.addWidget(n_home_label)

        left_header_layout.addStretch()

        header_layout.addLayout(left_header_layout)

        header_widget.setLayout(header_layout)
        header_widget.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-bottom: 1px solid {BG_COLOR_DARK};")

        self.menu_widget = QFrame()
        self.menu_widget.setFixedWidth(200)
        self.menu_widget.setStyleSheet(f"background-color: {BG_COLOR_MEDIUM}; border-radius: 0px;")
        self.menu_layout = QVBoxLayout(self.menu_widget)
        self.menu_layout.setContentsMargins(10, 10, 10, 10)
        self.menu_layout.setSpacing(5)

        menu_items_text = [
            ("Dashboard"),
            ("CPU"),
            ("RAM"),
            ("Disco"),
            ("Red"),
            ("GPU"),
        ]
        self.menu_buttons = []

        for text in menu_items_text:
            btn = QPushButton(f"{text}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {TEXT_COLOR_MUTED};
                    background-color: transparent;
                    border: none;
                    text-align: left;
                    padding: 8px 10px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {BG_COLOR_LIGHT};
                    border-radius: 5px;
                    color: {TEXT_COLOR_LIGHT};
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.menu_layout.addWidget(btn)
            self.menu_buttons.append(btn)

        self.menu_buttons[0].clicked.connect(self.show_dashboard)
        self.menu_buttons[1].clicked.connect(self.show_cpu_detail)
        self.menu_buttons[2].clicked.connect(self.show_ram_detail)
        self.menu_buttons[3].clicked.connect(self.show_disk_detail)
        self.menu_buttons[4].clicked.connect(self.show_network_detail)
        self.menu_buttons[5].clicked.connect(self.show_gpu_detail)

        self.menu_layout.addStretch()

        self.dashboard_view = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_view)
        self.dashboard_layout.setContentsMargins(20, 20, 20, 20)
        self.dashboard_layout.setSpacing(20)

        graph_row_1_widget = QWidget()
        graph_row_1_layout = QHBoxLayout(graph_row_1_widget)
        graph_row_1_layout.setSpacing(20)

        self.cpu_graph = LiveGraphWidget("Uso de CPU", "CPU (%)")
        self.cpu_graph.setMinimumHeight(150)
        self.cpu_graph.clicked.connect(self.show_cpu_detail)
        graph_row_1_layout.addWidget(self.cpu_graph)

        self.ram_graph = LiveGraphWidget("Uso de RAM (Memoria)", "RAM (%)")
        self.ram_graph.setMinimumHeight(150)
        self.ram_graph.clicked.connect(self.show_ram_detail)
        graph_row_1_layout.addWidget(self.ram_graph)

        self.disk_io_dashboard_graph = LiveGraphWidget("Velocidad del Disco", "Velocidad (Bytes/s)")
        self.disk_io_dashboard_graph.setMinimumHeight(150)
        self.disk_io_dashboard_graph.clicked.connect(self.show_disk_detail)
        graph_row_1_layout.addWidget(self.disk_io_dashboard_graph)

        self.dashboard_layout.addWidget(graph_row_1_widget)

        graph_row_2_widget = QWidget()
        graph_row_2_layout = QHBoxLayout(graph_row_2_widget)
        graph_row_2_layout.setSpacing(20)

        self.network_graph = LiveGraphWidget("Uso de Red", "Datos (Bytes/s)")
        self.network_graph.setMinimumHeight(150)
        self.network_graph.clicked.connect(self.show_network_detail)
        graph_row_2_layout.addWidget(self.network_graph)

        self.gpu_graph = None
        gpu_detected = False
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    self.gpu_graph = LiveGraphWidget(f"Uso GPU ({gpus[0].name})", "GPU (%)")
                    self.gpu_graph.setMinimumHeight(150)
                    self.gpu_graph.clicked.connect(self.show_gpu_detail)
                    graph_row_2_layout.addWidget(self.gpu_graph)
                    gpu_detected = True
            except Exception:
                pass

        if not gpu_detected:
            gpu_placeholder = QLabel("No GPU detectada.")
            gpu_placeholder.setAlignment(Qt.AlignCenter)
            gpu_placeholder.setStyleSheet(f"color: {TEXT_COLOR_MUTED}; background-color: {BG_COLOR_MEDIUM}; border-radius: 8px; padding: 20px;")
            graph_row_2_layout.addWidget(gpu_placeholder)

        self.dashboard_layout.addWidget(graph_row_2_widget)

        top_processes_frame = QFrame()
        top_processes_layout = QVBoxLayout(top_processes_frame)
        top_processes_layout.setContentsMargins(15, 15, 15, 15)
        top_processes_layout.setSpacing(10)

        top_processes_label = QLabel("Procesos")
        top_processes_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        top_processes_layout.addWidget(top_processes_label)

        self.process_list_widget = QListWidget()
        self.process_list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {BG_COLOR_DARK};
                border: 1px solid {BG_COLOR_LIGHT};
                border-radius: 5px;
                color: {TEXT_COLOR_LIGHT};
                font-size: 12px;
            }}
            QListWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {BG_COLOR_MEDIUM};
            }}
        """)
        top_processes_layout.addWidget(self.process_list_widget)

        self.dashboard_layout.addWidget(top_processes_frame)

        self.dashboard_layout.addStretch()

        self.cpu_detail_widget = CPUDetailWidget()
        self.cpu_detail_widget.back_to_dashboard.connect(self.show_dashboard)

        self.ram_detail_widget = RAMDetailedWidget()
        self.ram_detail_widget.back_to_dashboard.connect(self.show_dashboard)

        self.disk_detail_widget = DiskDetailWidget()
        self.disk_detail_widget.back_to_dashboard.connect(self.show_dashboard)

        self.network_detail_widget = NetworkDetailWidget()
        self.network_detail_widget.back_to_dashboard.connect(self.show_dashboard)

        self.gpu_detail_widget = GPUDetailWidget()
        self.gpu_detail_widget.back_to_dashboard.connect(self.show_dashboard)

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.dashboard_view)
        self.content_stack.addWidget(self.cpu_detail_widget)
        self.content_stack.addWidget(self.ram_detail_widget)
        self.content_stack.addWidget(self.disk_detail_widget)
        self.content_stack.addWidget(self.network_detail_widget)
        self.content_stack.addWidget(self.gpu_detail_widget)

        central_widget = QWidget()
        main_h_layout = QHBoxLayout(central_widget)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        main_v_layout = QVBoxLayout()
        main_v_layout.setContentsMargins(0, 0, 0, 0)
        main_v_layout.setSpacing(0)
        main_v_layout.addWidget(header_widget)
        main_v_layout.addWidget(self.content_stack)

        main_h_layout.addWidget(self.menu_widget)
        main_h_layout.addLayout(main_v_layout)

        self.setCentralWidget(central_widget)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage(f"Todo fino | {platform.node()} | OS: {platform.system()} {platform.release()}")

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_resource_usage)
        self.timer.start()

        self.last_net_io = psutil.net_io_counters()
        self.last_disk_io = psutil.disk_io_counters(perdisk=False)

    def update_resource_usage(self):
        cpu_percent = psutil.cpu_percent(interval=None)
        self.cpu_graph.update_data(cpu_percent)

        ram_percent = psutil.virtual_memory().percent
        self.ram_graph.update_data(ram_percent)

        current_disk_io_dashboard = psutil.disk_io_counters(perdisk=False)
        bytes_read_diff_disk_dashboard = current_disk_io_dashboard.read_bytes - self.last_disk_io.read_bytes
        bytes_write_diff_disk_dashboard = current_disk_io_dashboard.write_bytes - self.last_disk_io.write_bytes
        self.last_disk_io = current_disk_io_dashboard
        self.disk_io_dashboard_graph.update_data((bytes_read_diff_disk_dashboard, bytes_write_diff_disk_dashboard))

        current_net_io = psutil.net_io_counters()
        bytes_sent_diff = current_net_io.bytes_sent - self.last_net_io.bytes_sent
        bytes_recv_diff = current_net_io.bytes_recv - self.last_net_io.bytes_recv
        self.last_net_io = current_net_io
        self.network_graph.update_data((bytes_sent_diff, bytes_recv_diff))

        if self.gpu_graph:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_percent = gpus[0].load * 100
                    self.gpu_graph.update_data(gpu_percent)
            except Exception:
                pass

        self.process_list_widget.clear()
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)

        for i, proc in enumerate(processes[:10]):
            item_text = f"{proc.get('name', 'N/A')}: {proc.get('cpu_percent', 0):.1f}% CPU"
            item = QListWidgetItem(item_text)
            self.process_list_widget.addItem(item)
            if i % 2 == 0:
                 item.setBackground(QColor(BG_COLOR_DARK))

        if self.content_stack.currentWidget() == self.cpu_detail_widget:
            self.cpu_detail_widget.update_dynamic_info()
        elif self.content_stack.currentWidget() == self.ram_detail_widget:
            self.ram_detail_widget.update_dynamic_info()
        elif self.content_stack.currentWidget() == self.disk_detail_widget:
            self.disk_detail_widget.update_dynamic_info()
        elif self.content_stack.currentWidget() == self.network_detail_widget:
            self.network_detail_widget.update_dynamic_info()
        elif self.content_stack.currentWidget() == self.gpu_detail_widget:
            self.gpu_detail_widget.update_dynamic_info()

    def show_cpu_detail(self):
        self.content_stack.setCurrentIndex(1)

    def show_ram_detail(self):
        self.content_stack.setCurrentIndex(2)

    def show_disk_detail(self):
        self.content_stack.setCurrentIndex(3)

    def show_network_detail(self):
        self.content_stack.setCurrentIndex(4)

    def show_gpu_detail(self):
        self.content_stack.setCurrentIndex(5)

    def show_dashboard(self):
        self.content_stack.setCurrentIndex(0)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

    window = Dashboard()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()