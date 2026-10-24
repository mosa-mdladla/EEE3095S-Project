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

    if not response:
        raise AssertionError(f"No response for {command} {arguments}")

    print(f"Sent:     {request.decode('ascii').strip()}")
    print(f"Received: {response}")

    return response

# Each test lists (player, cell index) in the order played.
# The final move in each sequence should produce a win.
win_tests = [
    ("Top row", [
        ("X", 0), ("O", 3),
        ("X", 1), ("O", 4),
        ("X", 2),
    ]),
    ("Middle row", [
        ("X", 3), ("O", 0),
        ("X", 4), ("O", 1),
        ("X", 5),
    ]),
    ("Bottom row", [
        ("X", 6), ("O", 0),
        ("X", 7), ("O", 1),
        ("X", 8),
    ]),
    ("Left column", [
        ("X", 0), ("O", 1),
        ("X", 3), ("O", 2),
        ("X", 6),
    ]),
    ("Middle column", [
        ("X", 1), ("O", 0),
        ("X", 4), ("O", 2),
        ("X", 7),
    ]),
    ("Right column", [
        ("X", 2), ("O", 0),
        ("X", 5), ("O", 1),
        ("X", 8),
    ]),
    ("Main diagonal", [
        ("X", 0), ("O", 1),
        ("X", 4), ("O", 2),
        ("X", 8),
    ]),
    ("Other diagonal", [
        ("X", 2), ("O", 0),
        ("X", 4), ("O", 1),
        ("X", 6),
    ]),
]

try:
    seq = 1

    for name, moves in win_tests:
        print(f"\n=== Testing {name} ===")

        response = send(seq, "NEW")
        assert "|OK|-" in response, "NEW failed"
        seq += 1

        for player, cell in moves:
            response = send(seq, "MOVE", f"{player},{cell}")
            seq += 1

        assert "|WIN|X," in response, (
            f"{name} was not detected as an X win"
        )

        print(f"PASS: {name}")

        # Confirm that the game is locked after the win.
        response = send(seq, "MOVE", "O,8")
        seq += 1

        assert "|NACK|NOGAME|" in response, (
            f"Game was not locked after {name}"
        )

        print("PASS: Further moves rejected")

    print("\nALL WINNING-COMBINATION TESTS PASSED!")

finally:
    s.close()