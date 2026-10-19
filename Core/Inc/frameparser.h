#ifndef FRAME_H
#define FRAME_H

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

#endif