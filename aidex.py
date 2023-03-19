import os
import sys
import json
import time
import subprocess
import pyotp
import threading
import urllib.request
from urllib.error import URLError, HTTPError
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QCheckBox, QFileDialog
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt


CONFIG_FILE = os.path.join(os.path.expanduser('~'), 'AppData', 'config.json')

config = {
    'username': '',
    'password': '',
    'secret': '',
    'public_url':  'https://www.baidu.com',
    'test_url': 'http://172.17.43.53:8080/login',
    'open_vpn_home': os.path.join('C:', 'Program Files', 'OpenVPN'),
    'auto_flag': False
}

tray = reconnect_lock = None


# 用于发送系统通知的函数
def send_notification(message):
    tray.showMessage(
        'aidex',
        message,
        QSystemTrayIcon.Information,
        3000
    )


class ConfigDialog(QDialog):
    def __init__(self, config, parent=None):
        super(ConfigDialog, self).__init__(parent)
        icon_path = resource_path('favicon.ico')
        self.setWindowIcon(QIcon(icon_path))
        self.config = config
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(' configuration')

        layout = QVBoxLayout()

        labels = ['username', 'password', 'secret', 'test url']
        self.config_keys = ['username', 'password', 'secret', 'test_url']
        self.entries = []
        for i, label_text in enumerate(labels):
            hbox = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(75)
            hbox.addWidget(label)
            entry = QLineEdit()
            hbox.addWidget(entry)
            self.entries.append(entry)
            layout.addLayout(hbox)

        hbox = QHBoxLayout()
        label = QLabel('openVPN path')
        hbox.addWidget(label)
        self.folder_entry = QLineEdit()
        hbox.addWidget(self.folder_entry)
        folder_btn = QPushButton('select folder')
        folder_btn.clicked.connect(self.choose_directory)
        hbox.addWidget(folder_btn)
        layout.addLayout(hbox)

        self.auto_connect_check = QCheckBox('Auto-connect')
        layout.addWidget(self.auto_connect_check)

        save_button = QPushButton('save')
        save_button.clicked.connect(self.save_config)
        layout.addWidget(save_button)

        self.setLayout(layout)
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                self.config.update(json.load(f))
        for i, entry in enumerate(self.entries):
            entry.setText(self.config.get(
                self.config_keys[i], self.config[self.config_keys[i]]))
        self.folder_entry.setText(self.config.get(
            'open_vpn_home', self.config['open_vpn_home']))
        self.auto_connect_check.setChecked(self.config['auto_flag'])

    def save_config(self):
        # 检查 username 和 test_url 是否为空
        if not self.entries[0].text().strip() or not self.entries[3].text().strip():
            send_notification("username and test_url cannot be empty")
            return

        # 检查 client.ovpn 文件
        ovpn_path = os.path.join(
            self.folder_entry.text(), 'config', 'client.ovpn')

        if not os.path.exists(ovpn_path):
            send_notification("openVPN path is incorrect")
        else:
            # 修改 client.ovpn 文件
            with open(ovpn_path, 'r') as f:
                lines = f.readlines()
            with open(ovpn_path, 'w') as f:
                for line in lines:
                    if line.startswith("auth-user-pass"):
                        f.write("auth-user-pass pass.txt\n")
                    else:
                        f.write(line)
            for key, entry in zip(self.config_keys, self.entries):
                self.config[key] = entry.text()
            self.config['open_vpn_home'] = self.folder_entry.text()
            self.config['auto_flag'] = self.auto_connect_check.isChecked()
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
            send_notification("Configuration successful")
            self.hide()

    def choose_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "select folder")
        if directory:
            self.folder_entry.setText(directory)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


# 点击事件
def on_tray_icon_activated(reason):
    if reason == QSystemTrayIcon.DoubleClick:
        ConfigDialog(config).exec()


# 点击断开
def on_click_disconnect(config):
    config['auto_flag'] = False
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)
    disconnect(config)
    send_notification("Disconnect")


# 点击连接
def on_click_connect():
    global config, reconnect_lock
    if check_connect(config['test_url'], timeout=1):
        send_notification("Connected")
        return
    if not os.path.exists(CONFIG_FILE):
        send_notification("Please complete the configuration first")
        return
    if not check_connect(config['public_url'], timeout=1):
        send_notification("No network connection")
        return
    send_notification("trying to connect")
    reconnect_thread_instance = threading.Thread(
        target=reconnect, args=(config, reconnect_lock))
    reconnect_thread_instance.daemon = True
    reconnect_thread_instance.start()


# 检查连接
def check_connect(url: str, timeout=1):
    try:
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/49.0.2')]
        opener.open(url, timeout=timeout)
        return True
    except (URLError, HTTPError):
        return False

# 重连
def reconnect(config, reconnect_lock):
    with reconnect_lock:
        open_vpn_home = config['open_vpn_home']
        username = config['username']
        password = config['password'] if config['password'] else ''
        secret = config['secret']
        totp = pyotp.TOTP(secret)
        flag = False

        while check_connect(config['public_url']) and not check_connect(config['test_url']):
            flag = True
            disconnect(config)
            time.sleep(5)
            otp = totp.now() if secret else ''
            send_notification(
                f"Hello, {username}\nTrying to connect with {password}{otp}")
            with open(os.path.join(open_vpn_home, "config", "pass.txt"), "w") as f:
                f.write(f"{username}\n{password}{otp}\n")
            connect(config)
            time.sleep(10)
        if flag:
            send_notification('Connection successful')


# 连接
def connect(config):
    open_vpn_home = config['open_vpn_home']
    connect_cmd = f'''start "" "{open_vpn_home}\\bin\\openvpn-gui.exe" --connect client.ovpn'''
    subprocess.run(connect_cmd, shell=True)


# 断开连接
def disconnect(config):
    open_vpn_home = config['open_vpn_home']
    disconnect_cmd = f'''start "" "{open_vpn_home}\\bin\\openvpn-gui.exe" --command disconnect_all'''
    subprocess.run(disconnect_cmd, shell=True)


# 自动连接线程
def auto_connection():
    while True:
        global config, reconnect_lock
        if config['auto_flag']:
            reconnect(config, reconnect_lock)
        time.sleep(30)


def main():
    app = QApplication([])
    app.setApplicationDisplayName('aidex')

    global tray, config, reconnect_lock

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            config.update(json.load(f))

    reconnect_lock = threading.Lock()

    icon_path = resource_path('favicon.ico')
    tray = QSystemTrayIcon(QIcon(icon_path), parent=None)
    tray.activated.connect(on_tray_icon_activated)
    tray.show()

    menu = QMenu()

    edit_config_action = QAction('configuration')
    edit_config_action.triggered.connect(lambda: ConfigDialog(config).exec())
    menu.addAction(edit_config_action)

    disconnect_action = QAction('disconnect')
    disconnect_action.triggered.connect(lambda: on_click_disconnect(config))
    menu.addAction(disconnect_action)

    connect_action = QAction('connect')
    connect_action.triggered.connect(lambda: on_click_connect())
    menu.addAction(connect_action)

    exit_action = QAction('exit aide')
    exit_action.triggered.connect(lambda: app.quit())
    menu.addAction(exit_action)

    tray.setContextMenu(menu)

    # 自动连接线程
    auto_connection_thread = threading.Thread(target=auto_connection)
    auto_connection_thread.daemon = True
    auto_connection_thread.start()

    app.exec()


def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)


if __name__ == '__main__':
    main()
    
