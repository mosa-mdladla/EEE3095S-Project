/*
 * Author: Madzibandila Charmain
 * Date: 17 October 2026
 * Noughts and Crosses UART protocol.
 * UART configuration: 115200 baud, 8 data bits,
 * no parity, one stop bit.
 */

#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stddef.h>  
#include <stdint.h> 

#define PROTOCOL_BAUD_RATE          115200U
#define PROTOCOL_MAX_FRAME_LENGTH   64U
#define PROTOCOL_START_MARKER       '@'      // Marks the beginning of a new protocol frame.
#define PROTOCOL_FRAME_END          '\n'
#define PROTOCOL_SEQUENCE_LENGTH    4U
#define PROTOCOL_CRC_LENGTH         4U

#define PROTOCOL_BOARD_CELLS        9U
#define PROTOCOL_EMPTY_CELL         '.'
#define PROTOCOL_X_MARK             'X'
#define PROTOCOL_O_MARK             'O'

#define PROTOCOL_CRC_INITIAL_VALUE  0xFFFFU
#define PROTOCOL_CRC_POLYNOMIAL     0x1021U

/*
 * Calculate CRC over the specified bytes.
 * The caller decides which part of the frame
 * should be included in the checksum.
 */
uint16_t protocol_crc16(const uint8_t *data, size_t length);

#endif 