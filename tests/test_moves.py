import serial
import binascii


def frame(seq, command, arguments="-"):
    body = f"{seq:04X}|{command}|{arguments}".encode("ascii")
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode("ascii")
    return b"@" + body + b"|" + crc + b"\n"

# Connect to the STM32 board.
s = serial.Serial("COM5", 115200, timeout=2)
s.reset_input_buffer()

def send(seq, command, arguments="-"):
    request = frame(seq, command, arguments)
    s.write(request)
    response = s.readline().decode("ascii").strip()

    print(f"Sent:     {request.decode('ascii').strip()}")
    print(f"Received: {response}")
    print()

    return response

try:
    print("TEST 1: Start a new game")
    send(1, "NEW")

    print("TEST 2: X makes a legal move at cell 0")
    response = send(2, "MOVE", "X,0")
    assert "|BOARD|X........|" in response

    print("TEST 3: O tries to use occupied cell 0")
    response = send(3, "MOVE", "O,0")
    assert "|NACK|OCCUPIED|" in response

    print("TEST 4: O makes a legal move at cell 1")
    response = send(4, "MOVE", "O,1")
    assert "|BOARD|XO.......|" in response

    print("TEST 5: O tries to move again when it is X's turn")
    response = send(5, "MOVE", "O,2")
    assert "|NACK|NOTURN|" in response

    print("TEST 6: X tries to use invalid cell 9")
    response = send(6, "MOVE", "X,9")
    assert "|NACK|RANGE|" in response

    print("TEST 7: Confirm rejected moves did not change the board")
    response = send(7, "STATE")
    assert "|BOARD|XO.......|" in response

    print("ALL MOVE TESTS PASSED!")

finally:
    s.close()