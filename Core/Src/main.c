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

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/
UART_HandleTypeDef huart1;

/* USER CODE BEGIN PV */
FrameParser fp;
uint32_t last_byte_tick = 0U;

#define RX_BUF_SIZE 128U
uint8_t rx_buf[RX_BUF_SIZE];
volatile uint8_t rx_head = 0U;
volatile uint8_t rx_tail = 0U;
volatile uint8_t rx_overflow = 0U;

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

/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
static void MX_GPIO_Init(void);
static void MX_USART1_UART_Init(void);
/* USER CODE BEGIN PFP */

/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

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

    // Construct the content protected by the CRC.
    int n = snprintf(body, sizeof(body), "%s|%s|%s",
                     seq, command, arguments);

    // Do not transmit a truncated or invalid frame.
    if (n < 0 || (size_t)n >= sizeof(body))
    {
        return;
    }

    // Calculate the CRC over SSSS|COMMAND|ARGUMENTS.
    uint16_t crc = protocol_crc16((const uint8_t *)body, (size_t)n);

    // Add the start marker, final separator, CRC and newline.
    int m = snprintf(out, sizeof(out), "@%s|%04X\n",
                     body, (unsigned)crc);

    if (m < 0 || (size_t)m >= sizeof(out))
    {
        return;
    }

    // Transmit the complete response over USART1.
    HAL_UART_Transmit(&huart1, (uint8_t *)out, (uint16_t)m, 100);
}


/*
 * Validate and handle a received protocol frame.
 *
 * For now, CONNECT is the only supported command. I will change it later:Mutalukanyi.
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

    // Remove the final separator and CRC from the string.
    d[len - 5U] = '\0';

    // Skip '@SSSS|' to reach the command.
    char *command = &d[6];

    // Find the separator between the command and arguments.
    char *separator = strchr(command, '|');

    if (separator == NULL)
    {
        send_frame(seq, "NACK", "BADFRAME");
        return;
    }

    // Split the frame into separate command and argument strings.
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
        // Clear all nine board cells.
        for (uint8_t i = 0U; i < 9U; i++)
        {
            game_board[i] = '.';
        }

        // Reset the game to its initial state.
        current_player = 'X';
        game_state = GAME_IN_PROGRESS;

        // Confirm that the new game has started.
        send_frame(seq, "OK", "-");
    }
    // Return the authoritative board state.
    else if (strcmp(command, "STATE") == 0
            && strcmp(arguments, "-") == 0)
    {
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

        /* legal move to the authoritative board. */
        game_board[move_index] = current_player;

        /* Alternate the turn. */
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
  __HAL_UART_ENABLE_IT(&huart1, UART_IT_RXNE);
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  while (1)
  {
    /* USER CODE END WHILE */
    /* Recover if the UART receive buffer overflowed. */
    if (rx_overflow != 0U)
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

        /* Allow USART1 receive interrupts again. */
        HAL_NVIC_EnableIRQ(USART1_IRQn);

        /* Discard any incomplete frame currently being parsed. */
        frameparser_init(&fp);
    }

    /* USER CODE BEGIN 3 */
	  while (rx_tail != rx_head) {
	      uint8_t b = rx_buf[rx_tail];
	      rx_tail = (uint8_t)((rx_tail + 1U) % RX_BUF_SIZE);
	      last_byte_tick = HAL_GetTick();

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

  /* USER CODE END MX_GPIO_Init_2 */
}

/* USER CODE BEGIN 4 */
void uart_rx_isr(void)
{
    uint32_t isr = USART1->ISR;

    if (isr & USART_ISR_RXNE) {
        uint8_t b = (uint8_t)USART1->RDR;
        uint8_t next = (uint8_t)((rx_head + 1U) % RX_BUF_SIZE);
        if (next != rx_tail) {
            rx_buf[rx_head] = b;
            rx_head = next;
        } else {
            rx_overflow = 1U;
        }
    }

    if (isr & (USART_ISR_ORE | USART_ISR_FE | USART_ISR_NE)) {
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
