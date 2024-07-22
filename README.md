# aidex

## What's this？
This is a simple TOTP client.
Purely local processing, no network required.
Double-click the verification code to copy it to the clipboard.

<img width="239" alt="Main pop-up window" src="https://github.com/user-attachments/assets/82fe6c86-39f0-431d-9b75-6bbb4f449bd0">


## packaging
It can be modified arbitrarily. If you want to package it as an exe file, you can use the following command:
pyinstaller --windowed  --onefile --noconsole  --clean  --debug=all  --icon=icon.ico  --add-data="icon.ico;."  aidex.py
