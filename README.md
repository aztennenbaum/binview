# binview

View raw binary data as raster images. Memory efficient for large files.

## Usage

    ./binview.py [file]

## Features

- Memory efficient: reads only visible viewport from disk
- View state persistence (~/.binview/)
- Pan/scroll with mouse
- Data types: uint8/16/32/64, int8/16/32/64, float32/64
- Grayscale and interleaved RGB modes
- Manual and automatic contrast adjustment
- Byte alignment control for headers

## Requirements

Python 3, numpy, PIL/Pillow, tkinter (usually included)

    pip install numpy pillow

## Controls

**Width/Offset:** Image dimensions and header skip  
**Depth:** Data type selection  
**Align:** Byte offset for headers/padding  
**Mode:** Grayscale or RGB  
**Auto Contrast:** Stretch visible region min/max to [0,255]  
**Min/Max:** Manual contrast range (updated by auto contrast)

Settings auto-save per file.

## Notes

Native endian only. Useful for reverse engineering formats, analyzing scientific 
data, and viewing memory dumps.
