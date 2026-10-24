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

# Test 1: Connect.
s.write(frame(1, "CONNECT"))
print("CONNECT:", s.readline())

# Test 2: Start a new game.
s.write(frame(2, "NEW"))
print("NEW:", s.readline())

# Test 3: Read the initial board.
s.write(frame(3, "STATE"))
print("STATE after NEW:", s.readline())

# Test 4: Start another new game.
s.write(frame(4, "NEW"))
print("NEW again:", s.readline())

# Test 5: Read the board again.
s.write(frame(5, "STATE"))
print("STATE after NEW again:", s.readline())

# Test 6: Unsupported command.
s.write(frame(6, "HELLO"))
print("HELLO:", s.readline())

s.close()