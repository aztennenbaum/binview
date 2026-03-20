# binview

Simple tool to view raw binary data as raster images. Load multi-gigabyte files 
with minimal RAM. Inspired by GIMP raw import but optimized for large datasets.

## Usage

    ./binview.py [file1] [file2] ...

Opens files in separate tabs. Ctrl+W closes current tab.

## Features

- Memory efficient: reads only visible viewport from disk
- View state persistence (~/.binview/)
- Tabbed interface for multiple files
- Multiple data types: uint8/16/32/64, int8/16/32/64, float32/64
- Grayscale and RGB (interleaved) modes
- Byte alignment control for headers
- Endian swap for big-endian data
- Auto contrast or manual min/max range control
- Click-drag to pan, scrollbars for large images

## Requirements

Python 3, numpy, PIL/Pillow, tkinter (usually included)

    pip install numpy pillow

## Notes

RGB is interleaved not planar. Normalization stretches data range to [0,255] 
for display. Settings auto-save per file and restore on reopen.
