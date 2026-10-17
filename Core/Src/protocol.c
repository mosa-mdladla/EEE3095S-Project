/*
 * Author: Madzibandila Mutalukanyi
 * Date: 17 October 2026
 *
 * Calculates the CRC-16/CCITT-FALSE checksum of a sequence of bytes.
 *
 * Cyclic Redundancy Check.
 *
 * When the computer sends a message, it calculates a checksum and
 * includes it in the frame. The STM32 calculates the checksum again.
 * If the two values differ, the message may have been corrupted.
 *
 * Initial value: 0xFFFF
 * Polynomial:    0x1021
 * No input reflection
 * No final XOR
 *
 */

#include "protocol.h"

uint16_t protocol_crc16(const uint8_t *data, size_t length){

    uint16_t crc = PROTOCOL_CRC_INITIAL_VALUE;

    size_t byte_index;           //tracks which input byte is currently being processed.
    uint8_t bit_index;          // tracks which of the eight bits in the current byte is being processed.

     if (data == NULL)
    {
        return 0U;
    }

     for (byte_index = 0U; byte_index < length; byte_index++)
    {
        /*
         * Moves the current byte into the upper eight bits of a
         * 16-bit value, then combine it with the CRC using XOR.
         */
        crc ^= (uint16_t)((uint16_t)data[byte_index] << 8U);

        /*
         * Processes all eight bits of the current byte.
         *
         * Each step updates the CRC according to its most
         * significant bit and the configured polynomial.
         */
        for (bit_index = 0U; bit_index < 8U; bit_index++) {
            /*
             * Checks whether bit 15, the most significant bit,
             * is currently set to 1.
             */
            if ((crc & 0x8000U) != 0U) {
                /*
                 * Shift the CRC one bit to the left, then XOR it
                 * with the CRC polynomial.
                 */
                crc = (uint16_t)((crc << 1U)
                                 ^ PROTOCOL_CRC_POLYNOMIAL);
            }
            else {
                crc = (uint16_t)(crc << 1U);
            }
        }
    }

    return crc;
}