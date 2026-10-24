import serial, binascii

def frame(seq, payload):
    body = f"{seq:04d}:{payload}".encode()
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode()
    return b"@" + body + b"*" + crc + b"\n"

s = serial.Serial('COM5', 115200, timeout=1)
s.write(frame(1, "CONNECT")); print(s.readline())
s.write(frame(2, "HELLO")); print(s.readline())
s.write(b"@0003:CONNECT*0000\n"); print(s.readline())
s.write(b"garbage\n"); print(s.readline())
s.close()
