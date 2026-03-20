# binview

Simple tool to view raw binary data as raster images, optimized for large files. Inspired by GIMP raw 
import.

## Usage

    ./binview.py [file]

## Features

- Memory efficient: reads only visible viewport from disk
- View state persistence (~/.binview/)
- Standard image viewer UI (scroll, pan, drag)
- Multiple data types: uint8/16/32/64, int8/16/32/64, float32/64
- Grayscale and RGB (interleaved) modes
- Byte alignment control for headers

## Requirements

Python 3, numpy, PIL/Pillow, tkinter (usually included)

    pip install numpy pillow

## Notes

Native endian only. Normalization stretches data range to [0,255] for display.
