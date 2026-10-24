#include "frameparser.h"

//initialisation
void frameparser_init(FrameParser *fp){
    if(fp == NULL){
        return;
    }
    else{
        fp->length = 0U;
        fp->started = false;
        fp->outOfBounds = false;
    }
}

//pushing byte to frame parser
FrameStatus frameparser_push(FrameParser *fp, uint8_t byte){
    if(fp == NULL){
        return ERROR;
    }
    
    if(!fp->started){   //reads bytes when the start marker is fed through
        uint8_t byte_marker = (uint8_t)PROTOCOL_START_MARKER; 
        if(byte== byte_marker){
            fp->length = 0U;
            fp->started = true;
            fp->outOfBounds = false; 
            
            fp->data[fp->length++] = (char) byte;
        
        }
        return PARSING;
    }


    //end of frame is indicated by \n

    uint8_t end_marker = (uint8_t) PROTOCOL_FRAME_END;

    if(byte == end_marker){
        if (fp -> outOfBounds){
            frameparser_init(fp);
            return ERROR;
        }

        fp->data[fp->length] = '\0';
        fp->started = false;

        return FINISHED;
    }

    if(fp->length < (PROTOCOL_MAX_FRAME_LENGTH - 1)){
        fp->data[fp->length++] = (char) byte;
    }
    else{
        fp->outOfBounds=true;
    }
    return PARSING; //keeps reading until \n and then that particular if statement is executed
}