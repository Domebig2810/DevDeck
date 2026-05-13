import sys
import qdarktheme
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DevDeck")
    app.setOrganizationName("DevDeck")
    qdarktheme.setup_theme("auto")
    window = MainWindow()
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

# TODO: to bundle:
# pip install pyinstaller
# pyinstaller --name "DevDeck" --windowed main.py