from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QVBoxLayout)

from gui.background import AnimatedBackground


class StartScreen(AnimatedBackground):
    """Landing page: two name fields and one Connect & Start button."""

    start_requested = Signal(str, str)      # (name for X, name for O)
    close_requested = Signal()              # the Close button was pressed

    def __init__(self):
        super().__init__()

        centre = Qt.AlignmentFlag.AlignCenter

        # Heading
        eyebrow = QLabel("EEE3095S  ·  SERIAL GAME SERVER")
        eyebrow.setObjectName("eyebrow")
        eyebrow.setAlignment(centre)
        font = eyebrow.font()
        font.setPointSize(9)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        eyebrow.setFont(font)

        title = QLabel("Tic Tac Toe")
        title.setObjectName("title")
        title.setAlignment(centre)

        # Card contents
        self.x_input = QLineEdit()
        self.x_input.setPlaceholderText("Name (Player X)")
        self.o_input = QLineEdit()
        self.o_input.setPlaceholderText("Name (Player O)")
        for box in (self.x_input, self.o_input):
            box.setMaxLength(16)
            box.returnPressed.connect(self.on_start)

        vs = QLabel("vs")
        vs.setObjectName("vs")
        vs.setAlignment(centre)

        self.start_button = QPushButton("Connect && Start")
        self.start_button.setObjectName("startButton")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.clicked.connect(self.on_start)

        self.close_button = QPushButton("Close")
        self.close_button.setObjectName("closeButton")
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.clicked.connect(lambda: self.close_requested.emit())

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(26, 26, 26, 26)
        card_layout.setSpacing(14)
        card_layout.addLayout(self.player_header("X"))
        card_layout.addWidget(self.x_input)
        card_layout.addWidget(vs)
        card_layout.addLayout(self.player_header("O"))
        card_layout.addWidget(self.o_input)
        card_layout.addSpacing(6)
        card_layout.addWidget(self.start_button)
        card_layout.addWidget(self.close_button)

        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(440)
        card.setLayout(card_layout)

        footer = QLabel("Plug in the STM32 board, then press Connect & Start.")
        footer.setObjectName("footer")
        footer.setAlignment(centre)

        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addStretch(1)
        layout.addWidget(eyebrow)
        layout.addWidget(title)
        layout.addSpacing(24)
        layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(10)
        layout.addWidget(footer)
        layout.addStretch(1)
        self.setLayout(layout)

        self.apply_styles()

    def player_header(self, mark):
        """Badge + 'Player X' label row."""
        badge = QLabel(mark)
        badge.setObjectName("badgeX" if mark == "X" else "badgeO")
        badge.setFixedSize(32, 32)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name = QLabel(f"Player {mark}")
        name.setObjectName("playerName")

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(badge)
        row.addWidget(name)
        row.addStretch(1)
        return row

    def on_start(self):
        if not self.start_button.isEnabled():
            return
        x_name = self.x_input.text().strip() or "Player X"
        o_name = self.o_input.text().strip() or "Player O"
        self.start_requested.emit(x_name, o_name)

    def set_busy(self, busy):
        """Lock the form while the connection attempt is running."""
        self.start_button.setEnabled(not busy)
        self.x_input.setEnabled(not busy)
        self.o_input.setEnabled(not busy)
        self.start_button.setText("Connecting..." if busy else "Connect && Start")

    def apply_styles(self):
        self.setStyleSheet("""
            QLabel#eyebrow  { color: #8B97A8; }
            QLabel#title    { color: #EBCB8B; font-size: 54px;
                              font-family: "Palatino Linotype", "Georgia", serif; }
            QLabel#footer   { color: #64748B; font-size: 12px; }
            QLabel#vs       { color: #64748B; font-style: italic; }
            QLabel#playerName { color: #E2E8F0; font-weight: bold; font-size: 14px; }

            QLabel#badgeX { background-color: rgba(34, 211, 238, 40);
                            border: 1px solid rgba(34, 211, 238, 130);
                            border-radius: 8px; color: #67E8F9; font-weight: bold; }
            QLabel#badgeO { background-color: rgba(248, 113, 113, 40);
                            border: 1px solid rgba(248, 113, 113, 130);
                            border-radius: 8px; color: #FCA5A5; font-weight: bold; }

            QFrame#card { background-color: rgba(13, 19, 33, 215);
                          border: 1px solid rgba(255, 255, 255, 28);
                          border-radius: 26px; }

            QLineEdit { background-color: rgba(7, 11, 20, 210);
                        border: 1px solid rgba(255, 255, 255, 30);
                        border-radius: 14px; padding: 14px 16px;
                        color: #F1F5F9; font-size: 15px; }
            QLineEdit:focus { border: 1px solid #EBCB8B; }
            QLineEdit:disabled { color: #64748B; }

            QPushButton#startButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #EBCB8B, stop:1 #DB9E45);
                color: #1A1205; border: none; border-radius: 14px;
                padding: 15px; font-size: 16px; font-weight: bold; }
            QPushButton#startButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #F2D79E, stop:1 #E5AA58); }
            QPushButton#startButton:disabled {
                background: rgba(235, 203, 139, 90); color: #3A2F18; }

            QPushButton#closeButton {
                background-color: rgba(7, 11, 20, 150);
                border: 1px solid rgba(255, 255, 255, 38);
                border-radius: 14px; padding: 14px;
                color: #CBD5E1; font-size: 16px; font-weight: bold; }
            QPushButton#closeButton:hover {
                background-color: rgba(255, 255, 255, 22); }
        """)