import serial
import binascii

def frame(seq, command, arguments="-"):
    body = f"{seq:04X}|{command}|{arguments}".encode("ascii")
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode("ascii")
    return b"@" + body + b"|" + crc + b"\n"

with serial.Serial("COM5", 115200, timeout=2) as s:
    s.reset_input_buffer()

    def send(seq, command, arguments="-"):
        request = frame(seq, command, arguments)
        s.write(request)

        response = s.readline().decode("ascii").strip()

        print(f"Sent:     {request.decode('ascii').strip()}")
        print(f"Received: {response}")

        assert response, f"No response for {command}"
        return response

    # Reset the STM32 manually before running this test.
    # The board should be in IDLE.

    # Test 1: STATE should return the empty board in IDLE.
    response = send(1, "STATE")
    assert "|BOARD|.........|" in response, (
        "STATE should return the empty board in IDLE"
    )
    print("PASS: STATE returns the empty board in IDLE")

    # Test 2: STATE should not prevent a new game from starting.
    response = send(2, "NEW")
    assert "|OK|-" in response, "NEW failed"
    print("PASS: NEW starts a game")

    # Test 3: STATE should return the current board during a game.
    response = send(3, "STATE")
    assert "|BOARD|.........|" in response, (
        "STATE should return the board during a game"
    )
    print("PASS: STATE works during an active game")

print("\nSTATE RULE TESTS PASSED!")