# aidex

## What's this?
This is a simple TOTP client designed for local processing without any network requirements.

1. Add, edit, delete, and drag to sort TOTP configurations.
2. Generate TOTP verification codes.
3. Double-click the verification code to copy it to the clipboard.

We hope this tool brings you convenience.

## Software Screenshots
![image](https://github.com/user-attachments/assets/04553a25-e479-47d1-96d9-15e8662a4285)


## packaging
It can be modified arbitrarily. If you want to package it as an exe file, you can use the following command:
windows: pyinstaller --windowed  --onefile --noconsole  --clean  --debug=all  --icon=icon.png  --add-data="icon.png;."  aidex.py
macos: pyinstaller aidex.spec


