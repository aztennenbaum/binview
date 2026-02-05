#!/usr/bin/env python3
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog
import sys, os

# Global state
g_raw_data = None
g_data = None
g_filename = None
g_photo = None
g_repeat_id = None

# UI state
g_depth_var = None
g_byte_align_var = None
g_width_var = None
g_offset_var = None
g_mode_var = None
g_canvas = None
g_status_label = None
g_file_label = None
g_width_label = None
g_offset_label = None
g_offset_slider = None
g_root = None

CANVAS_W = 1280
CANVAS_H = 960

def load_file(filename):
    global g_raw_data, g_filename
    try:
        with open(filename, 'rb') as f:
            g_raw_data = f.read()
        g_filename = filename
        g_file_label.config(text=os.path.basename(filename))
        reload_data()
    except Exception as e:
        g_status_label.config(text=f"Error: {e}")

def open_file_dialog():
    filename = filedialog.askopenfilename(title="Select Binary File")
    if filename:
        load_file(filename)

def reload_data():
    global g_data
    if g_raw_data is None:
        return
    
    try:
        byte_align = g_byte_align_var.get()
        dtype = np.dtype(g_depth_var.get())
        item_size = dtype.itemsize
        
        raw_bytes = np.frombuffer(g_raw_data, dtype=np.uint8)
        aligned_bytes = raw_bytes[byte_align:]
        truncated_size = (len(aligned_bytes) // item_size) * item_size
        aligned_bytes = aligned_bytes[:truncated_size]
        
        g_data = np.frombuffer(aligned_bytes, dtype=dtype)
        
        g_offset_slider.config(to=max(1, len(g_data)-1))
        g_offset_var.set(0)
        g_status_label.config(text=f"Loaded {len(g_data)} elements of {dtype} ({item_size} bytes) | Byte align: {byte_align}")
        
        update_image()
    except Exception as e:
        g_status_label.config(text=f"Error: {e}")

def update_image():
    global g_photo
    if g_data is None:
        return
    
    width = g_width_var.get()
    offset = g_offset_var.get()
    mode = g_mode_var.get()
    
    g_width_label.config(text=str(width))
    g_offset_label.config(text=str(offset))
    
    if width < 1:
        return
    
    data_slice = g_data[offset:]
    
    # Calculate height based on mode
    if mode == "RGB":
        channels = 3
        height = len(data_slice) // (width * channels)
    else:  # Grayscale
        channels = 1
        height = len(data_slice) // width
    
    if height < 1:
        g_status_label.config(text="Not enough data")
        return
    
    try:
        if mode == "RGB":
            img_data = data_slice[:height*width*channels].reshape((height, width, channels))
        else:
            img_data = data_slice[:height*width].reshape((height, width))
        
        # Normalize to 0-255
        if np.issubdtype(img_data.dtype, np.floating):
            img_data = np.clip(img_data, 0, 1) * 255
        elif np.issubdtype(img_data.dtype, np.signedinteger):
            info = np.iinfo(img_data.dtype)
            img_data = ((img_data.astype(np.float64) - info.min) / (info.max - info.min)) * 255
        else:
            img_data = (img_data.astype(np.float64) / np.iinfo(img_data.dtype).max) * 255
        
        img_data = img_data.astype(np.uint8)
        img = Image.fromarray(img_data, mode='RGB' if mode == "RGB" else 'L')
        g_photo = ImageTk.PhotoImage(img)
        
        g_canvas.delete("all")
        x = (CANVAS_W - img.width) // 2
        y = (CANVAS_H - img.height) // 2
        g_canvas.create_image(x, y, anchor=tk.NW, image=g_photo)
        
        dtype = g_data.dtype
        item_size = dtype.itemsize
        byte_align = g_byte_align_var.get()
        g_status_label.config(text=f"{width}x{height} | {mode} | Offset: {offset} | {dtype} ({item_size}B) | Align: {byte_align} | {os.path.basename(g_filename)}")
    except Exception as e:
        g_status_label.config(text=f"Error: {e}")

def adjust_width(delta):
    g_width_var.set(max(1, g_width_var.get() + delta))
    update_image()

def adjust_offset(delta):
    if g_data is None:
        return
    v = g_offset_var.get() + delta
    g_offset_var.set(max(0, min(len(g_data)-1, v)))
    update_image()

def start_repeat(func):
    global g_repeat_id
    stop_repeat()
    func()
    g_repeat_id = g_root.after(300, lambda: continue_repeat(func))

def continue_repeat(func):
    global g_repeat_id
    func()
    g_repeat_id = g_root.after(50, lambda: continue_repeat(func))

def stop_repeat():
    global g_repeat_id
    if g_repeat_id:
        g_root.after_cancel(g_repeat_id)
        g_repeat_id = None

def create_button(parent, text, press_func):
    btn = tk.Button(parent, text=text, width=3)
    btn.pack(side=tk.LEFT)
    btn.bind('<ButtonPress-1>', lambda e: start_repeat(press_func))
    btn.bind('<ButtonRelease-1>', lambda e: stop_repeat())
    return btn

def main():
    global g_depth_var, g_byte_align_var, g_width_var, g_offset_var, g_mode_var
    global g_canvas, g_status_label, g_file_label, g_width_label, g_offset_label
    global g_offset_slider, g_root
    
    g_root = tk.Tk()
    g_root.title("Binary Image Viewer")
    
    # File selection
    frame = ttk.Frame(g_root)
    frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
    ttk.Button(frame, text="Open File", command=open_file_dialog).pack(side=tk.LEFT)
    g_file_label = ttk.Label(frame, text="No file loaded")
    g_file_label.pack(side=tk.LEFT, padx=10)
    
    # Bit depth, alignment, and mode
    frame = ttk.Frame(g_root)
    frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
    ttk.Label(frame, text="Bit Depth:").pack(side=tk.LEFT)
    g_depth_var = tk.StringVar(value="uint8")
    combo = ttk.Combobox(frame, textvariable=g_depth_var,
                         values=["uint8", "uint16", "uint32", "uint64",
                                "int8", "int16", "int32", "int64",
                                "float32", "float64"],
                         state="readonly", width=10)
    combo.pack(side=tk.LEFT, padx=5)
    combo.bind("<<ComboboxSelected>>", lambda e: reload_data())
    
    ttk.Label(frame, text="Byte Align:").pack(side=tk.LEFT, padx=(20, 0))
    g_byte_align_var = tk.IntVar(value=0)
    spin = ttk.Spinbox(frame, from_=0, to=7, width=5,
                       textvariable=g_byte_align_var, command=reload_data)
    spin.pack(side=tk.LEFT, padx=5)
    spin.bind('<KeyRelease>', lambda e: reload_data())
    
    ttk.Label(frame, text="Mode:").pack(side=tk.LEFT, padx=(20, 0))
    g_mode_var = tk.StringVar(value="Grayscale")
    mode_combo = ttk.Combobox(frame, textvariable=g_mode_var,
                              values=["Grayscale", "RGB"],
                              state="readonly", width=10)
    mode_combo.pack(side=tk.LEFT, padx=5)
    mode_combo.bind("<<ComboboxSelected>>", lambda e: update_image())
    
    # Width controls
    frame = ttk.Frame(g_root)
    frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
    ttk.Label(frame, text="Width:").pack(side=tk.LEFT)
    create_button(frame, "<", lambda: adjust_width(-1))
    create_button(frame, "<<", lambda: adjust_width(-10))
    g_width_var = tk.IntVar(value=1280)
    slider = ttk.Scale(frame, from_=1, to=8192, variable=g_width_var,
                       command=lambda x: update_image(), orient=tk.HORIZONTAL, length=300)
    slider.pack(side=tk.LEFT, padx=5)
    create_button(frame, ">>", lambda: adjust_width(10))
    create_button(frame, ">", lambda: adjust_width(1))
    g_width_label = ttk.Label(frame, text="1280", width=6)
    g_width_label.pack(side=tk.LEFT, padx=5)
    
    # Offset controls
    frame = ttk.Frame(g_root)
    frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
    ttk.Label(frame, text="Offset:").pack(side=tk.LEFT)
    create_button(frame, "<", lambda: adjust_offset(-1))
    create_button(frame, "<<", lambda: adjust_offset(-100))
    g_offset_var = tk.IntVar(value=0)
    g_offset_slider = ttk.Scale(frame, from_=0, to=1000, variable=g_offset_var,
                                command=lambda x: update_image(), orient=tk.HORIZONTAL, length=300)
    g_offset_slider.pack(side=tk.LEFT, padx=5)
    create_button(frame, ">>", lambda: adjust_offset(100))
    create_button(frame, ">", lambda: adjust_offset(1))
    g_offset_label = ttk.Label(frame, text="0", width=10)
    g_offset_label.pack(side=tk.LEFT, padx=5)
    
    # Canvas
    g_canvas = tk.Canvas(g_root, width=CANVAS_W, height=CANVAS_H, bg='black')
    g_canvas.pack(padx=5, pady=5)
    
    # Status
    g_status_label = ttk.Label(g_root, text="Load a file to begin", relief=tk.SUNKEN)
    g_status_label.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Load file from command line if provided
    if len(sys.argv) > 1:
        load_file(sys.argv[1])
    
    g_root.mainloop()

if __name__ == "__main__":
    main()
