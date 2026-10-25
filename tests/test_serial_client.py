import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(project_root))
from gui.serial_client import SerialClient

def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")

def main():
    #Create client and open connection
    client = SerialClient()

    try:
        # Test 1: Connect
        print("\n===Test 1: CONNECT===")
        response = client.send_command("CONNECT")
        print("Received:", response)
        check(response == ("OK","-"),"CONNECT returns OK")

        # Test 2: New
        print("\n===Test 2: NEW===")
        response = client.send_command("NEW")
        print("Received:", response)
        check(response == ("OK","-"),"NEW returns OK")

        # Test 3: State
        print("\n===Test 3: STATE===")
        response = client.send_command("STATE")
        print("Received:", response)
        check(response == ("BOARD","........."),"STATE returns empty board after NEW")

        print("\nAll serial client tests passed")
    finally:
        client.close()

if __name__ == "__main__":
    main()