# aidex

## What's this？
This is a simple TOTP client.
Purely local processing, no network required.
Double-click the verification code to copy it to the clipboard.

![image](https://github.com/user-attachments/assets/f83036b6-97c1-46ec-acb1-82f18c5a2bbb)

## packaging
It can be modified arbitrarily. If you want to package it as an exe file, you can use the following command:
pyinstaller --windowed  --onefile --noconsole  --clean  --debug=all  --icon=icon.ico  --add-data="icon.ico;."  aidex.py
