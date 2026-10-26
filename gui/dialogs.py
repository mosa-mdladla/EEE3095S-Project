from PySide6.QtWidgets import QMessageBox

# Dialogs carry their own stylesheet so they look the same wherever they are
# opened from, whatever the page behind them is styled like.
DIALOG_STYLE = """
QMessageBox {
    background-color: #0F172A;
}
QMessageBox QLabel {
    color: #F1F5F9;
    background: transparent;
    font-family: "Segoe UI";
    font-size: 14px;
}
QPushButton {
    background-color: #334155;
    color: #F1F5F9;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 8px 18px;
    min-width: 80px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #475569;
}
QPushButton:default {
    background-color: #2563EB;
    border: none;
}
"""


def _make_box(parent, title, text, icon):
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(icon)
    box.setStyleSheet(DIALOG_STYLE)
    return box


def show_message(parent, title, text, icon=QMessageBox.Icon.Information):
    """Simple popup with an OK button."""
    box = _make_box(parent, title, text, icon)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()


def confirm(parent, title, text, yes_text="Yes"):
    """Ask before a destructive action. Cancel is the default button."""
    box = _make_box(parent, title, text, QMessageBox.Icon.Question)
    yes = box.addButton(yes_text, QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.exec()
    return box.clickedButton() == yes


def ask(parent, title, text, yes_text="Yes", no_text="No"):
    """Two-choice question. The first button is the default."""
    box = _make_box(parent, title, text, QMessageBox.Icon.Warning)
    yes = box.addButton(yes_text, QMessageBox.ButtonRole.AcceptRole)
    no = box.addButton(no_text, QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(yes)
    box.setEscapeButton(no)
    box.exec()
    return box.clickedButton() == yes