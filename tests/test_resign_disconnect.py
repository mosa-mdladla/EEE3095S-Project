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

    # Start a game.
    response = send(1, "NEW")
    assert "|OK|-" in response

    # Resign while a game is active.
    response = send(2, "RESIGN")
    assert "|OK|GAMEOVER|" in response
    print("PASS: RESIGN ends the game")

    # Moves must now be rejected.
    response = send(3, "MOVE", "X,0")
    assert "|NACK|NOGAME|" in response
    print("PASS: MOVE rejected after resignation")

    # STATE remains available after game over.
    response = send(4, "STATE")
    assert "|BOARD|.........|" in response
    print("PASS: STATE works after resignation")

    # DISCONNECT is allowed after game over.
    response = send(5, "DISCONNECT")
    assert "|OK|DISCONNECT|" in response
    print("PASS: DISCONNECT accepted after game over")

print("\nRESIGN AND DISCONNECT TESTS PASSED!")