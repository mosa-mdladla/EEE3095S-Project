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


s = serial.Serial("COM5", 115200, timeout=1)
s.reset_input_buffer()


def read():
    return s.readline().decode("ascii", errors="replace").strip()


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


try:
    # Known starting state: CONNECT returns the server to IDLE.
    s.write(frame(0x0FFF, "CONNECT"))
    check("|OK|-|" in read(), "Server reset to IDLE with CONNECT")

    print("\nTest 1: CONNECT")
    s.write(frame(1, "CONNECT"))
    response = read()
    print("Received:", response)
    check("@0001|OK|-|" in response, "CONNECT returns OK")

    print("\nTest 2: NEW starts a game")
    s.write(frame(2, "NEW"))
    response = read()
    print("Received:", response)
    check("@0002|OK|-|" in response, "NEW returns OK")

    print("\nTest 3: STATE after NEW")
    s.write(frame(3, "STATE"))
    response = read()
    print("Received:", response)
    check("|BOARD|.........|" in response, "Board is empty after NEW")

    print("\nTest 4: NEW while a game is in progress")
    s.write(frame(4, "NEW"))
    response = read()
    print("Received:", response)
    check("|NACK|GAMEACTIVE|" in response, "NEW is refused during an active game")

    print("\nTest 5: STATE after the refused NEW")
    s.write(frame(5, "STATE"))
    response = read()
    print("Received:", response)
    check("|BOARD|.........|" in response, "Board unchanged after the refused NEW")

    print("\nTest 6: Unsupported command")
    s.write(frame(6, "HELLO"))
    response = read()
    print("Received:", response)
    check("|NACK|BADCMD|" in response, "Unknown command returns NACK:BADCMD")

    print("\nTest 7: Garbage bytes before a valid frame")
    s.write(b"garbage123?!")
    s.write(frame(7, "CONNECT"))
    response = read()
    print("Received:", response)
    check("@0007|OK|-|" in response, "Garbage before '@' is ignored")

    print("\nTest 8: Oversized frame")
    s.write(b"@" + b"A" * 80 + b"\n")
    response = read()
    print("Received:", response)
    check("|NACK|BADFRAME|" in response, "Oversized frame returns NACK:BADFRAME")

    print("\nTest 9: Incomplete frame, then recovery")
    s.write(b"@0008|CONNECT|")
    time.sleep(0.8)  # longer than the 500 ms frame timeout
    s.write(frame(9, "CONNECT"))
    response = read()
    print("Received:", response)
    check("@0009|OK|-|" in response,
          "Incomplete frame was dropped and the next frame was accepted")

    print("\nTest 10: Frame sent one byte at a time, 2 ms apart")
    for byte_value in frame(10, "CONNECT"):
        s.write(bytes([byte_value]))
        time.sleep(0.002)
    response = read()
    print("Received:", response)
    check("@000A|OK|-|" in response, "Slowly sent frame is received intact")

    print("\nROBUSTNESS TESTS PASSED")

finally:
    s.close()