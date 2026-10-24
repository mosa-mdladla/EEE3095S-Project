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
        return ERROR;
    }
    
    if(!fp->started){   //reads bytes when the start marker is fed through
        auto byte_marker = (uint8_t)PROTOCOL_START_MARKER; 
        if(byte== byte_marker){
            fp->length = 0U;
            fp->started = true;
            fp->outOfBounds = false; 
            
            return data[fp->length++] = (char) byte;
        
        }
        return PARSING;
    }


    //end of frame is indicated by \n

    auto end_marker = (uint8_t) PROTOCOL_FRAME_END;

    if(byte == end_marker){
        if (fp -> overflow){
            frameparser_init(fp);
            return ERROR;
        }

        fp->data[fp->length] = '\0';
        fp->started = false;

        return FINISHED;
    }
    
}