import sys
from PySide6.QtWidgets import QApplication

import os
os.environ["GLOG_minloglevel"] = "2" 

from app.launcher import LauncherWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SignVision")

    window = LauncherWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
