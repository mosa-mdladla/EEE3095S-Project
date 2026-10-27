import serial
import binascii

def frame(seq, command, arguments="-"):
    body = f"{seq:04X}|{command}|{arguments}".encode("ascii")
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode("ascii")
    return b"@" + body + b"|" + crc + b"\n"

with serial.Serial("COM5", 115200, timeout=1) as s:
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

        assert response, f"No response for valid command {command}"
        return response

    # Start with a known board.
    response = send(1, "NEW")
    assert "|OK|-" in response

    response = send(2, "MOVE", "X,0")
    assert "|BOARD|X........|" in response

    # Construct a MOVE command with a deliberately incorrect CRC.
    bad_request = frame(3, "MOVE", "O,1")
    parts = bad_request.rstrip(b"\n").rsplit(b"|", 1)

    original_crc = parts[1]
    wrong_first_digit = b"0" if original_crc[:1] != b"0" else b"1"
    wrong_crc = wrong_first_digit + original_crc[1:]

    corrupted_request = parts[0] + b"|" + wrong_crc + b"\n"

    print("\nSending a MOVE with an invalid CRC:")
    print(f"Sent:     {corrupted_request.decode('ascii').strip()}")

    s.write(corrupted_request)
    response = s.readline().decode("ascii").strip()
    print(f"Received: {response}")

    # The server should explicitly reject the corrupted frame.
    assert "|NACK|BADCRC|" in response, (
        f"Expected NACK|BADCRC, but received: {response}"
    )

    print("PASS: Invalid CRC frame was rejected")

    # The next valid command must still work.
    response = send(4, "STATE")
    assert "|BOARD|X........|" in response

    print("PASS: Server recovered and preserved the board")

print("\nBAD CRC RECOVERY TESTS PASSED!")