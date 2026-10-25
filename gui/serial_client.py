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
