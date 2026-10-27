SERIAL GAME SERVER SYSTEM

1. Project Overview
Serial Game Server is an authoritative STM32 game server with a thin PC-side GUI client. The aim is to build a client-server game system over a serial link and have the STM32 microontroller act as the single authority whilst the PC client (GUI) communicates requests and processes responses over the serial connection.

2. Features of Game System
    - Authoritative Tic-Tac-Toe game logic running on the STM32
    - UART communication between teh STM32 and PC
    - Serial message framing and CRC-16 error detection
    - Detection of wins and draws
    - Handling invalid commands, moves, frames and other errors
    - LCD and LED output corresponding to game state
    - PC-side GUI implemented using Python and PySide6
    - Automated tests for protocol handling

3. Hardware
    - STM32F051C8 development board
    - ST-LINK virtual COM port for PC-to-UART communication (typically COM5)
    - PC running GUI client
    - UART Configuration    
        - USART1
        - 115200 baud
        - 8 data bits
        - No parity
        - 1 stop bit
        - No hardware flow control
        - 8N1 Serial Format

4. Repository Structure
    SerialGameServer/
    ├── .settings
    ├── Core/
    │   ├── Inc/
    │   └── Src/
    ├── Drivers/
    ├── docs/
    ├── gui/
    ├── tests/
    ├── .project
    ├── .cproject
    ├── .mxproject
    ├── EEE3095S-Project Debug.launch
    ├── EEE3095S-Project.ioc
    ├── NoughtsAndCrosses Debug.launch
    ├── README.md
    ├── STM32F051C8TX_FLASH.Id

    - Core/Inc contains firmware header files
    - Core/Src contains firmware source files, which include the main application, frame parser and protocol
    - Drivers/ contain the STM32 hardware support and HAL driver
    - docs/ contains project documentation 
    - tests/ contains tests for protocol framing, CRC validation, game logic and error handling
    - gui/ contains source files pertaining to the user interface and interaction with the game system


    5. Building the firmware

    - Instructions
        - Open STM32CubeIDE
        - Import the project into the workspace
        - Build project using Project -> Build Project
        - Connect development board through ST-LINK
        - Flash the firmware using Run or Debug in STM32CubeIDE
    
    6. Running the GUI

    - Requirements
        - Python3
        - PySide6

    - Instructions
        - Connect STM32 board to PC using USB
        - Open terminal in GUI source directory
        - Run main.py using "python -m gui.main"
        - Start new game and make moves using the GUI

    7. Responses and Errors
        - The server returns the following responses
            - OK
            - BOARD
            - WIN
            - DRAW
            - NACK
                - BADFRAME -> Invalid frame format
                - BADSEQ   -> Invalid sequence number
                - BADCRC   -> Invalid checksum
                - BADCMD   -> Invalid command arguments
                - NOGAME   -> No active game present
                - BADARG   -> Invalid argument format
                - RANGE    -> Board position outside valid range
                - NOTURN   -> Not that player's turn
                - OCCUPIED -> Selected position is already occupied
                - GAMEACTIVE -> Operation is rejected becasue the game is active
