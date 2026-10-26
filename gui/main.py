
from PySide6.QtWidgets import (QApplication,QWidget,QPushButton,QLabel,QVBoxLayout,QHBoxLayout,QGridLayout,QMessageBox,QFrame)
from PySide6.QtCore import Qt
from gui.serial_worker import SerialWorker


class GameWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Serial Game Server")
        self.setMinimumSize(480, 600)
        self.resize(540,680)

        self.worker = None
        self.connected = False
        self.game_active = False
        self.pending = False
        self.last_command = ""

        self.board = ["."] * 9
        self.board_buttons = []

        #LABELLING
        self.title_label = QLabel("TIC TAC TOE")
        self.title_label.setObjectName("title")
        self.subtitle_label = QLabel("STM32 Serial Game Server")
        self.subtitle_label.setObjectName("subtitle")


        self.status_label = QLabel("Not connected to STM32")
        self.status_label.setObjectName("status")

        self.next_player_label = QLabel("Next player: -")
        self.next_player_label.setObjectName("nextPlayer")

        status_layout = QVBoxLayout()
        status_layout.setSpacing(8)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.next_player_label)

        status_frame = QFrame()
        status_frame.setObjectName("statusFrame")
        status_frame.setLayout(status_layout)

        board_layout = QGridLayout()
        board_layout.setSpacing(8)
        board_layout.setContentsMargins(0,0,0,0)


        for index in range(9):
            button = QPushButton("")
            button.setObjectName("cell")
            button.setMinimumSize(90, 90)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            button.clicked.connect(
                lambda checked=False, cell=index: self.make_move(cell)
            )

            self.board_buttons.append(button)

            row = index // 3
            column = index % 3
            board_layout.addWidget(button, row, column)

        board_frame = QFrame()
        board_frame.setObjectName("boardFrame")
        board_frame.setLayout(board_layout)

        # Game controls
        self.new_game_button = QPushButton("New Game")
        self.new_game_button.setObjectName("primaryButton")

        self.state_button = QPushButton("Sync with STM32")
        self.state_button.setObjectName("secondaryButton")

        self.end_game_button = QPushButton("End Game")
        self.end_game_button.setObjectName("dangerButton")

        self.connect_button = QPushButton("Connect to STM32")
        self.connect_button.setObjectName("connectButton")

        controls_layout = QGridLayout()
        controls_layout.setSpacing(10)

        controls_layout.addWidget(self.new_game_button, 0, 0)
        controls_layout.addWidget(self.state_button, 0, 1)
        controls_layout.addWidget(self.connect_button, 1, 0)
        controls_layout.addWidget(self.end_game_button, 1, 1)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.subtitle_label)
        main_layout.addWidget(status_frame)
        main_layout.addWidget(board_frame, 1)
        main_layout.addLayout(controls_layout)

        self.setLayout(main_layout)

        
        self.connect_button.clicked.connect(self.connect_to_stm32)
        self.new_game_button.clicked.connect(self.start_new_game)
        self.state_button.clicked.connect(self.get_state)
        self.end_game_button.clicked.connect(self.end_game)

        self.apply_styles()
        self.update_controls()
        self.refresh_board()

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0F172A;
                color: #F1F5F9;
                font-family: "Segoe UI";
                font-size: 14px;
            }

            QLabel#title {
                font-size: 27px;
                font-weight: bold;
                color: #F8FAFC;
            }

            QLabel#subtitle {
                font-size: 13px;
                color: #94A3B8;
                padding-bottom: 4px;
            }

            QFrame#statusFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 12px;
            }

            QLabel#status {
                background-color: transparent;
                color: #E2E8F0;
                font-size: 15px;
                font-weight: bold;
            }

            QLabel#nextPlayer {
                background-color: transparent;
                color: #94A3B8;
                font-size: 13px;
            }

            QFrame#boardFrame {
                background-color: #172033;
                border: 1px solid #334155;
                border-radius: 14px;
                padding: 12px;
            }

            QPushButton#cell {
                background-color: #1E293B;
                border: 2px solid #334155;
                border-radius: 10px;
                color: #F8FAFC;
                font-size: 38px;
                font-weight: bold;
            }

            QPushButton#cell:hover:enabled {
                background-color: #26364F;
                border: 2px solid #60A5FA;
            }

            QPushButton#cell:disabled {
                color: #F8FAFC;
            }

            QPushButton#primaryButton {
                background-color: #2563EB;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
            }

            QPushButton#primaryButton:hover:enabled {
                background-color: #3B82F6;
            }

            QPushButton#secondaryButton,
            QPushButton#connectButton {
                background-color: #334155;
                color: #F1F5F9;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
            }

            QPushButton#secondaryButton:hover:enabled,
            QPushButton#connectButton:hover:enabled {
                background-color: #475569;
            }

            QPushButton#dangerButton {
                background-color: #7F1D1D;
                color: #FEE2E2;
                border: 1px solid #991B1B;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
            }

            QPushButton#dangerButton:hover:enabled {
                background-color: #991B1B;
            }

            QPushButton:disabled {
                color: #64748B;
                background-color: #1E293B;
                border-color: #334155;
            }
        """)
    
    
    def connect_to_stm32(self):
        if self.connected:
            return

        if self.worker is not None and self.worker.isRunning():
            return

        self.worker = SerialWorker(port="COM5")

        self.worker.new_connection.connect(self.update_connection)
        self.worker.response_received.connect(self.show_response)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.finished.connect(self.update_controls)

        self.status_label.setText("Connecting to STM32...")
        self.pending = True
        self.last_command = "CONNECT"
        self.update_controls()

        self.worker.start()
        self.worker.send_command("CONNECT")

    def start_new_game(self):
        if not self.connected or self.pending:
            return

        self.pending = True
        self.last_command = "NEW"
        self.status_label.setText("Starting a new game...")
        self.update_controls()

        self.worker.send_command("NEW")

    def get_state(self):
        if not self.connected or self.pending:
            return

        self.pending = True
        self.last_command = "STATE"
        self.status_label.setText("Getting game state...")
        self.update_controls()

        self.worker.send_command("STATE")

    
    def make_move(self, index):

        if not self.connected or not self.game_active or self.pending:
            return

        if self.board[index] != ".":
            return

        x_count = self.board.count("X")
        o_count = self.board.count("O")

        if x_count == o_count:
            player = "X"
        else:
            player = "O"

        self.pending = True
        self.last_command = "MOVE"
        self.status_label.setText(f"Sending Player {player}'s move...")
        self.update_controls()
        self.worker.send_command("MOVE", f"{player},{index}")


    def end_game(self):
        if not self.connected or not self.game_active or self.pending:
            return

        self.pending = True
        self.last_command = "RESIGN"
        self.status_label.setText("Ending game...")
        self.update_controls()

        self.worker.send_command("RESIGN")

    def update_connection(self, connected):
        self.connected = connected

        if connected:
            self.status_label.setText("Connected to STM32")
        else:
            self.game_active = False
            self.status_label.setText("Disconnected from STM32")

        self.update_controls()

    def show_response(self, command, arguments):
        if command == "OK" and self.last_command == "CONNECT":
            self.connected = True
            self.status_label.setText("Connected to STM32")

        elif command == "OK" and self.last_command == "NEW":
            self.board = ["."] * 9
            self.game_active = True
            self.status_label.setText("New game started")

        elif command == "OK" and arguments == "GAMEOVER":
            self.game_active = False
            self.board = ["."] * 9
            self.status_label.setText("Game ended")

        elif command == "BOARD":
            if len(arguments) == 9:
                self.board = list(arguments)

                if self.last_command == "NEW":
                    self.game_active = True

                self.status_label.setText("Board updated")

        elif command == "WIN":
            parts = arguments.split(",", 1)

            if len(parts) == 2 and len(parts[1]) == 9:
                winner, final_board = parts

                self.board = list(final_board)
                self.game_active = False
                self.status_label.setText(f"Player {winner} wins!")

                QMessageBox.information(
                    self,
                    "Game Over",
                    f"Player {winner} wins!",
                )
            else:
                self.status_label.setText(
                    f"Winner response received: {arguments}"
                )
                self.game_active = False

        elif command == "DRAW":
            if len(arguments) == 9:
                self.board = list(arguments)

            self.game_active = False
            self.status_label.setText("Game ended in a draw")

            QMessageBox.information(self,"Game Over","The game ended in a draw!", )

        elif command == "NACK":
           self.status_label.setText(f"Move or command rejected: {arguments}" )

        else:
            self.status_label.setText( f"Response: {command} {arguments}" )
        self.pending = False
        self.refresh_board()
        self.update_controls()

    def show_error(self, message):
        self.status_label.setText(f"Error: {message}")

        self.pending = False
        self.update_controls()

    def refresh_board(self):
        for index, value in enumerate(self.board):
            button = self.board_buttons[index]

            if value == ".":
                button.setText("")
                button.setStyleSheet("")
            else:
                button.setText(value)

                if value == "X":
                    button.setStyleSheet("""
                        QPushButton {
                            color: #60A5FA;
                            font-size: 38px;
                            font-weight: bold;
                        }
                    """)
                else:
                    button.setStyleSheet("""
                        QPushButton {
                            color: #F87171;
                            font-size: 38px;
                            font-weight: bold;
                        }
                    """)
        if self.game_active:
            x_count = self.board.count("X")
            o_count = self.board.count("O")

            if x_count == o_count:
                self.next_player_label.setText("Next player: X")
            else:
                self.next_player_label.setText("Next player: O")
        else:
            self.next_player_label.setText("Next player: -")

        self.update_board_buttons()

    def update_board_buttons(self):
        for index, button in enumerate(self.board_buttons):
            can_play = (self.connected and self.game_active and not self.pending and self.board[index] == ".")

            button.setEnabled(can_play)

    def update_controls(self):
        self.connect_button.setEnabled(not self.connected and(self.worker is None or not self.worker.isRunning()))
        self.new_game_button.setEnabled(self.connected and not self.pending)

        self.state_button.setEnabled( self.connected and not self.pending )

        self.end_game_button.setEnabled(self.connected and self.game_active and not self.pending)

        self.update_board_buttons()

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()

        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    window = GameWindow()
    window.show()
    app.exec()
