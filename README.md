# binview

Simple tool to view raw binary data as raster images. Inspired by GIMP raw 
import but optimized for large files.

## Usage

    ./binview.py [file1] [file2] ...

## Features

- Memory efficient: reads only visible viewport from disk
- View state persistence (~/.binview/)
- Tabbed interface for multiple files
- Multiple data types: uint8/16/32/64, int8/16/32/64, float32/64
- Grayscale and RGB (interleaved) modes
- Auto contrast and manual contrast adjustment
- Byte alignment control for headers
- Interactive width/offset adjustment
- Click-drag panning, scrollbars

## Requirements

Python 3, numpy, PIL/Pillow, tkinter (usually included)

    pip install numpy pillow

## Notes

Native endian only. Normalization stretches data range to [0,255] for display.
Custom min/max values persist until data type changes.
