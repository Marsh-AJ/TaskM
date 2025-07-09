import sys
import psutil
from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QFrame, QGridLayout, QDialog, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation
import qdarkstyle

class ResourceCard(QFrame):
    def __init__(self, resource_name, parent=None):
        super().__init__(parent)
        self.resource_name = resource_name
        self.setObjectName(resource_name)
        self.setStyleSheet("""
            QFrame {
                background-color: #232a36;
                border-radius: 14px;
                border: 2px solid #232a36;
            }
            QFrame:hover {
                border: 2px solid #00bfff;
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 #232a36, stop:0.5 #00bfff22, stop:1 #232a36
                );
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 191, 255, 100)) 
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)  # 200ms de duración

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(220, 140)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon = QLabel()
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setFont(QFont("Open Sans", 32))
        # Puedes personalizar los íconos aquí
        icons = {"CPU": "🖥️", "RAM": "💾", "Disco": "🗄️", "Red": "🌐"}
        self.icon.setText(icons.get(resource_name, "❓"))
        self.title = QLabel(resource_name)
        self.title.setFont(QFont("Open Sans", 16, QFont.Bold))
        self.title.setStyleSheet("color: #00bfff;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #181e27;
                border: 1px solid #00bfff;
                border-radius: 6px;
                height: 20px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00bfff, stop:1 #0066ff
                );
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

    def mousePressEvent(self, event):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalles de {self.resource_name}")
        dialog.setStyleSheet("background-color: #232a36; color: #fff; font-family: 'Open Sans';")
        dialog.setFixedSize(400, 200)
        vbox = QVBoxLayout()
        label = QLabel(f"Aquí se mostrarán los detalles y gráficos de {self.resource_name}.")
        label.setFont(QFont("Open Sans", 16))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addStretch()
        vbox.addWidget(label)
        vbox.addStretch()
        dialog.setLayout(vbox)
        dialog.exec_()

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Recursos - Dashboard Moderno")
        self.setGeometry(400, 100, 1100, 650)
        self.setStyleSheet("font-family: 'Open Sans', Arial, sans-serif;")

        # --- Menú lateral ---
        self.menu_widget = QWidget()
        self.menu_widget.setStyleSheet("background-color: #232a36;")
        self.menu_layout = QVBoxLayout()
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setSpacing(20)

        # Título del menú
        menu_title = QLabel("taskM")
        menu_title.setFont(QFont("Open Sans", 22, QFont.Bold))
        menu_title.setStyleSheet("color: #00bfff; padding: 20px 0 10px 0;")
        menu_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.menu_layout.addWidget(menu_title)

        # Botones del menú
        btn_dashboard = QPushButton("  Dashboard")
        btn_dashboard.setStyleSheet("color: #fff; background: none; text-align: left; padding: 10px 20px; font-size: 16px;")
        btn_dashboard.setIcon(QIcon.fromTheme("view-dashboard"))
        btn_dashboard.setIconSize(QSize(24, 24))
        btn_dashboard.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dashboard.setFlat(True)
        self.menu_layout.addWidget(btn_dashboard)

        btn_settings = QPushButton("  Configuración")
        btn_settings.setStyleSheet("color: #fff; background: none; text-align: left; padding: 10px 20px; font-size: 16px;")
        btn_settings.setIcon(QIcon.fromTheme("settings"))
        btn_settings.setIconSize(QSize(24, 24))
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.setFlat(True)
        self.menu_layout.addWidget(btn_settings)

        self.menu_layout.addStretch()
        self.menu_widget.setLayout(self.menu_layout)
        self.menu_widget.setFixedWidth(200)

        # --- Panel principal ---
        self.main_panel = QWidget()
        self.main_panel.setStyleSheet("background-color: #181e27;")
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        # Título principal
        title = QLabel("Monitor de Recursos del Sistema")
        title.setFont(QFont("Open Sans", 24, QFont.Bold))
        title.setStyleSheet("color: #fff;")
        self.main_layout.addWidget(title)

        # Collage de tarjetas (cards)
        collage_widget = QWidget()
        collage_layout = QGridLayout()
        collage_layout.setSpacing(30)
        self.cards = {}
        resources = ["CPU", "RAM", "Disco", "Red"]
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for resource, pos in zip(resources, positions):
            card = ResourceCard(resource)
            self.cards[resource] = card
            collage_layout.addWidget(card, *pos)
        collage_widget.setLayout(collage_layout)
        self.main_layout.addWidget(collage_widget)

        # Placeholder para gráficos generales
        graph_placeholder = QLabel("[Aquí irán los gráficos en tiempo real]")
        graph_placeholder.setFont(QFont("Open Sans", 16))
        graph_placeholder.setStyleSheet("color: #aaa; padding: 60px;")
        graph_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(graph_placeholder)

        self.main_panel.setLayout(self.main_layout)

        # --- Layout general ---
        central_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.menu_widget)
        layout.addWidget(self.main_panel)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # --- Barra de estado ---     
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("✅ Sistema activo | Modo: Oscuro | v1.0")
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #232a36;
                color: #00bfff;
                font-family: 'Open Sans';
                padding-left: 10px;
            }
        """)

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
import sys
import psutil
from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QFrame, QGridLayout, QDialog, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation
import qdarkstyle

class ResourceCard(QFrame):
    def __init__(self, resource_name, parent=None):
        super().__init__(parent)
        self.resource_name = resource_name
        self.setObjectName(resource_name)
        self.setStyleSheet("""
            QFrame {
                background-color: #232a36;
                border-radius: 14px;
                border: 2px solid #232a36;
            }
            QFrame:hover {
                border: 2px solid #00bfff;
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 #232a36, stop:0.5 #00bfff22, stop:1 #232a36
                );
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 191, 255, 100)) 
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)

        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)  # 200ms de duración

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(220, 140)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon = QLabel()
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setFont(QFont("Open Sans", 32))
        # Puedes personalizar los íconos aquí
        icons = {"CPU": "🖥️", "RAM": "💾", "Disco": "🗄️", "Red": "🌐"}
        self.icon.setText(icons.get(resource_name, "❓"))
        self.title = QLabel(resource_name)
        self.title.setFont(QFont("Open Sans", 16, QFont.Bold))
        self.title.setStyleSheet("color: #00bfff;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: #181e27;
                border: 1px solid #00bfff;
                border-radius: 6px;
                height: 20px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00bfff, stop:1 #0066ff
                );
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)

    def mousePressEvent(self, event):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Detalles de {self.resource_name}")
        dialog.setStyleSheet("background-color: #232a36; color: #fff; font-family: 'Open Sans';")
        dialog.setFixedSize(400, 200)
        vbox = QVBoxLayout()
        label = QLabel(f"Aquí se mostrarán los detalles y gráficos de {self.resource_name}.")
        label.setFont(QFont("Open Sans", 16))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addStretch()
        vbox.addWidget(label)
        vbox.addStretch()
        dialog.setLayout(vbox)
        dialog.exec_()

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor de Recursos - Dashboard Moderno")
        self.setGeometry(400, 100, 1100, 650)
        self.setStyleSheet("font-family: 'Open Sans', Arial, sans-serif;")

        # --- Menú lateral ---
        self.menu_widget = QWidget()
        self.menu_widget.setStyleSheet("background-color: #232a36;")
        self.menu_layout = QVBoxLayout()
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setSpacing(20)

        # Título del menú
        menu_title = QLabel("taskM")
        menu_title.setFont(QFont("Open Sans", 22, QFont.Bold))
        menu_title.setStyleSheet("color: #00bfff; padding: 20px 0 10px 0;")
        menu_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.menu_layout.addWidget(menu_title)

        # Botones del menú
        btn_dashboard = QPushButton("  Dashboard")
        btn_dashboard.setStyleSheet("color: #fff; background: none; text-align: left; padding: 10px 20px; font-size: 16px;")
        btn_dashboard.setIcon(QIcon.fromTheme("view-dashboard"))
        btn_dashboard.setIconSize(QSize(24, 24))
        btn_dashboard.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dashboard.setFlat(True)
        self.menu_layout.addWidget(btn_dashboard)

        btn_settings = QPushButton("  Configuración")
        btn_settings.setStyleSheet("color: #fff; background: none; text-align: left; padding: 10px 20px; font-size: 16px;")
        btn_settings.setIcon(QIcon.fromTheme("settings"))
        btn_settings.setIconSize(QSize(24, 24))
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.setFlat(True)
        self.menu_layout.addWidget(btn_settings)

        self.menu_layout.addStretch()
        self.menu_widget.setLayout(self.menu_layout)
        self.menu_widget.setFixedWidth(200)

        # --- Panel principal ---
        self.main_panel = QWidget()
        self.main_panel.setStyleSheet("background-color: #181e27;")
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(20)

        # Título principal
        title = QLabel("Monitor de Recursos del Sistema")
        title.setFont(QFont("Open Sans", 24, QFont.Bold))
        title.setStyleSheet("color: #fff;")
        self.main_layout.addWidget(title)

        # Collage de tarjetas (cards)
        collage_widget = QWidget()
        collage_layout = QGridLayout()
        collage_layout.setSpacing(30)
        self.cards = {}
        resources = ["CPU", "RAM", "Disco", "Red"]
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for resource, pos in zip(resources, positions):
            card = ResourceCard(resource)
            self.cards[resource] = card
            collage_layout.addWidget(card, *pos)
        collage_widget.setLayout(collage_layout)
        self.main_layout.addWidget(collage_widget)

        # Placeholder para gráficos generales
        graph_placeholder = QLabel("[Aquí irán los gráficos en tiempo real]")
        graph_placeholder.setFont(QFont("Open Sans", 16))
        graph_placeholder.setStyleSheet("color: #aaa; padding: 60px;")
        graph_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(graph_placeholder)

        self.main_panel.setLayout(self.main_layout)

        # --- Layout general ---
        central_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.menu_widget)
        layout.addWidget(self.main_panel)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # --- Barra de estado ---     
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("✅ Sistema activo | Modo: Oscuro | v1.0")
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #232a36;
                color: #00bfff;
                font-family: 'Open Sans';
                padding-left: 10px;
            }
        """)

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
