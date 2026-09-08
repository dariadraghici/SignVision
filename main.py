import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

try:
    from app.launcher import LauncherWindow
except ImportError:
    from launcher import LauncherWindow


def resource_path(relative_path: str) -> str:
    """Resolve a path to a bundled resource, checking every location it
    could plausibly live in: next to the PyInstaller bundle, next to this
    file, and the current working directory. Returns the first match, or
    the first candidate (for a clear error message) if none exist."""
    candidates = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(os.path.join(meipass, relative_path))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(script_dir, relative_path))

    candidates.append(os.path.join(os.getcwd(), relative_path))

    for path in candidates:
        if os.path.exists(path):
            return path

    print(f"[icon] WARNING: could not find '{relative_path}' in any of: {candidates}")
    return candidates[0]


def set_windows_app_user_model_id():
    """Give the app its own identity in the Windows shell so the taskbar
    uses our icon instead of falling back to the python.exe icon (this only
    matters when running from source with `python main.py`; a PyInstaller
    build already has its own .exe and icon)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SignVision.App")
    except Exception:
        pass


def main():
    set_windows_app_user_model_id()

    app = QApplication(sys.argv)
    app.setApplicationName("SignVision")

    icon_path = resource_path("app_icon.ico")
    app_icon = QIcon(icon_path)
    if app_icon.isNull():
        print(f"[icon] WARNING: found '{icon_path}' but Qt could not load it as an icon.")
    else:
        app.setWindowIcon(app_icon)

    window = LauncherWindow()
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
