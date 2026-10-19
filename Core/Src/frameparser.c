#include "frameparser.h"

//initialisation
void frameparser_init(FrameParser *fp){
    if(fp == NULL){
        return NULL;
    }
    else{
        fp->length = 0U;
        fp->started = false;
        fp->outOfBounds = false;
    }
}

//pushing byte to frame parser
FrameParser frameparser_push(FrameParser *fp, uint8_t byte){
    if(fp == NULL){
        return FrameStatus.ERROR;
    }
    else{
        if(!fp->started){
            auto byte_marker = (uint8_t)PROTOCOL_START_MARKER; 
            if(byte== byte_marker){
                fp->length = 0U;
                fp->started = true;
                fp->outOfBounds = false; 
                
                return data[fp->length++] = (char) byte;
            
            }
            return PARSING;
        }
    }
}