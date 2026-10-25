
import serial
import binascii
import time


def frame(seq, command, arguments="-"):
    # Build the text covered by the CRC.
    body = f"{seq:04X}|{command}|{arguments}".encode("ascii")

    # Calculate CRC-16/CCITT-FALSE.
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode("ascii")

    # Build the complete frame.
    return b"@" + body + b"|" + crc + b"\n"


# Open the STM32 serial connection.
s = serial.Serial("COM5", 115200, timeout=1)
time.sleep(0.5)
s.reset_input_buffer()

print("A: Send each whole frame at once")

for i in range(1, 7):
    s.write(frame(i, "CONNECT"))
    print(i, s.readline())
    time.sleep(0.3)


print("B: Send one byte at a time, 2 ms apart")

for i in range(7, 13):
    for byte_value in frame(i, "CONNECT"):
        s.write(bytes([byte_value]))
        time.sleep(0.002)

    print(i, s.readline())
    time.sleep(0.3)

s.close()