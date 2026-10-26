from collections import deque

from PySide6.QtWidgets import (QApplication, QPushButton, QLabel,
                               QVBoxLayout, QHBoxLayout, QStackedWidget,
                               QMessageBox)
from PySide6.QtCore import Qt, Signal, QTimer

from gui.background import AnimatedBackground
from gui.dialogs import show_message, confirm, ask
from gui.game_widgets import BoardWidget, PlayerCard
from gui.serial_worker import SerialWorker
from gui.start_screen import StartScreen

PORT = "COM5"
POLL_MS = 1500                 # how often the board is checked while connected
EMPTY_BOARD = "." * 9

# Plain-English versions of the server's NACK codes
NACK_TEXT = {
    "OCCUPIED": "That square is already taken.",
    "NOTURN": "It isn't that player's turn.",
    "RANGE": "That square doesn't exist.",
    "NOGAME": "There is no game in progress.",
    "GAMEACTIVE": "A game is still running. End it first.",
    "BADARG": "The board didn't understand that move.",
    "BADCMD": "The board didn't recognise that command.",
    "BADFRAME": "The message was damaged on its way to the board. Please try again.",
    "BADSEQ": "The message was damaged on its way to the board. Please try again.",
    "BADCRC": "The message was damaged on its way to the board. Please try again.",
}

# After these the GUI re-reads the board, in case it is out of step with it
RESYNC_AFTER = ("OCCUPIED", "NOTURN", "RANGE", "BADARG")


def failure_text(kind):
    """(title, message) shown when the STM32 can't be reached."""
    if kind == "port_busy":
        return ("Connection already in use",
                f"Another program is using {PORT}.\n\n"
                "Close any serial monitor or debugger that is connected to "
                "the board, then try again.")
    if kind == "timeout":
        return ("STM32 not responding",
                "The STM32 board is connected but isn't responding.\n\n"
                "Check that it is switched on and connected properly, "
                "then try again.")
    if kind in ("protocol", "sequence", "nack"):
        return ("Connection problem",
                "The STM32 sent a reply that couldn't be understood.\n\n"
                "Check the connection and try again.")
    return ("STM32 not connected",
            "The STM32 board is not connected.\n\n"
            "Please check that it is plugged in properly, then try again.")


class GameWindow(AnimatedBackground):
    connection_ready = Signal()          # first game is running on the board
    connection_failed = Signal(str, str) # (title, message): could not connect
    left_game = Signal()                 # go back to the start page

    def __init__(self):
        super().__init__()

        self.setMinimumSize(480, 620)

        self.worker = None
        self.connected = False
        self.connecting = False          # first CONNECT + NEW after the start page
        self.reconnecting = False        # CONNECT + NEW + replay after a loss
        self.lost = False                # the board vanished / was reset
        self.game_active = False         # server is IN_PROGRESS
        self.game_over = False           # server is GAME_OVER
        self.pending = False             # a button-triggered command is running

        # Commands sent and not yet answered, oldest first. The worker answers
        # in the same order, so each reply belongs to inflight.popleft().
        self.inflight = deque()
        self.flow = None                 # "new" or "end": what follows a RESIGN
        self.swap_on_new = False         # next round: the winner plays X and starts
        self.resume_active = False       # a game was running when the link dropped
        self.replay_moves = deque()      # moves to replay onto a reset board

        # How the last game finished: None, ("win", "X"), ("draw",) or "ended"
        self.result = None
        self.round_number = 0

        # Display-only names from the start screen (the STM32 only knows X and O)
        self.player_names = {"X": "Player X", "O": "Player O"}

        self.board = ["."] * 9

        # ---------- header ----------
        self.title_label = QLabel("Tic Tac Toe")
        self.title_label.setObjectName("title")

        self.conn_label = QLabel(f"●  {PORT}")
        self.conn_label.setObjectName("connLabel")

        self.sync_button = QPushButton("↻")
        self.sync_button.setObjectName("smallButton")
        self.sync_button.setToolTip("Re-read the board from the STM32")
        self.sync_button.setFixedWidth(40)

        self.disconnect_button = QPushButton("Change players")
        self.disconnect_button.setObjectName("smallButton")

        centre_v = Qt.AlignmentFlag.AlignVCenter
        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self.title_label, 1)
        header.addWidget(self.conn_label, 0, centre_v)
        header.addWidget(self.sync_button, 0, centre_v)
        header.addWidget(self.disconnect_button, 0, centre_v)

        # ---------- player cards ----------
        self.card_x = PlayerCard("X")
        self.card_o = PlayerCard("O")

        vs = QLabel("vs")
        vs.setObjectName("vs")
        vs.setAlignment(Qt.AlignmentFlag.AlignCenter)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(0)
        cards_row.addWidget(self.card_x, 1)
        cards_row.addWidget(vs)
        cards_row.addWidget(self.card_o, 1)

        # ---------- board ----------
        self.board_widget = BoardWidget()
        self.board_buttons = self.board_widget.cells
        self.board_widget.cell_clicked.connect(self.make_move)

        # ---------- action buttons (the same two in every state) ----------
        self.new_game_button = QPushButton("New game")
        self.new_game_button.setObjectName("primaryButton")
        self.end_game_button = QPushButton("End game")
        self.end_game_button.setObjectName("dangerButton")

        actions = QHBoxLayout()
        actions.setSpacing(12)
        actions.addWidget(self.new_game_button)
        actions.addWidget(self.end_game_button)

        # ---------- footer ----------
        self.round_label = QLabel("")
        self.round_label.setObjectName("roundLabel")
        self.round_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.status_label = QLabel("Not connected to STM32")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)

        # ---------- main layout ----------
        column = QVBoxLayout()
        column.setContentsMargins(24, 22, 24, 16)
        column.setSpacing(12)
        column.addLayout(header)
        column.addLayout(cards_row)
        column.addWidget(self.board_widget, 1)
        column.addLayout(actions)
        column.addWidget(self.round_label)
        column.addWidget(self.status_label)
        self.setLayout(column)

        for button in self.findChildren(QPushButton):
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        # ---------- signals ----------
        self.sync_button.clicked.connect(self.get_state)
        self.disconnect_button.clicked.connect(self.end_game)
        self.new_game_button.clicked.connect(self.new_game)
        self.end_game_button.clicked.connect(self.end_game)

        # Checks the board now and then, so a reset or unplugged cable is
        # noticed even when nobody is clicking
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(POLL_MS)
        self.poll_timer.timeout.connect(self.poll_server)
        self.poll_timer.start()

        self.apply_styles()
        self.update_controls()
        self.refresh_board()

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                color: #F1F5F9;
                font-family: "Segoe UI";
                font-size: 14px;
            }

            QLabel#title {
                color: #EBCB8B;
                font-size: 34px;
                font-family: "Palatino Linotype", "Georgia", serif;
            }

            QLabel#connLabel {
                color: #34D399;
                font-size: 12px;
                font-weight: bold;
                padding-right: 4px;
            }

            QLabel#vs {
                color: #64748B;
                font-style: italic;
                padding: 0px 10px;
            }

            QLabel#cardName {
                color: #F1F5F9;
                font-size: 15px;
                font-weight: bold;
            }

            QLabel#cardSub {
                color: #94A3B8;
                font-size: 12px;
            }

            QLabel#badgeX {
                background-color: rgba(34, 211, 238, 40);
                border: 1px solid rgba(34, 211, 238, 130);
                border-radius: 8px;
                color: #67E8F9;
                font-weight: bold;
            }

            QLabel#badgeO {
                background-color: rgba(248, 113, 113, 40);
                border: 1px solid rgba(248, 113, 113, 130);
                border-radius: 8px;
                color: #FCA5A5;
                font-weight: bold;
            }

            QLabel#roundLabel {
                color: #64748B;
                font-size: 12px;
            }

            QLabel#status {
                color: #8B97A8;
                font-size: 12px;
            }

            QPushButton#primaryButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #EBCB8B, stop:1 #DB9E45);
                color: #1A1205;
                border: none;
                border-radius: 14px;
                padding: 14px;
                font-size: 15px;
                font-weight: bold;
            }

            QPushButton#primaryButton:hover:enabled {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #F2D79E, stop:1 #E5AA58);
            }

            QPushButton#primaryButton:disabled {
                background: rgba(235, 203, 139, 90);
                color: #3A2F18;
            }

            QPushButton#dangerButton {
                background-color: rgba(13, 19, 33, 170);
                color: #FCA5A5;
                border: 1px solid rgba(248, 113, 113, 110);
                border-radius: 14px;
                padding: 14px;
                font-size: 15px;
                font-weight: bold;
            }

            QPushButton#dangerButton:hover:enabled {
                background-color: rgba(248, 113, 113, 35);
            }

            QPushButton#smallButton {
                background-color: rgba(13, 19, 33, 170);
                color: #F1F5F9;
                border: 1px solid rgba(255, 255, 255, 38);
                border-radius: 12px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: bold;
            }

            QPushButton#smallButton:hover:enabled {
                background-color: rgba(255, 255, 255, 22);
            }

            QPushButton#dangerButton:disabled,
            QPushButton#smallButton:disabled {
                color: #64748B;
                background-color: rgba(13, 19, 33, 120);
                border: 1px solid rgba(255, 255, 255, 18);
            }
        """)

    # ------------------------------------------------------------------
    # Names
    # ------------------------------------------------------------------
    def set_players(self, x_name, o_name):
        self.player_names = {"X": x_name, "O": o_name}
        self.swap_on_new = False
        self.refresh_board()

    # ------------------------------------------------------------------
    # Worker / sending
    # ------------------------------------------------------------------
    def can_act(self):
        """True when a button press may send something to the board."""
        return (self.connected and not self.pending and not self.lost
                and not self.connecting and not self.reconnecting)

    def start_worker(self):
        worker = SerialWorker(port=PORT)
        # Replies from an old worker are ignored (see on_response / on_error)
        worker.response_received.connect(
            lambda command, arguments, w=worker: self.on_response(w, command, arguments))
        worker.error_occurred.connect(
            lambda kind, message, w=worker: self.on_error(w, kind, message))
        self.worker = worker
        worker.start()

    def drop_worker(self):
        worker, self.worker = self.worker, None
        self.inflight.clear()
        if worker is not None:
            worker.stop()
            worker.wait()

    def send(self, command, arguments="-", status="", label=None):
        """Queue a command. `label` names it in `inflight` (e.g. POLL, SYNC)."""
        self.inflight.append(label or command)
        if label != "POLL":                 # background checks stay invisible
            self.pending = True
            if status:
                self.status_label.setText(status)
            self.update_controls()
        self.worker.send_command(command, arguments)

    def finish_step(self):
        self.pending = False
        self.refresh_board()
        self.update_controls()

    # ------------------------------------------------------------------
    # Connecting
    # ------------------------------------------------------------------
    def reset_game_view(self):
        self.board = ["."] * 9
        self.game_active = False
        self.game_over = False
        self.result = None
        self.round_number = 0
        self.flow = None
        self.swap_on_new = False
        self.resume_active = False
        self.replay_moves.clear()

    def connect_to_stm32(self):
        """Open the port and send CONNECT. Returns False if it could not start."""
        if self.connected or self.connecting or self.worker is not None:
            return False

        self.reset_game_view()
        self.connecting = True
        self.status_label.setText("Connecting to STM32...")
        self.start_worker()
        self.send("CONNECT")
        self.refresh_board()
        return True

    def fail_connection(self, kind):
        """The port would not open, or the board did not answer properly."""
        self.drop_worker()
        self.connecting = False
        self.connected = False
        self.pending = False
        self.status_label.setText("Not connected to STM32")
        self.refresh_board()
        self.update_controls()
        title, text = failure_text(kind)
        self.connection_failed.emit(title, text)

    def finish_disconnect(self):
        """Close the port and go back to the start page."""
        self.drop_worker()
        self.connected = False
        self.connecting = False
        self.reconnecting = False
        self.lost = False
        self.pending = False
        self.reset_game_view()
        self.status_label.setText("Not connected to STM32")
        self.refresh_board()
        self.update_controls()
        self.left_game.emit()

    # ------------------------------------------------------------------
    # The board vanished (reset button, unplugged cable, no answer)
    # ------------------------------------------------------------------
    def server_lost(self, kind, retry=False):
        if self.lost:
            return

        self.lost = True
        if not retry:
            self.resume_active = self.game_active
        self.game_active = False
        self.flow = None
        self.drop_worker()
        self.connected = False
        self.connecting = False
        self.reconnecting = False
        self.pending = False
        self.status_label.setText("STM32 disconnected")
        self.refresh_board()
        self.update_controls()

        if retry:
            title = "Still can't reach the STM32"
            text = failure_text(kind)[1]
        else:
            title = "STM32 disconnected"
            text = ("The connection to the STM32 board was lost. It may have "
                    "been unplugged or reset.")

        if self.resume_active:
            text += ("\n\nYour game has been kept. Reconnect to carry on "
                     "from where you left off, or go back to the main menu.")
        else:
            text += "\n\nReconnect to keep playing, or go back to the main menu."

        if ask(self, title, text, "Reconnect", "Main menu"):
            self.begin_reconnect()
        else:
            self.finish_disconnect()

    def begin_reconnect(self):
        self.lost = False
        self.reconnecting = True
        self.status_label.setText("Reconnecting to the STM32...")
        self.start_worker()
        self.send("CONNECT")
        self.refresh_board()

    def start_replay(self):
        """The board has a fresh game: play the saved moves back onto it."""
        xs = [i for i, v in enumerate(self.board) if v == "X"]
        os_ = [i for i, v in enumerate(self.board) if v == "O"]

        self.replay_moves.clear()
        for k in range(max(len(xs), len(os_))):
            if k < len(xs):
                self.replay_moves.append(("X", xs[k]))
            if k < len(os_):
                self.replay_moves.append(("O", os_[k]))

        if self.replay_moves:
            self.send_next_replay()
        else:
            self.finish_reconnect()

    def send_next_replay(self):
        mark, index = self.replay_moves.popleft()
        self.send("MOVE", f"{mark},{index}", "Restoring your game...",
                  label="REPLAY")

    def finish_reconnect(self):
        was_active = self.resume_active
        self.reconnecting = False
        self.connected = True
        self.game_active = was_active
        self.resume_active = False
        self.replay_moves.clear()
        self.status_label.setText(
            "Reconnected. Your game is back." if was_active else "Reconnected.")
        self.finish_step()

    def fail_reconnect(self, kind):
        self.reconnecting = False
        self.server_lost(kind, retry=True)

    # ------------------------------------------------------------------
    # Buttons
    # ------------------------------------------------------------------
    def poll_server(self):
        if (not self.can_act() or self.inflight or self.worker is None):
            return
        self.send("STATE", "-", label="POLL")

    def get_state(self):
        if not self.can_act():
            return
        self.send("STATE", "-", "Getting game state...")

    def make_move(self, index):
        if not self.can_act() or not self.game_active:
            return
        if self.board[index] != ".":
            return

        player = "X" if self.board.count("X") == self.board.count("O") else "O"
        self.send("MOVE", f"{player},{index}",
                  f"Sending {self.player_names[player]}'s move...")

    def new_game(self):
        """New game / Play again: clear the board and start another round."""
        if not self.can_act():
            return

        if self.game_active:
            if not confirm(self, "Start a new game?",
                           "The current game will be abandoned and a new one "
                           "started.", "New game"):
                return
            self.flow = "new"
            self.swap_on_new = False
            self.send("RESIGN", "-", "Ending the current game...")
            return

        # The previous winner starts. The board always lets X go first, so
        # the winner takes the X mark. After a draw the players swap, so the
        # other one opens.
        if isinstance(self.result, tuple) and self.result[0] == "win":
            self.swap_on_new = self.result[1] == "O"
        elif isinstance(self.result, tuple) and self.result[0] == "draw":
            self.swap_on_new = True
        else:
            self.swap_on_new = False
        self.send("NEW", "-", "Starting a new game...")

    def end_game(self):
        """End game / Change players: back to the start screen."""
        if not self.can_act():
            return

        self.flow = "end"
        if self.game_active:
            if not confirm(self, "End game?",
                           "This ends the game and takes you back to the "
                           "start screen.", "End game"):
                self.flow = None
                return
            self.send("RESIGN", "-", "Ending the game...")
        else:
            self.send("DISCONNECT", "-", "Leaving...")

    # ------------------------------------------------------------------
    # Replies
    # ------------------------------------------------------------------
    def on_response(self, worker, command, arguments):
        if worker is not self.worker or self.lost:
            return
        sent = self.inflight.popleft() if self.inflight else ""

        if command == "NACK":
            self.handle_nack(sent, arguments)
        elif sent == "CONNECT" and command == "OK":
            self.connected = True
            if self.reconnecting and not self.resume_active:
                self.finish_reconnect()         # nothing to restore
            else:
                self.send("NEW", "-")           # both start and reconnect
        elif sent == "NEW" and command == "OK":
            self.handle_new_ok()
        elif sent == "REPLAY":
            self.handle_replay(command, arguments)
        elif sent == "MOVE":
            self.handle_move_reply(command, arguments)
        elif sent in ("STATE", "SYNC", "POLL") and command == "BOARD":
            self.handle_board_reply(sent, arguments)
        elif sent == "RESIGN" and command == "OK" and arguments == "GAMEOVER":
            self.game_ended()
        elif sent == "DISCONNECT" and command == "OK":
            self.finish_disconnect()
        elif sent != "POLL":
            self.flow = None
            self.status_label.setText(f"Unexpected reply: {command} {arguments}")
            self.finish_step()

    def on_error(self, worker, kind, message):
        if worker is not self.worker or self.lost:
            return
        sent = self.inflight.popleft() if self.inflight else ""

        if self.connecting:
            self.fail_connection(kind)
        elif self.reconnecting:
            self.fail_reconnect(kind)
        elif self.flow == "end" or sent == "DISCONNECT":
            # The player wants out, so let them go even if the board is gone
            self.finish_disconnect()
        elif kind in ("protocol", "sequence"):
            # A damaged reply: the move may or may not have gone through
            if sent == "POLL":
                return
            if sent == "SYNC":
                self.flow = None
                self.status_label.setText(
                    "Couldn't read the board. Press ↻ to try again.")
                self.finish_step()
                return
            self.flow = None
            self.status_label.setText(
                "The board's reply was damaged. Checking the board...")
            self.send("STATE", "-", label="SYNC")
        else:
            # no answer / cable pulled
            self.server_lost(kind)

    def handle_new_ok(self):
        if self.reconnecting:
            self.start_replay()
            return

        if self.swap_on_new:
            self.player_names = {"X": self.player_names["O"],
                                 "O": self.player_names["X"]}
        self.swap_on_new = False

        self.board = ["."] * 9
        self.game_active = True
        self.game_over = False
        self.result = None
        self.flow = None
        self.round_number += 1
        self.status_label.setText(
            f"Round {self.round_number}: {self.player_names['X']} starts")

        was_connecting = self.connecting
        self.connecting = False
        self.finish_step()

        if was_connecting:
            self.connection_ready.emit()

    def handle_replay(self, command, arguments):
        if command != "BOARD" or len(arguments) != 9:
            self.fail_reconnect("nack")
        elif self.replay_moves:
            self.send_next_replay()
        else:
            self.board = list(arguments)
            self.finish_reconnect()

    def handle_move_reply(self, command, arguments):
        popup = None

        if command == "BOARD" and len(arguments) == 9:
            self.board = list(arguments)
            self.status_label.setText("Board updated")

        elif command == "WIN":
            parts = arguments.split(",", 1)
            self.game_active = False
            self.game_over = True

            if len(parts) == 2 and len(parts[1]) == 9:
                winner, final_board = parts
                winner_name = self.player_names.get(winner, winner)
                self.board = list(final_board)
                self.result = ("win", winner)
                self.status_label.setText(f"{winner_name} ({winner}) wins!")
                popup = ("Game Over", f"{winner_name} ({winner}) wins!")
            else:
                self.status_label.setText(f"Winner response received: {arguments}")

        elif command == "DRAW":
            if len(arguments) == 9:
                self.board = list(arguments)
            self.game_active = False
            self.game_over = True
            self.result = ("draw",)
            self.status_label.setText("Game ended in a draw")
            popup = ("Game Over", "The game ended in a draw!")

        else:
            self.status_label.setText(f"Unexpected reply: {command} {arguments}")

        self.finish_step()

        if popup is not None:
            # Give the last mark time to finish being written before the
            # dialog covers the board
            QTimer.singleShot(
                1100, lambda p=popup: self.show_result_popup(p[0], p[1]))

    def show_result_popup(self, title, text):
        # Skip it if the player already moved on (Play again / End game)
        if self.game_over and self.connected and not self.lost:
            show_message(self, title, text)

    def handle_board_reply(self, sent, arguments):
        """STATE answers: the manual refresh, a re-sync and the background check."""
        if len(arguments) == 9 and self.game_active:
            if arguments != "".join(self.board):
                if arguments == EMPTY_BOARD:
                    # The board has an empty board but we have moves: it was reset
                    self.server_lost("reset")
                    return
                self.board = list(arguments)

        if sent == "STATE":
            self.status_label.setText("Board updated")

        if sent == "POLL":
            self.refresh_board()
        else:
            self.finish_step()

    def game_ended(self):
        """RESIGN worked (or the board wasn't in a game any more)."""
        self.game_active = False
        self.game_over = True
        self.result = "ended"
        self.status_label.setText("Game ended")

        flow, self.flow = self.flow, None
        if flow == "new":
            self.swap_on_new = False
            self.send("NEW", "-", "Starting a new game...")
        elif flow == "end":
            self.send("DISCONNECT", "-", "Leaving...")
        else:
            self.finish_step()

    def handle_nack(self, sent, code):
        if self.connecting:
            self.fail_connection("nack")
            return
        if self.reconnecting:
            self.fail_reconnect("nack")
            return
        if sent == "POLL":
            return

        if sent == "MOVE" and code == "NOGAME":
            # The board isn't in a game any more: it must have been reset
            self.server_lost("reset")
            return

        if sent == "RESIGN" and code == "NOGAME":
            # Nothing left to resign (the board was reset), carry on anyway
            self.game_ended()
            return

        self.flow = None
        self.status_label.setText(NACK_TEXT.get(code, f"The board refused that ({code})."))

        if sent == "MOVE" and code in RESYNC_AFTER:
            self.send("STATE", "-", label="SYNC")
        else:
            self.finish_step()

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def refresh_board(self):
        win_line = self.find_win_line()

        for index, value in enumerate(self.board):
            cell = self.board_widget.cells[index]
            cell.set_mark(value)       # a newly placed mark is written out
            cell.highlight = win_line is not None and index in win_line
            cell.dimmed = win_line is not None and index not in win_line
            cell.update()

        self.update_players()
        self.update_board_buttons()

    def find_win_line(self):
        if not (isinstance(self.result, tuple) and self.result[0] == "win"):
            return None

        lines = [(0, 1, 2), (3, 4, 5), (6, 7, 8),
                 (0, 3, 6), (1, 4, 7), (2, 5, 8),
                 (0, 4, 8), (2, 4, 6)]
        for a, b, c in lines:
            if self.board[a] != "." and self.board[a] == self.board[b] == self.board[c]:
                return (a, b, c)
        return None

    def update_players(self):
        """Player cards (name + whose move / who won) and the round line."""
        subs = {"X": "ready", "O": "ready"}
        active = {"X": False, "O": False}

        if self.lost or self.reconnecting:
            subs = {"X": "paused", "O": "paused"}
        elif self.game_active:
            mark = "X" if self.board.count("X") == self.board.count("O") else "O"
            other = "O" if mark == "X" else "X"
            subs[mark] = "your move"
            subs[other] = "waiting"
            active[mark] = True
        elif isinstance(self.result, tuple) and self.result[0] == "win":
            winner = self.result[1]
            other = "O" if winner == "X" else "X"
            subs[winner] = "winner"
            subs[other] = ""
            active[winner] = True
        elif isinstance(self.result, tuple) and self.result[0] == "draw":
            subs = {"X": "draw", "O": "draw"}

        for mark, card in (("X", self.card_x), ("O", self.card_o)):
            card.set_state(self.player_names[mark], subs[mark], active[mark])

        if self.round_number > 0:
            self.round_label.setText(
                f"Round {self.round_number} · "
                f"{self.player_names['X']} opened this round")
        else:
            self.round_label.setText("")

    def update_board_buttons(self):
        for index, cell in enumerate(self.board_widget.cells):
            can_play = (self.can_act() and self.game_active
                        and self.board[index] == ".")
            cell.setEnabled(can_play)
            cell.setCursor(Qt.CursorShape.PointingHandCursor if can_play
                           else Qt.CursorShape.ArrowCursor)

    def update_controls(self):
        ready = self.can_act()

        self.new_game_button.setText(
            "Play again" if self.game_over and not self.game_active else "New game")
        self.new_game_button.setEnabled(ready)
        self.end_game_button.setEnabled(ready)
        self.sync_button.setEnabled(ready)
        self.disconnect_button.setEnabled(ready)

        self.update_board_buttons()

    def closeEvent(self, event):
        self.poll_timer.stop()
        self.drop_worker()
        event.accept()


class AppWindow(QStackedWidget):
    """Holds the start page and the game page; shows one at a time."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Serial Game Server")
        self.resize(720, 700)
        self.setMinimumSize(500, 640)

        self.names = ("Player X", "Player O")

        self.start_screen = StartScreen()
        self.game_window = GameWindow()
        self.addWidget(self.start_screen)
        self.addWidget(self.game_window)

        self.start_screen.start_requested.connect(self.begin_connect)
        self.start_screen.close_requested.connect(self.close)
        self.game_window.connection_ready.connect(self.show_game)
        self.game_window.connection_failed.connect(self.on_connection_failed)
        self.game_window.left_game.connect(self.show_start)

    def begin_connect(self, x_name, o_name):
        self.names = (x_name, o_name)
        self.game_window.set_players(x_name, o_name)
        self.start_screen.set_busy(True)

        if not self.game_window.connect_to_stm32():
            self.start_screen.set_busy(False)

    def show_game(self):
        self.start_screen.set_busy(False)
        self.setCurrentWidget(self.game_window)

    def on_connection_failed(self, title, text):
        self.start_screen.set_busy(False)
        show_message(self, title, text, QMessageBox.Icon.Warning)

    def show_start(self):
        self.setCurrentWidget(self.start_screen)

    def closeEvent(self, event):
        # A child's closeEvent is not called automatically; this stops the serial worker.
        self.game_window.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication([])
    window = AppWindow()
    window.show()
    app.exec()