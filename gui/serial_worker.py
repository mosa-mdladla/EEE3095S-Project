from PySide6.QtCore import QThread, Signal
from gui.serial_client import (SerialClient, ResponseTimeout, ProtocolError,
                               SequenceMismatch)
from queue import Queue


def open_failure_kind(error):
    """Why the serial port could not be opened."""
    text = str(error).lower()
    if "permissionerror" in text or "access is denied" in text or "busy" in text:
        return "port_busy"          # another program is using the port
    return "not_connected"          # the board isn't plugged in


def error_kind(error):
    """What kind of problem a failed command was."""
    if isinstance(error, ResponseTimeout):
        return "timeout"            # the board didn't answer
    if isinstance(error, SequenceMismatch):
        return "sequence"           # a reply that belongs to another request
    if isinstance(error, ProtocolError):
        return "protocol"           # garbled reply / bad CRC
    return "lost"                   # the serial link itself failed (unplugged)


class SerialWorker(QThread):
    #sending response back to main GUI
    response_received = Signal(str,str)
    #(kind, message): kind is one of not_connected, port_busy, timeout,
    #sequence, protocol, lost
    error_occurred = Signal(str,str)
    #boolean of whether a new connection has opened successfully
    new_connection = Signal(bool)

    def __init__(self,port="COM5"):
        super().__init__()

        self.port = port
        #Queue that will store commands yet to be processed
        self.commands = Queue()
        self.client = None
        self.closing = False

    def send_command(self,command,arguments="-"):
        self.commands.put((command,arguments))

    def stop(self):
        self.commands.put(None)

    def shutdown(self, commands):
        """Send these commands, then stop. Used when the window closes."""
        self.closing = True
        for command, arguments in commands:
            self.commands.put((command, arguments))
        self.commands.put(None)

    def run(self):
        #Opens a connection and keeps it open for the entire session
        try:
            try:
                self.client = SerialClient(port=self.port)
            except Exception as error:
                self.error_occurred.emit(open_failure_kind(error), str(error))
                return

            self.new_connection.emit(True)

            while True:
                command_data = self.commands.get()
                if command_data is None:
                    break
                command,arguments = command_data

                try:
                    #Send command and wait for response from STM32
                    response_command, response_arguments = (self.client.send_command(command,arguments))
                    #Passes response over to GUI
                    self.response_received.emit(response_command,response_arguments)
                except Exception as error:
                    self.error_occurred.emit(error_kind(error), str(error))
                    if self.closing:
                        break          # board not answering: give up and close
        finally:
            #serial connection closes when the worker/thread stops
            if self.client is not None:
                self.client.close()
                self.client = None

            self.new_connection.emit(False)