import serial
import binascii


def frame(seq, command, arguments="-"):
    # Build the text covered by the CRC.
    body = f"{seq:04d}|{command}|{arguments}".encode("ascii")

    # Calculate CRC-16/CCITT-FALSE.
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode("ascii")

    # Build the complete frame.
    return b"@" + body + b"|" + crc + b"\n"


s = serial.Serial("COM5", 115200, timeout=1)

# Test 1: Valid CONNECT command.
s.write(frame(1, "CONNECT"))
print("CONNECT:", s.readline())

# Test 2: Start a new game.
s.write(frame(2, "NEW"))
print("NEW:", s.readline())

# Test 3: Start another new game.
s.write(frame(3, "NEW"))
print("NEW again:", s.readline())

# Test 4: Unsupported command.
s.write(frame(4, "HELLO"))
print("HELLO:", s.readline())

# Test 5: Old frame format.
s.write(b"@0005:CONNECT*0000\n")
print("Old format:", s.readline())

# Test 6: Garbage without a start marker.
s.write(b"garbage\n")
print("Garbage:", s.readline())

s.close()
