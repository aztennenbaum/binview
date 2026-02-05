# Binary Image Viewer

## Overview

Binary Image Viewer is a tool to visualize arbitrary binary data as images. It is useful for reverse engineering unknown file formats, inspecting raw image data, or exploring binary dumps.

The viewer supports multiple data types (8/16/32/64-bit integers and floats), both grayscale and RGB modes, and provides interactive controls for width, offset, and byte alignment adjustment.

## Features

- Support for multiple data types: uint8, uint16, uint32, uint64, int8, int16, int32, int64, float32, float64
- Grayscale and RGB display modes
- Byte alignment control (0-7 byte offset) for handling headers and misaligned data
- Interactive width adjustment from 1 to 8192 pixels
- Data offset control with element-level precision
- Real-time visualization with 1280x960 display canvas
- Command-line file loading support
- Cross-platform (requires Python 3 with NumPy, PIL, and Tkinter)

## Installation

Install the required Python packages:

```bash
pip install numpy pillow
```

Tkinter is included with most Python distributions.

## Usage

### Interactive Mode

Launch the viewer without arguments:

```bash
python3 binary_viewer.py
```

Use the "Open File" button to select a binary file.

### Command Line Mode

Provide a filename as an argument to load it automatically:

```bash
python3 binary_viewer.py data.bin
```

## Controls

### Data Type Selection

The **Bit Depth** dropdown selects how binary data is interpreted:
- **uint8/16/32/64**: Unsigned integers (most common for image data)
- **int8/16/32/64**: Signed integers
- **float32/64**: Floating-point values (for scientific data)

### Byte Alignment

The **Byte Align** control offsets the starting position by 0-7 bytes. This is useful for:
- Skipping small headers
- Finding correct alignment for multi-byte types
- Handling padding in structured data

For example, if 16-bit data appears as noise, try byte alignment values 0 and 1 to find the correct byte boundary.

### Display Mode

- **Grayscale**: Interprets each element as a single intensity value
- **RGB**: Interprets consecutive elements as R, G, B channels (interleaved format)

In RGB mode, three consecutive elements form one pixel. The image width must be set correctly or the colors will be misaligned.

### Width and Offset

**Width** determines how many pixels are in each row. Finding the correct width is essential:
- Use the slider for coarse adjustment
- Use arrow buttons for fine adjustment (1 pixel) or medium adjustment (10 pixels)
- Hold buttons for continuous adjustment

**Offset** skips the specified number of elements from the start. This is useful for:
- Navigating through the data
- Skipping file headers
- Finding embedded images in larger files

## Data Normalization

All data types are normalized to 0-255 for display:

- **Unsigned integers**: Linearly scaled from [0, type_max] to [0, 255]
- **Signed integers**: Linearly scaled from [type_min, type_max] to [0, 255]
- **Floating point**: Values are clipped to [0, 1] then scaled to [0, 255]

This ensures all data types can be visualized regardless of their native range.

## Examples

### Raw Grayscale Image (640x480, 8-bit)

```bash
python3 binary_viewer.py image.raw
```

Set Bit Depth to `uint8`, Mode to `Grayscale`, and Width to `640`.

### 16-bit Sensor Data

```bash
python3 binary_viewer.py sensor.dat
```

Set Bit Depth to `uint16`. If the image appears noisy or shifted, try Byte Align values 0 and 1.

### RGB Image (1920x1080, 8-bit)

```bash
python3 binary_viewer.py frame.rgb
```

Set Bit Depth to `uint8`, Mode to `RGB`, and Width to `1920`. The file should contain 1920×1080×3 = 6,220,800 bytes.

### Floating Point Data

```bash
python3 binary_viewer.py scientific.f32
```

Set Bit Depth to `float32`. Ensure values are in the range [0, 1] for proper visualization.

## Troubleshooting

### Image looks like random noise

- **Incorrect data type**: Try different bit depths, especially uint8 vs uint16
- **Incorrect width**: The width doesn't match the actual image dimensions
- **Compressed data**: The viewer cannot display compressed formats (JPEG, PNG, etc.)

### Image appears shifted or has diagonal patterns

- **Width is incorrect**: Adjust width until horizontal features align properly
- **Byte misalignment**: Try different byte alignment values (0-7)
- **Width is off by a small factor**: Use fine adjustment buttons

### RGB colors look wrong

- **Byte misalignment**: Try byte alignment values 0, 1, 2
- **Wrong channel order**: Data might be BGR or another format
- **Width is incorrect**: Must be exact in RGB mode

### Cannot see image on canvas

- **All zeros**: Data might be empty or encrypted
- **Data out of range**: For floats, values should be in [0, 1]
- **Need offset**: Image data might start after a header

## Implementation Notes

The viewer uses a functional approach with global state for simplicity. Binary data is loaded once and reinterpreted using NumPy views, making data type changes efficient. Image rendering uses PIL with Tkinter's Canvas widget.

Key design choices:
- **NumPy frombuffer**: Zero-copy reinterpretation of binary data
- **Byte alignment first**: Applied before type interpretation for correct results
- **Global state**: Simplifies event handling and avoids callback complexity
- **Button repeat**: 300ms initial delay, 50ms repeat for smooth interaction

## Performance

The viewer handles large files efficiently:
- File loading: O(n), single read operation
- Data reinterpretation: O(1), NumPy array view
- Image rendering: O(pixels), conversion to uint8
- UI updates: ~50ms for smooth interaction

Files up to several hundred megabytes can be handled on typical hardware.

## Limitations

- RGB mode supports only interleaved format (RGBRGBRGB...), not planar
- No endianness control (uses system native byte order)
- No support for RGBA or other channel counts
- Maximum width limited to 8192 pixels
- Compressed formats (JPEG, PNG) are not supported

## License

This software is released into the public domain. You can use it for any purpose without restriction.

## Author

Based on the common need for a simple binary visualization tool. Inspired by GIMP's raw image import but simplified for command-line workflows and reverse engineering tasks.
