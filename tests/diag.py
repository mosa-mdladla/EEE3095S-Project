import serial, binascii, time

def frame(seq, payload):
    body = f"{seq:04d}:{payload}".encode()
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode()
    return b"@" + body + b"*" + crc + b"\n"

s = serial.Serial('COM5', 115200, timeout=1)
time.sleep(0.5)
s.reset_input_buffer()

print("A: whole frame at once")
for i in range(1, 7):
    s.write(frame(i, "CONNECT"))
    print(i, s.readline())
    time.sleep(0.3)

print("B: one byte at a time, 2 ms apart")
for i in range(7, 13):
    for b in frame(i, "CONNECT"):
        s.write(bytes([b]))
        time.sleep(0.002)
    print(i, s.readline())
    time.sleep(0.3)
s.close()
