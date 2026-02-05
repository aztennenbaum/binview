# binview - Binary Image Viewer

A tool for viewing raw binary data as images, inspired by GIMP's raw image import. Useful for reverse engineering file formats and analyzing raw image data.

## Installation

Requires Python 3 with numpy and PIL:

```bash
pip install numpy pillow
```

tkinter is included with most Python installations.

## Usage

```bash
./binary_viewer.py [filename]
```

Open the GUI and use "Open File" button, or pass filename as argument.

## Features

**Data Types:**
- Unsigned: uint8, uint16, uint32, uint64
- Signed: int8, int16, int32, int64
- Float: float32, float64

**Display Modes:**
- Grayscale: single channel per pixel
- RGB: three channels (interleaved format)

**Controls:**
- Width: 1 to 8192 pixels
- Offset: skip N elements from start
- Byte align: 0-7 byte offset for misaligned data
- Canvas: 1280x960 pixel display

## How It Works

All data is normalized to 0-255 for display:
- Unsigned integers: scale from 0 to maximum value
- Signed integers: scale from minimum to maximum value
- Floating point: clip to [0,1] then scale to [0,255]

## Troubleshooting

**Random static:** Wrong width or data type. Try different values.

**Image shifted/offset:** Adjust byte alignment (0-7) or use offset to skip header.

**Horizontal tearing:** Width is slightly incorrect. Adjust by 1 pixel increments.

**Diagonal patterns:** Width is off by a factor. Try multiples or divisors of current width.

**RGB colors wrong:** Data may be BGR format, try different byte alignments.

## Implementation Notes

- Single file, ~200 lines of code
- Global state for simplicity
- numpy for efficient array operations
- File loaded once into memory
- Data reinterpreted via numpy views (no copying)
- UI updates triggered by events

## Limitations

- RGB mode supports interleaved format only (not planar)
- Uses system native byte order (no endian control)
- Maximum width: 8192 pixels
- Does not support compressed data
- Large files load entirely into memory
- 
