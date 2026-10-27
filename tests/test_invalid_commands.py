import serial
import binascii

def frame(seq, command, arguments="-"):
    body = f"{seq:04X}|{command}|{arguments}".encode("ascii")
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode("ascii")
    return b"@" + body + b"|" + crc + b"\n"

s = serial.Serial("COM5", 115200, timeout=2)
s.reset_input_buffer()

seq = 0

def send(command, arguments="-"):
    """Send one frame with the next sequence number and return the reply."""
    global seq
    seq += 1
    request = frame(seq, command, arguments)
    s.write(request)
    response = s.readline().decode("ascii").strip()

    if not response:
        raise AssertionError(f"No response for {command} {arguments}")

    print(f"Sent:     {request.decode('ascii').strip()}")
    print(f"Received: {response}")

    return response

def check(condition, message):
    if not condition:
        raise AssertionError(message)

    print(f"PASS: {message}")

try:
    # CONNECT returns the server to IDLE, so the test starts from a known state.
    response = send("CONNECT")
    check("|OK|-" in response, "CONNECT succeeds")

    # Test 1: MOVE before NEW.
    print("\n=== Test 1: MOVE before NEW ===")
    response = send("MOVE", "X,0")
    check("|NACK|NOGAME|" in response, "MOVE before NEW is rejected")

    # Test 2: STATE before NEW.
    print("\n=== Test 2: STATE before NEW ===")
    response = send("STATE")
    check("|NACK|NOGAME|" in response, "STATE before NEW is rejected")

    # Test 3: Invalid arguments in an active game.
    print("\n=== Test 3: Invalid MOVE arguments ===")
    response = send("NEW")
    check("|OK|-" in response, "NEW starts a game")

    response = send("MOVE", "X,A")
    check("|NACK|BADARG|" in response, "Non-numeric cell returns NACK:BADARG")
    response = send("STATE")
    check("|BOARD|.........|" in response, "Invalid character did not change the board")

    response = send("MOVE", "X,10")
    check("|NACK|RANGE|" in response, "Two-digit cell index returns NACK:RANGE")
    response = send("STATE")
    check("|BOARD|.........|" in response, "Invalid index did not change the board")

    # Test 4: Unknown command.
    print("\n=== Test 4: Unknown command ===")
    response = send("HELLO")
    check("|NACK|BADCMD|" in response, "Unknown command is rejected")
    response = send("STATE")
    check("|BOARD|.........|" in response, "Unknown command did not change the board")

    # Test 5: NEW is refused during a game and allowed once it has ended.
    print("\n=== Test 5: NEW during a game ===")
    response = send("MOVE", "X,4")
    check("|BOARD|....X....|" in response, "A legal move updates the board")

    response = send("NEW")
    check("|NACK|GAMEACTIVE|" in response, "NEW is refused while a game is active")
    response = send("STATE")
    check("|BOARD|....X....|" in response, "Refused NEW did not change the board")

    response = send("RESIGN")
    check("|OK|GAMEOVER|" in response, "RESIGN ends the game")
    response = send("NEW")
    check("|OK|-" in response, "NEW is accepted after the game has ended")
    response = send("STATE")
    check("|BOARD|.........|" in response, "Board is empty after the new game starts")

    # Test 6: Rejects moves after a game has ended.
    # The game started at the end of Test 5 is active and empty.
    print("\n=== Test 6: MOVE after game over ===")
    for move in ["X,0", "O,3", "X,1", "O,4", "X,2"]:
        response = send("MOVE", move)
    check("|WIN|X," in response, "X wins after completing the top row")

    response = send("MOVE", "O,5")
    check("|NACK|NOGAME|" in response, "MOVE after game over is rejected")

    print("\nINVALID-COMMAND TESTS PASSED!")

finally:
    s.close()