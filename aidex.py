import sys
import time
import json
import pyotp
import pyperclip
import binascii
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QDialog, QPushButton, QLineEdit, QVBoxLayout, QWidget, QHBoxLayout, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QScrollArea, QFrame, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import QTimer, Qt, pyqtSlot, QEvent
from PyQt5.QtGui import QIcon, QCursor, QDrag
from qt_material import apply_stylesheet
import os

if hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

icon_path = os.path.join(base_path, 'icon.png')

# 获取用户文档目录
from pathlib import Path
CONFIG_FILE = os.path.join(str(Path.home()), "Documents", "totp_config.json")


def correct_secret_padding(secret):
    secret = secret.strip().replace(' ', '').upper()
    missing_padding = len(secret) % 8
    if missing_padding:
        secret += '=' * (8 - missing_padding)
    return secret


class DraggableTableWidget(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropOverwriteMode(False)
        self.setDropIndicatorShown(True)

        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setDragDropMode(QAbstractItemView.InternalMove)

        self.drag_start_position = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mimedata = self.model().mimeData(self.selectedIndexes())

        if mimedata:
            drag.setMimeData(mimedata)
            drag.exec_(Qt.MoveAction)

    def dropEvent(self, event):
        if event.source() == self and (event.dropAction() == Qt.MoveAction or self.dragDropMode() == QAbstractItemView.InternalMove):
            success, row, col, topIndex = self.dropOn(event)
            if success:
                selRows = self.getSelectedRowsFast()
                top = selRows[0]

                dropRow = row
                if dropRow == -1:
                    dropRow = self.rowCount()
                if dropRow > top:
                    dropRow -= 1

                rows = []
                for i in range(len(selRows)):
                    rows.append(self.extractRow(top))
                for i in range(len(rows)):
                    self.insertRow(dropRow)
                    for j in range(self.columnCount()):
                        self.setItem(dropRow, j, rows[i][j])
                    dropRow += 1
                event.accept()

                # 更新数据模型
                self.window().update_data_model()

    def extractRow(self, row):
        items = []
        for column in range(self.columnCount()):
            items.append(self.takeItem(row, column))
        self.removeRow(row)
        return items

    def getSelectedRowsFast(self):
        selRows = []
        for item in self.selectedItems():
            if item.row() not in selRows:
                selRows.append(item.row())
        return selRows

    def dropOn(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return False, self.rowCount(), 0, index
        return True, index.row(), index.column(), index


class TOTPConfig:
    def __init__(self):
        self.configs = self.load_config()

    def load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    return json.loads(content)
                else:
                    return []
        except FileNotFoundError:
            return []

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.configs, f, indent=4)

    def add_config(self, name, secret, prefix="", suffix=""):
        self.configs.append({"name": name, "secret": secret, "prefix": prefix, "suffix": suffix})
        self.save_config()
        return True

    def update_config(self, index, name, secret, prefix="", suffix=""):
        self.configs[index] = {"name": name, "secret": secret, "prefix": prefix, "suffix": suffix}
        self.save_config()
        return True

    def delete_config(self, index):
        del self.configs[index]
        self.save_config()



class MainApp(QDialog):
    def __init__(self):
        super().__init__()
        self.config_manager = TOTPConfig()
        self.initUI()
        self.copy_timer = QTimer(self)
        self.copy_timer.setSingleShot(True)
        self.copy_timer.timeout.connect(self.perform_copy)

    def initUI(self):
        self.setWindowTitle("aidex")
        self.setGeometry(300, 300, 450, 400)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        self.main_widget = QWidget(self)
        self.layout = QVBoxLayout(self.main_widget)
        self.setLayout(self.layout)

        self.button_layout = QHBoxLayout()

        spacer = QSpacerItem(340, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.button_layout.addItem(spacer)

        self.add_button = QPushButton("+", self)
        self.add_button.clicked.connect(lambda: self.show_config_dialog("", "", "", "", is_new=True))
        self.add_button.setFixedWidth(45)
        self.add_button.setFocusPolicy(Qt.NoFocus)
        self.add_button.setStyleSheet("font-size: 16px;")
        self.button_layout.addWidget(self.add_button)

        spacer = QSpacerItem(7, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        self.button_layout.addItem(spacer)

        self.quit_button = QPushButton("×", self)
        self.quit_button.clicked.connect(lambda: quit())
        self.quit_button.setFixedWidth(45)
        self.quit_button.setFocusPolicy(Qt.NoFocus)
        self.quit_button.setStyleSheet("font-size: 16px;")
        self.button_layout.addWidget(self.quit_button)

        self.button_layout.addStretch()
        self.layout.addLayout(self.button_layout, Qt.AlignRight)

        self.table_widget = DraggableTableWidget(0, 4, self)
        self.table_widget.setShowGrid(False)
        self.table_widget.setHorizontalHeaderLabels(["Name", "TOTP", "Time Left", "Action"])
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.verticalHeader().setDefaultSectionSize(40)
        self.table_widget.setFrameStyle(QFrame.NoFrame)

        self.table_widget.setStyleSheet("""
            QTableWidget {
                border: 0px; font-size: 16px; border-radius: 15px; margin: 1px; 
            }
            QTableWidget::item {
                border-bottom: 0.5px solid #B3B3B3; padding: 5px;
            }
            QHeaderView::section:first {
                border-top-left-radius: 7px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 7px;
            }
        """)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.table_widget)
        self.layout.addWidget(self.scroll_area)

        self.icon = QIcon(icon_path)
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.icon)

        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_clicked)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_totp_codes)
        self.refresh_timer.start(1000)

        self.load_totp_configs()

    def tray_icon_clicked(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.show()
                self.raise_()
                self.activateWindow()
                self.move_to_cursor()
            else:
                self.hide()

    def move_to_cursor(self):
        cursor_pos = QCursor.pos()
        screen = QApplication.primaryScreen().availableGeometry()
        size = self.geometry()

        x = cursor_pos.x() - size.width() // 2
        if x < screen.left():
            x = screen.left()
        elif x + size.width() > screen.right():
            x = screen.right() - size.width()

        if cursor_pos.y() + size.height() <= screen.bottom():
            y = cursor_pos.y() + 10
        else:
            y = cursor_pos.y() - size.height() - 10

        self.move(x, y)

    def load_totp_configs(self):
        self.table_widget.setRowCount(0)
        for config in self.config_manager.configs:
            self.add_totp_item(config["name"], config["secret"], config["prefix"], config["suffix"])

    def add_totp_item(self, name, secret, prefix="", suffix=""):
        try:
            totp = pyotp.TOTP(secret)
            code = totp.now()
            time_remaining = totp.interval - time.time() % totp.interval + 1

            row_position = self.table_widget.rowCount()
            self.table_widget.insertRow(row_position)

            name_item = QTableWidgetItem(name)
            totp_item = QTableWidgetItem(f"{code}")
            time_item = QTableWidgetItem(str(int(time_remaining)))
            
            name_item.setTextAlignment(Qt.AlignCenter)
            totp_item.setTextAlignment(Qt.AlignCenter)
            time_item.setTextAlignment(Qt.AlignCenter)
            
            action_widget = QWidget(self)
            action_layout = QHBoxLayout(action_widget)

            action_button = QPushButton("≡", self)
            action_button.clicked.connect(lambda: self.show_config_dialog(name, secret, prefix, suffix, row_position))
            action_button.setFixedWidth(30)
            action_button.setFixedHeight(20)

            action_layout.addStretch()
            action_layout.addWidget(action_button)
            action_layout.addStretch()
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_widget.setLayout(action_layout)

            self.table_widget.setItem(row_position, 0, name_item)
            self.table_widget.setItem(row_position, 1, totp_item)
            self.table_widget.setItem(row_position, 2, time_item)
            self.table_widget.setCellWidget(row_position, 3, action_widget)
            self.table_widget.setRowHeight(row_position, 40)
            
            self.table_widget.resizeColumnsToContents()
            self.table_widget.verticalHeader().setHidden(True)
            self.table_widget.cellDoubleClicked.connect(self.copy_to_clipboard)
        except binascii.Error:
            QMessageBox.warning(self, "Error", f"Invalid secret for {name}. Please check the secret and try again.")

    def refresh_totp_codes(self):
        for row in range(self.table_widget.rowCount()):
            if row >= len(self.config_manager.configs):
                break
            name_item = self.table_widget.item(row, 0)
            totp_item = self.table_widget.item(row, 1)
            time_item = self.table_widget.item(row, 2)
            if name_item and totp_item and time_item:
                config = self.config_manager.configs[row]
                try:
                    totp = pyotp.TOTP(config["secret"])
                    code = totp.now()
                    time_remaining = totp.interval - time.time() % totp.interval + 1
                    totp_item.setText(f"{code}")
                    time_item.setText(str(int(time_remaining)))
                except binascii.Error:
                    totp_item.setText("Invalid secret")
                    time_item.setText("")

    def copy_to_clipboard(self, row):
        self.copy_row = row
        self.copy_timer.start(300)  # 300ms 防抖时间
        
    def perform_copy(self):
        if self.copy_row is not None:
            config = self.config_manager.configs[self.copy_row]
            totp = pyotp.TOTP(config["secret"])
            code = totp.now()
            pyperclip.copy(f"{config['prefix']}{code}{config['suffix']}")
            self.show_notification(f"Copied: {config['prefix']}{code}{config['suffix']}")
            self.copy_row = None
            self.table_widget.clearSelection()  # 取消选择，防止重复触发双击事件

    def show_notification(self, message):
        self.tray_icon.showMessage("aidex", message, self.icon, 2000)

    def show_config_dialog(self, name="", secret="", prefix="", suffix="", row=None, is_new=False):
        config_dialog = ConfigDialog(self, name, secret, prefix, suffix, row, is_new)
        if config_dialog.exec_() == QDialog.Accepted:
            name, secret, prefix, suffix, is_delete = config_dialog.get_data()
            secret = correct_secret_padding(secret)
            if is_delete:
                self.config_manager.delete_config(row)
            elif is_new:
                self.config_manager.add_config(name, secret, prefix, suffix)
            else:
                self.config_manager.update_config(row, name, secret, prefix, suffix)
            self.load_totp_configs()
        apply_stylesheet(QApplication.instance(), theme='dark_teal.xml')
    
    def update_data_model(self):
        new_configs = []
        for row in range(self.table_widget.rowCount()):
            name_item = self.table_widget.item(row, 0)
            if name_item:
                name = name_item.text()
                for config in self.config_manager.configs:
                    if config['name'] == name:
                        new_configs.append(config)
                        break
        self.config_manager.configs = new_configs
        self.config_manager.save_config()

        for row in range(self.table_widget.rowCount()):
            name_item = self.table_widget.item(row, 0)
            if name_item:
                name = name_item.text()
                config = next((c for c in self.config_manager.configs if c['name'] == name), None)
                if config:
                    self.create_action_button(row, config["name"], config["secret"], config["prefix"], config["suffix"])
    
    def create_action_button(self, row, name, secret, prefix, suffix):
        action_widget = QWidget(self)
        action_layout = QHBoxLayout(action_widget)
        action_button = QPushButton("≡", self)
        action_button.clicked.connect(lambda _, row=row: self.show_config_dialog(name, secret, prefix, suffix, row))
        action_button.setFixedWidth(30)
        action_button.setFixedHeight(20)

        action_layout.addStretch()
        action_layout.addWidget(action_button)
        action_layout.addStretch()
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_widget.setLayout(action_layout)

        self.table_widget.setCellWidget(row, 3, action_widget)
        

    def event(self, event):
        if event.type() == QEvent.WindowDeactivate:
            if not any(isinstance(widget, ConfigDialog) and widget.isVisible() for widget in self.findChildren(QWidget)):
                self.hide()
        return super().event(event)


class ConfigDialog(QDialog):
    def __init__(self, parent=None, name="", secret="", prefix="", suffix="", row=None, is_new=False):
        super().__init__(parent)
        self.parent = parent
        self.is_new = is_new
        self.row = row
        self.is_delete = False
        self.setWindowTitle("TOTP Config")
        self.setGeometry(400, 400, 300, 200)

        self.layout = QVBoxLayout(self)

        self.name_edit = QLineEdit(self)
        self.name_edit.setPlaceholderText("Name")
        self.name_edit.setText(name)
        self.name_edit.setStyleSheet("color: white;")
        self.layout.addWidget(self.name_edit)

        self.secret_edit = QLineEdit(self)
        self.secret_edit.setPlaceholderText("Secret")
        self.secret_edit.setText(secret)
        self.secret_edit.setStyleSheet("color: white;")
        self.layout.addWidget(self.secret_edit)

        self.prefix_edit = QLineEdit(self)
        self.prefix_edit.setPlaceholderText("Password Prefix")
        self.prefix_edit.setText(prefix)
        self.prefix_edit.setStyleSheet("color: white;")
        self.layout.addWidget(self.prefix_edit)

        self.suffix_edit = QLineEdit(self)
        self.suffix_edit.setPlaceholderText("Password Suffix")
        self.suffix_edit.setText(suffix)
        self.suffix_edit.setStyleSheet("color: white;")
        self.layout.addWidget(self.suffix_edit)

        self.button_layout = QHBoxLayout()

        self.save_button = QPushButton("Save", self)
        self.save_button.clicked.connect(self.save)
        self.button_layout.addWidget(self.save_button)

        if not is_new:
            self.delete_button = QPushButton("Delete", self)
            self.delete_button.clicked.connect(self.delete)
            self.button_layout.addWidget(self.delete_button)

        self.layout.addLayout(self.button_layout)

    def save(self):
        secret = correct_secret_padding(self.secret_edit.text())
        if not self.validate_secret(secret):
            return
        self.accept()
        
    
    def validate_secret(self, secret):
        secret = secret.strip().replace(' ', '').upper()
        if not secret:
            self.parent.show_notification("The secret cannot be empty.")
            return False
        try:
            pyotp.TOTP(secret).now()
            return True
        except binascii.Error:
            self.parent.show_notification("The secret provided is not valid.")
            return False

    def get_data(self):
        return (self.name_edit.text(), self.secret_edit.text(), self.prefix_edit.text(), self.suffix_edit.text(), self.is_delete)

    @pyqtSlot()
    def delete(self):
        reply = QMessageBox.question(self, "Delete", "Are you sure you want to delete this config?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.is_delete = True
            self.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("aidex")
    app.setApplicationVersion("1.0")

    if sys.platform == "darwin":
        from AppKit import NSApp
        NSApp.setActivationPolicy_(1)
    elif sys.platform == "win32":
        from ctypes import windll
        windll.shell32.SetCurrentProcessExplicitAppUserModelID('aidex')
    
    apply_stylesheet(app, theme='dark_teal.xml')

    window = MainApp()
    window.hide()
    window.tray_icon.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
