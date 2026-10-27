import serial
import binascii

def frame(seq, command, arguments="-"):
    body = f"{seq:04X}|{command}|{arguments}".encode("ascii")
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode("ascii")
    return b"@" + body + b"|" + crc + b"\n"

with serial.Serial("COM5", 115200, timeout=2) as s:
    s.reset_input_buffer()

    # Known starting state: CONNECT always returns the server to IDLE.
    s.write(frame(0x0FFF, "CONNECT"))
    assert b"|OK|-|" in s.readline(), "Could not reset the server with CONNECT"

    def send(seq, command, arguments="-"):
        request = frame(seq, command, arguments)
        s.write(request)

        response = s.readline().decode("ascii").strip()

        print(f"Sent:     {request.decode('ascii').strip()}")
        print(f"Received: {response}")

        assert response, f"No response for {command}"
        return response

    # Test 1: STATE has no board to report in IDLE (no game exists yet),
    # so it is rejected in the same way as MOVE before NEW.
    response = send(1, "STATE")
    assert "|NACK|NOGAME|" in response, (
        "STATE in IDLE should return NACK:NOGAME"
    )
    print("PASS: STATE is rejected with NOGAME in IDLE")

    # Test 2: The rejected STATE must not prevent a new game from starting.
    response = send(2, "NEW")
    assert "|OK|-" in response, "NEW failed"
    print("PASS: NEW starts a game")

    # Test 3: STATE returns the current board during a game.
    response = send(3, "STATE")
    assert "|BOARD|.........|" in response, (
        "STATE should return the board during a game"
    )
    print("PASS: STATE works during an active game")

print("\nSTATE RULE TESTS PASSED!")