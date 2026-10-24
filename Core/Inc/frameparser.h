#ifndef FRAMEPARSER_H
#define FRAMEPARSER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "protocol.h"

typedef enum {PARSING, FINISHED, ERROR} FrameStatus;

//FrameParser struct to store all the bytes received thus far
typedef struct {
    char data[PROTOCOL_MAX_FRAME_LENGTH];
    size_t length;  //no. of bytes received
    bool started;   
    bool outOfBounds;   //does frame exceed allowed length
} FrameParser;
//initialisation of framer parser
void frameparser_init(FrameParser *fp);

//pushes/feeds a received byte into the parser
FrameStatus frameparser_push(FrameParser * fp, uint8_t byte);

//16 bits to accomodate for the longest status command and additional characters
typedef struct{
    uint16_t sequence;
    char command[16];
    char argument[16];
    uint16_t crc;
} DecodedFrame;



















#endif