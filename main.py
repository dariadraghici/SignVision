import sys
from PySide6.QtWidgets import QApplication

from app.launcher import LauncherWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SignVision")

    window = LauncherWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
