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