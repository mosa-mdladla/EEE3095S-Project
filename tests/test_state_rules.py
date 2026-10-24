import serial
import binascii

def frame(seq, command, arguments="-"):
    body = f"{seq:04d}|{command}|{arguments}".encode("ascii")
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode("ascii")
    return b"@" + body + b"|" + crc + b"\n"

with serial.Serial("COM5", 115200, timeout=2) as s:
    s.reset_input_buffer()

    def send(seq, command, arguments="-"):
        s.write(frame(seq, command, arguments))
        response = s.readline().decode("ascii").strip()
        print(f"{command}: {response}")

        assert response, f"No response for {command}"
        return response

    # Reset the board to its boot state by restarting the MCU

    # Test IDLE: STATE should be rejected.
    # MCU is currently in IDLE.
    response = send(1, "STATE")
    assert "|NACK|NOGAME|" in response, (
        "STATE should be rejected in IDLE"
    )
    print("PASS: STATE rejected in IDLE")

    response = send(2, "NEW")
    assert "|OK|-" in response, "NEW failed"
    print("PASS: NEW starts a game")

    response = send(3, "STATE")
    assert "|BOARD|.........|" in response, (
        "STATE should return the board during a game"
    )
    print("PASS: STATE works in IN_PROGRESS")

print("\nSTATE RULE TESTS PASSED!")