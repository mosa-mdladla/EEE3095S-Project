/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include "frameparser.h"
#include "protocol.h"
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* Server states */
typedef enum
{
    GAME_IDLE,
    GAME_IN_PROGRESS,
    GAME_OVER
} GameState;

typedef enum
{
    RESULT_NONE,
    RESULT_X_WIN,
    RESULT_O_WIN,
    RESULT_DRAW,
    RESULT_RESIGNED
} GameResult;

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */
#define PIN_WRITE(port, pin, on) \
    ((port)->BSRR = (on) ? (uint32_t)(pin) : ((uint32_t)(pin) << 16U))

#define LCD_RS(on) PIN_WRITE(GPIOC, GPIO_PIN_14, (on))
#define LCD_E(on)  PIN_WRITE(GPIOC, GPIO_PIN_15, (on))
#define LCD_BL(on) PIN_WRITE(GPIOC, GPIO_PIN_13, (on))

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
UART_HandleTypeDef huart1;

/* USER CODE BEGIN PV */
FrameParser fp;
volatile uint32_t last_byte_tick = 0U;

#define RX_BUF_SIZE 128U
uint8_t rx_buf[RX_BUF_SIZE];
volatile uint8_t rx_head = 0U;
volatile uint8_t rx_tail = 0U;
volatile uint8_t rx_overflow = 0U;
volatile uint8_t rx_error = 0U;

/* Nine game board cells plus a null terminator. */
char game_board[10] = {
    '.', '.', '.',
    '.', '.', '.',
    '.', '.', '.',
    '\0'
};

/* Game state */
uint8_t current_player = 'X';
GameState game_state = GAME_IDLE;

GameResult game_result = RESULT_NONE;

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART1_UART_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* Show an 8-bit pattern on PB0-PB7*/
static void leds_set(uint8_t pattern)
{
    GPIOB->BSRR = ((uint32_t)(uint8_t)~pattern << 16U) | pattern;
}

static void delay_us(uint32_t us)
{
    for (volatile uint32_t i = 0U; i < us; i++) { }
}

static void lcd_write_nibble(uint8_t n)
{
    PIN_WRITE(GPIOB, GPIO_PIN_8,  n & 0x1U);
    PIN_WRITE(GPIOB, GPIO_PIN_9,  n & 0x2U);
    PIN_WRITE(GPIOA, GPIO_PIN_12, n & 0x4U);
    PIN_WRITE(GPIOA, GPIO_PIN_15, n & 0x8U);

    LCD_E(1);
    delay_us(2U);
    LCD_E(0);
    delay_us(2U);
}

/* Send a full byte: is_data = 1 for characters, 0 for commands. */
static void lcd_send(uint8_t byte, uint8_t is_data)
{
    LCD_RS(is_data);
    lcd_write_nibble((uint8_t)(byte >> 4U));
    lcd_write_nibble((uint8_t)(byte & 0x0FU));
    delay_us(50U);                       
}

static void lcd_init(void)
{
    LCD_BL(1);                           /* backlight on */
    LCD_RS(0);
    LCD_E(0);
    HAL_Delay(50);                       /* LCD power-up time */

    /* Reset sequence that forces 4-bit mode. */
    lcd_write_nibble(0x3U); HAL_Delay(5);
    lcd_write_nibble(0x3U); delay_us(200U);
    lcd_write_nibble(0x3U); delay_us(200U);
    lcd_write_nibble(0x2U); delay_us(200U);

    lcd_send(0x28U, 0U);                 /* 4-bit, 2 lines*/
    lcd_send(0x08U, 0U);                 
    lcd_send(0x01U, 0U); HAL_Delay(3);   
    lcd_send(0x06U, 0U);                 
    lcd_send(0x0CU, 0U);                 
}

static void lcd_print_row(uint8_t row, const char *s)
{
    lcd_send((uint8_t)(0x80U | (row ? 0x40U : 0x00U)), 0U);
    for (uint8_t i = 0U; i < 16U; i++)
    {
        char c = (*s != '\0') ? *s++ : ' ';
        lcd_send((uint8_t)c, 1U);
    }
}

static void lcd_update(void)
{
    static char shown[2][17] = {"", ""};   
    char row0[17];
    char row1[17];
    char b[12];

    /* Compact board: 3 cells per row, rows separated by '|' */
    snprintf(b, sizeof(b), "%.3s|%.3s|%.3s",
             &game_board[0], &game_board[3], &game_board[6]);

    uint8_t moves = 0U;
    for (uint8_t i = 0U; i < 9U; i++)
    {
        if (game_board[i] != '.') { moves++; }
    }

    switch (game_state)
    {
    case GAME_IDLE:
        snprintf(row0, sizeof(row0), "TICTACTOE");
        snprintf(row1, sizeof(row1), "Waiting for game");
        break;

    case GAME_IN_PROGRESS:
        snprintf(row0, sizeof(row0), "%s", b);
        snprintf(row1, sizeof(row1), "TURN: %c  MOVES:%u",
                 (char)current_player, (unsigned)(moves % 10U));
        break;

    case GAME_OVER:
    default:
        if (game_result == RESULT_X_WIN)
        {
            snprintf(row0, sizeof(row0), "*** X WINS! ***");
        }
        else if (game_result == RESULT_O_WIN)
        {
            snprintf(row0, sizeof(row0), "*** O WINS! ***");
        }
        else if (game_result == RESULT_DRAW)
        {
            snprintf(row0, sizeof(row0), "=== DRAW! ===");
        }
        else
        {
            snprintf(row0, sizeof(row0), "GAME RESIGNED");
        }
        snprintf(row1, sizeof(row1), "%s", b);
        break;
    }

    if (strcmp(shown[0], row0) != 0)
    {
        lcd_print_row(0U, row0);
        strcpy(shown[0], row0);
    }
    if (strcmp(shown[1], row1) != 0)
    {
        lcd_print_row(1U, row1);
        strcpy(shown[1], row1);
    }
}

/* Non-blocking LED animation driven by the server state. */
static void leds_update(void)
{
    static uint8_t  last_key  = 0xFFU;
    static uint8_t  phase     = 0U;
    static uint32_t last_tick = 0U;

    uint8_t sub = 0U;
    if (game_state == GAME_IN_PROGRESS) { sub = (current_player == 'X') ? 0U : 1U; }
    else if (game_state == GAME_OVER)   { sub = (uint8_t)game_result; }
    uint8_t key = (uint8_t)(((uint8_t)game_state << 4U) | sub);

    /* How long each animation step lasts. */
    uint32_t step_ms = 150U;
    if (game_state == GAME_IDLE)                { step_ms = 120U; }
    else if (game_result == RESULT_DRAW)        { step_ms = 500U; }
    else if (game_result == RESULT_RESIGNED)    { step_ms = 200U; }

    uint32_t now = HAL_GetTick();
    if (key != last_key)
    {
        last_key  = key;
        phase     = 0U;
        last_tick = now;
    }
    else if ((now - last_tick) >= step_ms)
    {
        last_tick = now;
        phase = (uint8_t)((phase + 1U) % 28U);  /* 28 = common multiple of 2, 4, 14 */
    }
    else
    {
        return;                                  /* nothing to change yet */
    }

    uint8_t pattern = 0U;
    switch (game_state)
    {
    case GAME_IDLE:
    {
        uint8_t p = (uint8_t)(phase % 14U);      
        uint8_t idx = (p < 8U) ? p : (uint8_t)(14U - p);
        pattern = (uint8_t)(1U << idx);
        break;
    }
    case GAME_IN_PROGRESS:
        pattern = (current_player == 'X') ? 0x0FU : 0xF0U;
        break;
    case GAME_OVER:
        if (game_result == RESULT_DRAW)
        {
            pattern = (phase & 1U) ? 0x00U : 0xFFU;
        }
        else if (game_result == RESULT_RESIGNED)
        {
            static const uint8_t seq[4] = {0x81U, 0x42U, 0x24U, 0x18U};
            pattern = seq[phase & 3U];
        }
        else
        {
            pattern = (phase & 1U) ? 0x55U : 0xAAU;
        }
        break;
    }
    leds_set(pattern);
}

static void start_new_game(void){
    for(uint8_t i=0U; i<9U;i++){
        game_board[i] = '.';
    }

    game_board[9] = '\0';
    current_player = 'X';
    game_state = GAME_IN_PROGRESS;
    game_result = RESULT_NONE;

}

/* Back to the power-up state: empty board, LCD shows "Waiting for game". */
static void reset_to_idle(void){
    for(uint8_t i=0U; i<9U; i++){
        game_board[i] = '.';
    }

    game_board[9] = '\0';
    current_player = 'X';
    game_state = GAME_IDLE;
    game_result = RESULT_NONE;
}

static void turn_leds_update(void){
    static GameState previous_state = (GameState)255;
    static uint32_t last_tick = 0U;
    static uint8_t blink_on = 0U;

    uint32_t now = HAL_GetTick();

    if(game_state != previous_state){
        previous_state = game_state;
        last_tick = now;
        blink_on = 0U;
    }

    if (game_state == GAME_IN_PROGRESS){
        // X's turn: green on, red off.
        if (current_player == 'X')
        {
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, GPIO_PIN_RESET);
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_11, GPIO_PIN_SET);
        }
        // O's turn: red on, green off.
        else
        {
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, GPIO_PIN_SET);
            HAL_GPIO_WritePin(GPIOB, GPIO_PIN_11, GPIO_PIN_RESET);
        }
    }
    else if (game_state == GAME_OVER)
    {
        // Blink both LEDs together after the game ends. 
        if ((now - last_tick) >= 300U)
        {
            last_tick = now;
            blink_on = (uint8_t)!blink_on;
        }

        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10,
                          blink_on ? GPIO_PIN_SET : GPIO_PIN_RESET);
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_11,
                          blink_on ? GPIO_PIN_SET : GPIO_PIN_RESET);
    }
    else
    {
        // Idle: both turn indicators off.
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10, GPIO_PIN_RESET);
        HAL_GPIO_WritePin(GPIOB, GPIO_PIN_11, GPIO_PIN_RESET);
    }

}


/* Return 1 if the specified player has won, otherwise return 0. */
static uint8_t check_winner(char player)
{
    /* Check the three rows. */
    if (game_board[0] == player
        && game_board[1] == player
        && game_board[2] == player)
    {
        return 1U;
    }

    if (game_board[3] == player
        && game_board[4] == player
        && game_board[5] == player)
    {
        return 1U;
    }

    if (game_board[6] == player
        && game_board[7] == player
        && game_board[8] == player)
    {
        return 1U;
    }

    /* Check the three columns. */
    if (game_board[0] == player
        && game_board[3] == player
        && game_board[6] == player)
    {
        return 1U;
    }

    if (game_board[1] == player
        && game_board[4] == player
        && game_board[7] == player)
    {
        return 1U;
    }

    if (game_board[2] == player
        && game_board[5] == player
        && game_board[8] == player)
    {
        return 1U;
    }

    /* Check the two diagonals. */
    if (game_board[0] == player
        && game_board[4] == player
        && game_board[8] == player)
    {
        return 1U;
    }

    if (game_board[2] == player
        && game_board[4] == player
        && game_board[6] == player)
    {
        return 1U;
    }

    /* No winning combination was found. */
    return 0U;
}


/*
 * Send a pipe-separated protocol frame.
 *
 * Frame format:
 * @SSSS|COMMAND|ARGUMENTS|CCCC\n
 *
 * The CRC covers SSSS|COMMAND|ARGUMENTS.
 */
static void send_frame(const char *seq,
                       const char *command,
                       const char *arguments)
{
    char body[48];
    char out[64];

    int n = snprintf(body, sizeof(body), "%s|%s|%s",
                     seq, command, arguments);

    if (n < 0 || (size_t)n >= sizeof(body))
    {
        return;
    }

    // Calculates the CRC over SSSS|COMMAND|ARGUMENTS.
    uint16_t crc = protocol_crc16((const uint8_t *)body, (size_t)n);

    // Adds the start marker, final separator, CRC and newline.
    int m = snprintf(out, sizeof(out), "@%s|%04X\n",
                     body, (unsigned)crc);

    if (m < 0 || (size_t)m >= sizeof(out))
    {
        return;
    }

    // Transmits the complete response over USART1.
    HAL_UART_Transmit(&huart1, (uint8_t *)out, (uint16_t)m, 100);
}


/*
 * Validate and handle a received protocol frame.
 */
static void handle_frame(char *d)
{
    size_t len = strlen(d);
    char seq[5] = "0000";

    // Minimum valid frame: @0000|A|-|0000
    if (len < 14U || d[0] != '@' || d[5] != '|'
        || d[len - 5U] != '|')
    {
        send_frame(seq, "NACK", "BADFRAME");
        return;
    }

    // Extracts the four-character sequence number.
    memcpy(seq, &d[1], 4U);
    seq[4] = '\0';

    for (size_t i = 0U; i < 4U; i++)
    {
        if (!isxdigit((unsigned char)seq[i]))
        {
            send_frame("0000", "NACK", "BADSEQ");
            return;
        }
    }

    // Reads the four hexadecimal CRC digits.
    uint16_t rx_crc = 0U;

    for (size_t i = len - 4U; i < len; i++)
    {
        if (!isxdigit((unsigned char)d[i]))
        {
            send_frame(seq, "NACK", "BADCRC");
            return;
        }

        char c = d[i];
        uint8_t value;

        if (c >= '0' && c <= '9')
        {
            value = (uint8_t)(c - '0');
        }
        else
        {
            // Converts either uppercase or lowercase A-F.
            c = (char)tolower((unsigned char)c);
            value = (uint8_t)(c - 'a' + 10);
        }

        rx_crc = (uint16_t)((rx_crc << 4U) | value);
    }

    // Calculates the CRC over SSSS|COMMAND|ARGUMENTS.
    // The final separator and four CRC digits are excluded.
    uint16_t calc = protocol_crc16(
        (const uint8_t *)&d[1], len - 6U);

    if (calc != rx_crc)
    {
        send_frame(seq, "NACK", "BADCRC");
        return;
    }

    // Removes the final separator and CRC from the string.
    d[len - 5U] = '\0';

    char *command = &d[6];

    char *separator = strchr(command, '|');

    if (separator == NULL)
    {
        send_frame(seq, "NACK", "BADFRAME");
        return;
    }

    // Splits the frame into separate command and argument strings.
    *separator = '\0';
    char *arguments = separator + 1;

    // Handle the CONNECT command.
    if (strcmp(command, "CONNECT") == 0
        && strcmp(arguments, "-") == 0)
    {
        send_frame(seq, "OK", "-");
    }
    // Handle the NEW command.
    else if (strcmp(command, "NEW") == 0
            && strcmp(arguments, "-") == 0)
    {
        start_new_game();
        send_frame(seq, "OK","-");
    }
    
    // Return the authoritative board state.
    else if (strcmp(command, "STATE") == 0
            && strcmp(arguments, "-") == 0)
    {
        /*
         * STATE reports the current board while a game exists
         * (IN_PROGRESS or GAME_OVER). In IDLE there is no game,
         * so it is rejected with NOGAME.
         */
        if (game_state == GAME_IDLE)
        {
            send_frame(seq, "NACK", "NOGAME");
            return;
        }

        send_frame(seq, "BOARD", game_board);
    }
    
    /* Handle a player's move request. */
    else if (strcmp(command, "MOVE") == 0)
    {
        if (game_state != GAME_IN_PROGRESS)
        {
            send_frame(seq, "NACK", "NOGAME");
            return;
        }

        if (strlen(arguments) != 3U
            || arguments[1] != ','
            || (arguments[0] != 'X' && arguments[0] != 'O')
            || arguments[2] < '0'
            || arguments[2] > '9')
        {
            send_frame(seq, "NACK", "BADARG");
            return;
        }

        /* Converts the requested cell character into an index. */
        uint8_t move_index = (uint8_t)(arguments[2] - '0');

        if (move_index > 8U)
        {
            send_frame(seq, "NACK", "RANGE");
            return;
        }

        /* Rejects a move from the wrong player. */
        if (arguments[0] != current_player)
        {
            send_frame(seq, "NACK", "NOTURN");
            return;
        }

        /* Rejects a move to a cell that is already occupied. */
        if (game_board[move_index] != '.')
        {
            send_frame(seq, "NACK", "OCCUPIED");
            return;
        }

        
        /* A player made this move. */
        char moving_player = (char)current_player;

        /* A legal move to the authoritative board. */
        game_board[move_index] = moving_player;

        if (check_winner(moving_player) != 0U)
        {
            game_state = GAME_OVER;
            game_result = (moving_player == 'X') ? RESULT_X_WIN : RESULT_O_WIN;

            /* Sends the winning player and the final board. */
            char result[12];
            snprintf(result, sizeof(result), "%c,%.9s",
                    moving_player, game_board);

            send_frame(seq, "WIN", result);
            return;
        }

        /* Check whether all nine cells are occupied. */
        uint8_t board_full = 1U;

        for (uint8_t i = 0U; i < 9U; i++)
        {
            if (game_board[i] == '.')
            {
                board_full = 0U;
                break;
            }
        }

        /* If there is no winner and no empty cell, the game is a draw. */
        if (board_full != 0U)
        {
            game_state = GAME_OVER;
            game_result = RESULT_DRAW;
            send_frame(seq, "DRAW", game_board);
            return;
        }

        /* Continue the game by alternating the turn. */
        if (current_player == 'X')
        {
            current_player = 'O';
        }
        else
        {
            current_player = 'X';
        }

        send_frame(seq, "BOARD", game_board);
    }
    
    // Handle a player resigning from the current game.
    else if (strcmp(command, "RESIGN") == 0
             && strcmp(arguments, "-") == 0)
    {
        if (game_state != GAME_IN_PROGRESS)
        {
            send_frame(seq, "NACK", "NOGAME");
            return;
        }

        // End the current game.
        game_state = GAME_OVER;
        game_result = RESULT_RESIGNED;

        // Confirm that the game has ended.
        send_frame(seq, "OK", "GAMEOVER");
    }

    
    // Handle a client disconnecting.
    else if (strcmp(command, "DISCONNECT") == 0
             && strcmp(arguments, "-") == 0)
    {
        if (game_state == GAME_IN_PROGRESS)
        {
            // Do not silently abandon an active game.
            send_frame(seq, "NACK", "GAMEACTIVE");
            return;
        }

        // The client has left: go back to idle ("Waiting for game").
        reset_to_idle();

        // Acknowledge the disconnection.
        send_frame(seq, "OK", "DISCONNECT");
    }

    else
    {
        send_frame(seq, "NACK", "BADCMD");
    }
}

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_USART1_UART_Init();

  /* USER CODE BEGIN 2 */
  frameparser_init(&fp);
  lcd_init();
  __HAL_UART_ENABLE_IT(&huart1, UART_IT_RXNE);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */
    /* Recover if the UART receive buffer overflowed. */
    if (rx_overflow != 0U || rx_error != 0U)
    {
        /*
         * Temporarily disable the USART1 interrupt so the ISR
         * cannot modify the buffer indices while we reset them.
         */
        HAL_NVIC_DisableIRQ(USART1_IRQn);

        /* Discard buffered bytes because a frame may be incomplete. */
        rx_head = 0U;
        rx_tail = 0U;
        rx_overflow = 0U;
        rx_error = 0U;

        /* Allow USART1 receive interrupts again. */
        HAL_NVIC_EnableIRQ(USART1_IRQn);

        /* Discard any incomplete frame currently being parsed. */
        frameparser_init(&fp);
    }

    /* USER CODE BEGIN 3 */
	  while (rx_tail != rx_head) {
	      uint8_t b = rx_buf[rx_tail];
	      rx_tail = (uint8_t)((rx_tail + 1U) % RX_BUF_SIZE);

	      FrameStatus st = frameparser_push(&fp, b);
	      if (st == FINISHED) {
	          handle_frame(fp.data);
	          frameparser_init(&fp);
	      } else if (st == FRAME_ERROR) {
	    	  send_frame("0000", "NACK", "BADFRAME");
	      }
	  }

	  /* drop an incomplete frame after 500 ms of silence */
	  if (fp.started && (HAL_GetTick() - last_byte_tick) > 500U) {
	      frameparser_init(&fp);
	  }
    
    turn_leds_update();
    leds_update();
    lcd_update();
  }
  /* USER CODE END 3 */
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSI;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.HSICalibrationValue = RCC_HSICALIBRATION_DEFAULT;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_NONE;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_HSI;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_0) != HAL_OK)
  {
    Error_Handler();
  }
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_USART1;
  PeriphClkInit.Usart1ClockSelection = RCC_USART1CLKSOURCE_PCLK1;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}

/**
  * @brief USART1 Initialization Function
  * @param None
  * @retval None
  */
static void MX_USART1_UART_Init(void)
{

  /* USER CODE BEGIN USART1_Init 0 */

  /* USER CODE END USART1_Init 0 */

  /* USER CODE BEGIN USART1_Init 1 */

  /* USER CODE END USART1_Init 1 */
  huart1.Instance = USART1;
  huart1.Init.BaudRate = 115200;
  huart1.Init.WordLength = UART_WORDLENGTH_8B;
  huart1.Init.StopBits = UART_STOPBITS_1;
  huart1.Init.Parity = UART_PARITY_NONE;
  huart1.Init.Mode = UART_MODE_TX_RX;
  huart1.Init.HwFlowCtl = UART_HWCONTROL_NONE;
  huart1.Init.OverSampling = UART_OVERSAMPLING_16;
  huart1.Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
  huart1.AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
  if (HAL_UART_Init(&huart1) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN USART1_Init 2 */

  /* USER CODE END USART1_Init 2 */

}

/**
  * @brief GPIO Initialization Function
  * @param None
  * @retval None
  */
static void MX_GPIO_Init(void)
{
  /* USER CODE BEGIN MX_GPIO_Init_1 */

  /* USER CODE END MX_GPIO_Init_1 */

  /* GPIO Ports Clock Enable */
  __HAL_RCC_GPIOA_CLK_ENABLE();

  /* USER CODE BEGIN MX_GPIO_Init_2 */
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  
  GPIO_InitTypeDef led = {0};
  led.Pin   = GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_2 | GPIO_PIN_3
            | GPIO_PIN_4 | GPIO_PIN_5 | GPIO_PIN_6 | GPIO_PIN_7;
  led.Mode  = GPIO_MODE_OUTPUT_PP;
  led.Pull  = GPIO_NOPULL;
  led.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOB, &led);

  /* Red and green turn-indicator LEDs: PB10 and PB11. */
GPIO_InitTypeDef turn_led = {0};
turn_led.Pin = GPIO_PIN_10 | GPIO_PIN_11;
turn_led.Mode = GPIO_MODE_OUTPUT_PP;
turn_led.Pull = GPIO_NOPULL;
turn_led.Speed = GPIO_SPEED_FREQ_LOW;
HAL_GPIO_Init(GPIOB, &turn_led);

/* Start with both turn-indicator LEDs off. */
HAL_GPIO_WritePin(GPIOB, GPIO_PIN_10 | GPIO_PIN_11,GPIO_PIN_RESET);

/* No push-button inputs are configured. SW4 is the board's hardware reset
   (NRST): pressing it reboots the server into IDLE. Nothing else on the
   board can change the game; it is controlled only over the serial link. */

  GPIO_InitTypeDef lcd = {0};
  lcd.Mode  = GPIO_MODE_OUTPUT_PP;
  lcd.Pull  = GPIO_NOPULL;
  lcd.Speed = GPIO_SPEED_FREQ_LOW;

  lcd.Pin = GPIO_PIN_13 | GPIO_PIN_14 | GPIO_PIN_15;   /* BL, RS, E */
  HAL_GPIO_Init(GPIOC, &lcd);
  lcd.Pin = GPIO_PIN_8 | GPIO_PIN_9;                   /* D4, D5 */
  HAL_GPIO_Init(GPIOB, &lcd);
  lcd.Pin = GPIO_PIN_12 | GPIO_PIN_15;                 /* D6, D7 */
  HAL_GPIO_Init(GPIOA, &lcd);

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
void uart_rx_isr(void)
{
    uint32_t isr = USART1->ISR;

    if (isr & USART_ISR_RXNE) {
        uint8_t b = (uint8_t)USART1->RDR;
        last_byte_tick = HAL_GetTick();
        uint8_t next = (uint8_t)((rx_head + 1U) % RX_BUF_SIZE);
        if (next != rx_tail) {
            rx_buf[rx_head] = b;
            rx_head = next;
        } else {
            rx_overflow = 1U;
        }
    }

    if (isr & (USART_ISR_ORE | USART_ISR_FE | USART_ISR_NE))
    {
        /* Tell the main loop to discard potentially corrupted input. */
        rx_error = 1U;

        /* Clear the UART hardware error flags. */
        USART1->ICR = USART_ICR_ORECF | USART_ICR_FECF | USART_ICR_NCF;
    }
}
/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}
#ifdef USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */