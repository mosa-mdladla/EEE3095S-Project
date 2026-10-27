import time
import serial

PORT = "COM5"
seq = 0

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc

def send(ser, cmd, args="-"):
    """Send one framed command, return (command, arguments) of the reply."""
    global seq
    seq = (seq + 1) & 0xFFFF
    body = f"{seq:04X}|{cmd}|{args}"
    ser.write(f"@{body}|{crc16(body.encode()):04X}\n".encode())
    line = ser.readline().decode().strip()          # @SSSS|CMD|ARGS|CCCC
    assert line.startswith("@"), f"no/bad reply: {line!r}"
    _, rcmd, rargs, _ = line[1:].split("|")
    return rcmd, rargs

def look(msg):
    input(f"   LOOK: {msg}  -> press Enter to continue ")

def fresh_game(ser):
    """CONNECT returns the server to IDLE; NEW is only accepted from IDLE or GAME_OVER."""
    assert send(ser, "CONNECT") == ("OK", "-")
    assert send(ser, "NEW") == ("OK", "-")

def play(ser, moves):
    """moves: list of (player, cell). Returns the last reply."""
    for p, c in moves:
        reply = send(ser, "MOVE", f"{p},{c}")
    return reply

if __name__ == "__main__":
    with serial.Serial(PORT, 115200, timeout=1) as ser:
        time.sleep(0.2)
        ser.reset_input_buffer()

        assert send(ser, "CONNECT") == ("OK", "-")
        look("IDLE: one LED sweeping PB0<->PB7")

        # X's turn / O's turn
        assert send(ser, "NEW") == ("OK", "-")
        look("X's turn: PB0-PB3 steady")
        assert send(ser, "MOVE", "X,0")[0] == "BOARD"
        look("O's turn: PB4-PB7 steady")

        # rejected moves must not change the LEDs
        assert send(ser, "MOVE", "O,0") == ("NACK", "OCCUPIED")
        assert send(ser, "MOVE", "X,5") == ("NACK", "NOTURN")
        look("still O's turn (PB4-PB7), unchanged by the rejections")

        # win (X: 0,1,2)
        fresh_game(ser)
        r = play(ser, [("X",0),("O",3),("X",1),("O",4),("X",2)])
        assert r[0] == "WIN" and r[1].startswith("X,")
        look("WIN: alternating 10101010 / 01010101")

        # draw
        fresh_game(ser)
        r = play(ser, [("X",0),("O",1),("X",2),("O",4),("X",3),
                       ("O",5),("X",7),("O",6),("X",8)])
        assert r[0] == "DRAW"
        look("DRAW: all LEDs blinking slowly")

        # resign
        fresh_game(ser)
        assert send(ser, "RESIGN") == ("OK", "GAMEOVER")
        look("RESIGNED: edge LEDs closing inward")

        # new game after game over restarts the pattern
        assert send(ser, "NEW") == ("OK", "-")
        look("back to X's turn: PB0-PB3 steady")
        print("All protocol assertions passed.")