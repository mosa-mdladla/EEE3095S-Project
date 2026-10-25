import serial
import binascii

def frame(seq, command, arguments="-"):
    body = f"{seq:04X}|{command}|{arguments}".encode("ascii")
    crc = f"{binascii.crc_hqx(body, 0xFFFF):04X}".encode("ascii")
    return b"@" + body + b"|" + crc + b"\n"

s = serial.Serial("COM5", 115200, timeout=2)
s.reset_input_buffer()

def send(seq, command, arguments="-"):
    request = frame(seq, command, arguments)
    s.write(request)
    response = s.readline().decode("ascii").strip()

    if not response:
        raise AssertionError(
            f"No response for {command} {arguments}"
        )

    print(f"Sent:     {request.decode('ascii').strip()}")
    print(f"Received: {response}")

    return response

def check(condition, message):
    if not condition:
        raise AssertionError(message)

    print(f"PASS: {message}")

try:
    seq = 1

    # CONNECT to establish the protocol session.
    response = send(seq, "CONNECT")
    check("|OK|-" in response, "CONNECT succeeds")
    seq += 1

    # Test 1: MOVE before NEW.
    print("\n=== Test 1: MOVE before NEW ===")

    response = send(seq, "MOVE", "X,0")
    seq += 1

    check(
        "|NACK|NOGAME|" in response,
        "MOVE before NEW is rejected"
    )

    # Test 2: STATE before NEW.
    print("\n=== Test 2: STATE before NEW ===")

    response = send(seq, "STATE")
    seq += 1

    print("Review the response: does STATE return a board?")
    print("We will use this result to confirm the intended behaviour.")

    # Test 3: Invalid arguments in an active game.
    print("\n=== Test 3: Invalid MOVE arguments ===")

    response = send(seq, "NEW")
    seq += 1
    check("|OK|-" in response, "NEW starts a game")

    response = send(seq, "MOVE", "X,A")
    seq += 1
    print("Invalid cell character response:", response)

    response = send(seq, "STATE")
    seq += 1
    check(
        "|BOARD|.........|" in response,
        "Invalid character did not change the board"
    )

    response = send(seq, "MOVE", "X,10")
    seq += 1
    print("Two-digit cell index response:", response)

    response = send(seq, "STATE")
    seq += 1
    check(
        "|BOARD|.........|" in response,
        "Invalid index did not change the board"
    )

    # Test 4: Unknown command.
    print("\n=== Test 4: Unknown command ===")

    response = send(seq, "HELLO")
    seq += 1
    check(
        "|NACK|BADCMD|" in response,
        "Unknown command is rejected"
    )

    # Confirm that the unknown command did not change the board.
    response = send(seq, "STATE")
    seq += 1
    check(
        "|BOARD|.........|" in response,
        "Unknown command did not change the board"
    )

    # Test 5: NEW resets an existing game.
    print("\n=== Test 5: NEW resets the board ===")

    response = send(seq, "MOVE", "X,4")
    seq += 1
    check(
        "|BOARD|....X....|" in response,
        "A legal move updates the board"
    )

    response = send(seq, "NEW")
    seq += 1
    check("|OK|-" in response, "NEW resets the game")

    response = send(seq, "STATE")
    seq += 1
    check(
        "|BOARD|.........|" in response,
        "Board is empty after NEW"
    )

    # Test 6: Rejects moves after a game has ended.
    print("\n=== Test 6: MOVE after game over ===")

    #Start a new game
    response = send(seq, "NEW")
    seq += 1
    check("|OK|-" in response,"NEW starts a new game")

    moves = ["X,0","O,3","X,1","O,4","X,2"]

    for move in moves:
        response = send(seq,"MOVE",move)
        seq+=1

    check("WIN|X," in response, "X wins after completing the top row")

    #a further move must be rejected
    response = send(seq,"MOVE","O,5")
    seq+=1

    check("|NACK|NOGAME|" in response, "MOVE after game over is rejected")

    print("\nINVALID COMMAND TESTS COMPLETED")











    print("\nINVALID-COMMAND TESTS COMPLETED.")

finally:
    s.close()