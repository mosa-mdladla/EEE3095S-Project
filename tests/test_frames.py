
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

# Test 2: Unsupported command.
s.write(frame(2, "HELLO"))
print("HELLO:", s.readline())

# Test 3: Invalid checksum and old frame format.
s.write(b"@0003:CONNECT*0000\n")
print("Old format:", s.readline())

# Test 4: Input without a valid frame start marker.
s.write(b"garbage\n")
print("Garbage:", s.readline())

s.close()
