import serial
import binascii

def frame(seq, command, arguments="-"):
    body = f"{seq:04d}|{command}|{arguments}".encode("ascii")
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode("ascii")
    return b"@" + body + b"|" + crc + b"\n"

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
    # TEST 1: X wins across the top row.
    print("TEST 1: Detect a horizontal win for X")

    send(1, "NEW")
    send(2, "MOVE", "X,0")
    send(3, "MOVE", "O,3")
    send(4, "MOVE", "X,1")
    send(5, "MOVE", "O,4")

    response = send(6, "MOVE", "X,2")

    assert "|WIN|X," in response, "X's win was not detected"
    assert "XXX" in response, "Winning board is missing"

    print("PASS: X's win was detected.")

    # TEST 2: A move after a win must be rejected.
    print("\nTEST 2: Reject a move after game over")

    response = send(7, "MOVE", "O,5")

    assert "|NACK|NOGAME|" in response, (
        "A move was not rejected after the win"
    )

    print("PASS: Further moves were rejected.")

    # TEST 3: Fill the board without a winning line.
    print("\nTEST 3: Detect a draw")

    send(8, "NEW")

    moves = [
        ("X", 0), ("O", 4),
        ("X", 8), ("O", 2),
        ("X", 6), ("O", 3),
        ("X", 5), ("O", 7),
    ]

    seq = 9

    for player, cell in moves:
        response = send(seq, "MOVE", f"{player},{cell}")

        assert "|BOARD|" in response, (
            f"Unexpected result before the final move: {response}"
        )

        seq += 1

    # X fills the final empty cell at index 1.
    response = send(seq, "MOVE", "X,1")

    assert "|DRAW|" in response, "Draw was not detected"

    print("PASS: The draw was detected.")

    # TEST 4: A move after a draw must be rejected.
    print("\nTEST 4: Reject a move after a draw")

    response = send(seq + 1, "MOVE", "O,1")

    assert "|NACK|NOGAME|" in response, (
        "A move was not rejected after the draw"
    )

    print("PASS: Further moves were rejected.")

    print("\nALL WIN AND DRAW TESTS PASSED!")

finally:
    s.close()