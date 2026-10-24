#include "frameparser.h"

// Reset the parser so that it is ready for a new frame.
void frameparser_init(FrameParser *fp)
{
    if (fp == NULL)
    {
        return;
    }

    fp->length = 0U;
    fp->started = false;
    fp->outOfBounds = false;
}

// Feed one received byte into the frame parser.
FrameStatus frameparser_push(FrameParser *fp, uint8_t byte)
{
    if (fp == NULL)
    {
        return FRAME_ERROR;
    }

    // Ignore bytes until the frame start marker '@' arrives.
    if (!fp->started)
    {
        if (byte == (uint8_t)PROTOCOL_START_MARKER)
        {
            fp->length = 0U;
            fp->started = true;
            fp->outOfBounds = false;

            fp->data[fp->length] = (char)byte;
            fp->length++;
        }

        return PARSING;
    }

    /*
     * If a new start marker arrives before the current frame ends,
     * discard the incomplete frame and start collecting the new one.
     */
    if (byte == (uint8_t)PROTOCOL_START_MARKER)
    {
        fp->length = 0U;
        fp->started = true;
        fp->outOfBounds = false;

        fp->data[fp->length] = (char)byte;
        fp->length++;

        return PARSING;
    }

    // A newline terminates the frame.
    if (byte == (uint8_t)PROTOCOL_FRAME_END)
    {
        if (fp->outOfBounds)
        {
            frameparser_init(fp);
            return FRAME_ERROR;
        }

        // Reserve the final array position for the null terminator.
        fp->data[fp->length] = '\0';
        fp->started = false;

        return FINISHED;
    }

    // Store the byte if there is room for it and a null terminator.
    if (fp->length < (PROTOCOL_MAX_FRAME_LENGTH - 1U))
    {
        fp->data[fp->length] = (char)byte;
        fp->length++;
    }
    else
    {
        // Keep discarding bytes until newline so the oversized
        // frame cannot be mistaken for a valid, shorter frame.
        fp->outOfBounds = true;
    }

    return PARSING;
}
