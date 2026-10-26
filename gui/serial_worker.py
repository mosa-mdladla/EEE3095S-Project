from PySide6.QtCore import QThread, Signal
from gui.serial_client import SerialClient
from queue import Queue

class SerialWorker(QThread):
    #sending response back to main GUI
    response_received = Signal(str,str)
    error_occurred = Signal(str)
    #boolean of whether a new connection has opened successfully
    new_connection = Signal(bool)

    def __init__(self,port="COM5"):
        super().__init__()

        self.port = port
        #Queue that will store commands yet to be processed
        self.commands = Queue()
        self.client = None

    def send_command(self,command,arguments="-"):
        self.commands.put((command,arguments))

    def stop(self):
        self.commands.put(None)

    def run(self):
        #Opens a connection and keeps it open for the entire session
        try:
            self.client = SerialClient(port=self.port)
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
                except:
                    self.error_occurred.emit(str(error))
        except Exception as error:
            self.error_occurred.emit(str(error))
        finally:
            #serial connection closes when the worker/thread stops
            if self.client is not None:
                self.client.close()
                self.client = None

            self.new_connection.emit(False)