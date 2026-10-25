import serial

class SerialClientError(Exception):
    """Exception for serial communication between client and server"""
    pass

class ResponseTimeout(SerialClientError):
    """No response was received in time"""
    pass

class ProtocolError(SerialClientError):
    """The response frame is malformed or has an invalid CRC"""
    pass

class SequenceMismatch(SerialClientError):
    """The response sequence number does not match the request"""
    pass


#CRC-16 CALCULATION
#Crc is used ot check if the contents of frame have been corrupted during communication
def crc16(data: bytes) -> int:
    #initial CRC value 
    crc = 0xFFFF
    #processing each byte in the data
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

# SerialClient Class
# Manages  communication between the PC & STM32
class SerialClient:
    def __init__(self, port="COM5",baudrate=115200,timeout=2):
        #Sequence numbers to help identify which response belongs to which request
        self.seq = 0
        #opening serial connection to STM32
        self.ser = serial.Serial(port,baudrate,timeout=timeout)

    def close(self):
        #Closes connection only if it is open
        #GUI calls it when closing
        if self.ser.is_open:
            self.ser.close()

    def send_command(self,command,arguments="-"):
        self.seq = (self.seq +1) & 0xFFFF
        #building frame body without the @ or CRC
        body = f"{self,self.seq:04X}|{command}|{arguments}"
        #calculate CRC
        crc = crc16(body.encode("ascii"))

        request =  f"{self,self.seq:04X}|{command}|{arguments}"
        try:
            self.ser.write(request)
            line = self.ser.readline()
        except serial.SerialException as error:
            raise SerialClientError(f"Serial Communication failed:  {error}") from error

        if not line:
            raise ResponseTimeout(f"No response recieved for {command}")

        try:
            line = line.decode("ascii").strip()
        except UnicodeDecodeError as error:
            raise ProtocolError("Invalid characters used") from error

        if not line.startswith("@"):
            raise ProtocolError("Response does not start with @")

        parts = line[1:].split("|")
        if len(parts) != 4:
            raise ProtocolError("Invalid frame format.")
        #Stores each field separately for validation
        response_seq, response_command, response_args, response_crc = parts

        try:
            received_seq = int(response_seq, 16)
            received_crc = int(response_crc, 16)
        except ValueError as error:
            raise ProtocolError("Invalid sequence number or CRC") from error

        response_body = (f"{response_seq}|{response_command}|{response_args}")
        new_crc = crc16(response_body.encode("ascii"))

        if received_crc != new_crc:
            raise ProtocolError("Response CRC Mismatch")
        if received_seq != self.seq:
            raise SequenceMismatch(f"Expected sequence {self.seq:04X}," f"received {received_seq:04X}")

        #returns response command and its arguments
        return response_command, response_args