import serial
import binascii

def frame(seq, command, arguments="-"):
    body = f"{seq:04X}|{command}|{arguments}".encode("ascii")
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode("ascii")
    return b"@" + body + b"|" + crc + b"\n"

with serial.Serial("COM5", 115200, timeout=2) as s:
    s.reset_input_buffer()

    # Known starting state: CONNECT always returns the server to IDLE, so this
    # test no longer depends on what an earlier test left behind.
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

    # Test 1: DISCONNECT in IDLE.
    response = send(1, "DISCONNECT")
    assert "|OK|DISCONNECT|" in response
    print("PASS: DISCONNECT accepted in IDLE")

    # Test 2: Start a game and try to disconnect.
    response = send(2, "NEW")
    assert "|OK|-" in response

    response = send(3, "DISCONNECT")
    assert "|NACK|GAMEACTIVE|" in response
    print("PASS: DISCONNECT rejected during an active game")

    # Test 3: The rejected disconnect must not stop the game.
    response = send(4, "MOVE", "X,0")
    assert "|BOARD|X........|" in response
    print("PASS: Game remains active after rejected disconnect")

print("\nDISCONNECT STATE TESTS PASSED!")