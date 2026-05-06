import sys
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout

def main():
    app = QApplication(sys.argv)

    # Hauptfenster
    window = QWidget()
    window.setWindowTitle("Hello World PyQt")

    # Layout
    layout = QVBoxLayout()

    # Label
    label = QLabel("Hello, World!")
    layout.addWidget(label)

    # Layout setzen
    window.setLayout(layout)

    # Fenster anzeigen
    window.show()

    # Event-Loop starten
    sys.exit(app.exec())

if __name__ == "__main__":
    main()