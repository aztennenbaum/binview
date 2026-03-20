#!/usr/bin/env python3
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog
import sys, os, json, hashlib

g_fname=None; g_fsize=0; g_photo=None; g_repeat=None
g_depth=None; g_align=None; g_width=None; g_off=None; g_mode=None
g_canvas=None; g_status=None; g_flabel=None; g_wentry=None; g_oentry=None
g_root=None; g_imgw=0; g_imgh=0; g_itemsize=0; g_dtype=None
g_drag_x=None; g_drag_y=None; g_autocontrast=None
g_vmin=None; g_vmax=None; g_vmin_entry=None; g_vmax_entry=None
g_view_dir=os.path.expanduser("~/.binview")

def ensure_view_dir():
    if not os.path.exists(g_view_dir): os.makedirs(g_view_dir)

def file_hash(fpath):
    """Generate hash of filepath for view state filename"""
    return hashlib.sha256(fpath.encode()).hexdigest()[:16]

def get_default_range(dtype):
    """Get default min/max for data type"""
    if np.issubdtype(dtype,np.floating):
        return (0.0,1.0)
    elif np.issubdtype(dtype,np.signedinteger):
        inf=np.iinfo(dtype)
        return (float(inf.min),float(inf.max))
    else:
        return (0.0,float(np.iinfo(dtype).max))

def save_view_state():
    """Save current view state for the file"""
    if not g_fname: return
    try:
        ensure_view_dir()
        state={
            'filepath': g_fname,
            'depth': g_depth.get(),
            'align': g_align.get(),
            'width': g_width.get(),
            'offset': g_off.get(),
            'mode': g_mode.get(),
            'autocontrast': g_autocontrast.get(),
            'vmin': g_vmin.get(),
            'vmax': g_vmax.get(),
            'scroll_x': g_canvas.canvasx(0),
            'scroll_y': g_canvas.canvasy(0)
        }
        vfile=os.path.join(g_view_dir,file_hash(g_fname)+'.json')
        with open(vfile,'w') as f: json.dump(state,f,indent=2)
    except Exception as e: print(f"Save view error: {e}")

def load_view_state(fpath):
    """Load saved view state for the file"""
    try:
        vfile=os.path.join(g_view_dir,file_hash(fpath)+'.json')
        if not os.path.exists(vfile): return None
        with open(vfile,'r') as f: state=json.load(f)
        # verify filepath matches
        if state.get('filepath')==fpath: return state
    except Exception as e: print(f"Load view error: {e}")
    return None

def apply_view_state(state):
    """Apply saved view state to UI"""
    if not state: return
    try:
        g_depth.set(state.get('depth','uint8'))
        g_align.set(state.get('align',0))
        g_width.set(state.get('width',1280))
        g_off.set(state.get('offset',0))
        g_mode.set(state.get('mode','Grayscale'))
        g_autocontrast.set(state.get('autocontrast',False))
        # load or compute default range
        dt=np.dtype(g_depth.get())
        dmin,dmax=get_default_range(dt)
        g_vmin.set(state.get('vmin',dmin))
        g_vmax.set(state.get('vmax',dmax))
        update_contrast_entries()
        # apply scroll position after image is loaded
        def apply_scroll():
            sx=state.get('scroll_x',0); sy=state.get('scroll_y',0)
            if g_imgw>0 and g_imgh>0:
                g_canvas.xview_moveto(sx/g_imgw if g_imgw>0 else 0)
                g_canvas.yview_moveto(sy/g_imgh if g_imgh>0 else 0)
        g_root.after(100,apply_scroll)
    except Exception as e: print(f"Apply view error: {e}")

def load_file(f):
    global g_fname,g_fsize
    try:
        g_fname=f; g_fsize=os.path.getsize(f)
        g_flabel.config(text=os.path.basename(f))
        # load saved state before reloading data
        state=load_view_state(f)
        if state: apply_view_state(state)
        reload_data()
    except Exception as e: g_status.config(text=f"Error: {e}")

def open_dlg():
    f=filedialog.askopenfilename(title="Select Binary File")
    if f: load_file(f)

def update_contrast_entries():
    """Update contrast entry boxes from variables"""
    g_vmin_entry.delete(0,tk.END)
    g_vmin_entry.insert(0,str(g_vmin.get()))
    g_vmax_entry.delete(0,tk.END)
    g_vmax_entry.insert(0,str(g_vmax.get()))

def reload_data():
    global g_imgw,g_imgh,g_itemsize,g_dtype
    if not g_fname: return
    try:
        a=g_align.get(); 
        old_dtype=g_dtype
        g_dtype=np.dtype(g_depth.get()); g_itemsize=g_dtype.itemsize
        # reset contrast range if dtype changed
        if old_dtype!=g_dtype:
            dmin,dmax=get_default_range(g_dtype)
            g_vmin.set(dmin); g_vmax.set(dmax)
            update_contrast_entries()
        w=g_width.get(); o=g_off.get(); m=g_mode.get()
        ch=3 if m=="RGB" else 1
        avail=(g_fsize-a)//g_itemsize
        w=max(1,min(avail,w)); o=max(0,min(avail-1,o))
        g_width.set(w); g_off.set(o)
        g_wentry.delete(0,tk.END); g_wentry.insert(0,str(w))
        g_oentry.delete(0,tk.END); g_oentry.insert(0,str(o))
        avail_after=avail-o
        h=avail_after//(w*ch)
        g_imgw=w; g_imgh=h
        g_canvas.config(scrollregion=(0,0,w,h))
        g_status.config(text=f"Mapped {avail} elems {g_dtype}({g_itemsize}B) align:{a}")
        save_view_state()  # save after any change
        g_root.after_idle(update_view)
    except Exception as e: g_status.config(text=f"Error: {e}")

def read_visible_region(x0,y0,x1,y1):
    """Read only the visible region from file"""
    if not g_fname or g_imgw==0 or g_imgh==0: return None
    try:
        w=g_imgw; o=g_off.get(); m=g_mode.get(); a=g_align.get()
        ch=3 if m=="RGB" else 1
        # clamp to image bounds
        x0=max(0,min(w,x0)); y0=max(0,min(g_imgh,y0))
        x1=max(0,min(w,x1)); y1=max(0,min(g_imgh,y1))
        if x1<=x0 or y1<=y0: return None
        rw=x1-x0; rh=y1-y0
        # allocate buffer for visible region
        if m=="RGB":
            buf=np.zeros((rh,rw,ch),dtype=g_dtype)
        else:
            buf=np.zeros((rh,rw),dtype=g_dtype)
        # read line by line
        with open(g_fname,'rb') as f:
            for ly in range(rh):
                gy=y0+ly  # global y coordinate
                if m=="RGB":
                    # offset in file for this line segment
                    line_offset=a+(o+gy*w*ch+x0*ch)*g_itemsize
                    f.seek(line_offset)
                    line_bytes=f.read(rw*ch*g_itemsize)
                    if len(line_bytes)==rw*ch*g_itemsize:
                        line_data=np.frombuffer(line_bytes,dtype=g_dtype)
                        buf[ly,:,:]=line_data.reshape((rw,ch))
                else:
                    line_offset=a+(o+gy*w+x0)*g_itemsize
                    f.seek(line_offset)
                    line_bytes=f.read(rw*g_itemsize)
                    if len(line_bytes)==rw*g_itemsize:
                        buf[ly,:]=np.frombuffer(line_bytes,dtype=g_dtype)
        return buf
    except Exception as e:
        g_status.config(text=f"Read error: {e}")
        return None

def update_view(*args):
    global g_photo
    if not g_fname: return
    # get canvas dimensions
    cw=g_canvas.winfo_width(); ch=g_canvas.winfo_height()
    if cw<=1 or ch<=1: return
    # get visible region
    x0=int(g_canvas.canvasx(0)); y0=int(g_canvas.canvasy(0))
    x1=int(g_canvas.canvasx(cw)); y1=int(g_canvas.canvasy(ch))
    # read only visible portion
    id=read_visible_region(x0,y0,x1,y1)
    if id is None: return
    try:
        # normalize
        if g_autocontrast.get():
            # auto: stretch actual min->0, max->255
            vmin=float(np.min(id)); vmax=float(np.max(id))
            g_vmin.set(vmin); g_vmax.set(vmax)
            update_contrast_entries()
            if vmax>vmin:
                id=((id.astype(np.float64)-vmin)/(vmax-vmin))*255
            else:
                id=np.zeros_like(id,dtype=np.float64)
        else:
            # manual: use specified range
            vmin=g_vmin.get(); vmax=g_vmax.get()
            if vmax>vmin:
                id=np.clip(id.astype(np.float64),vmin,vmax)
                id=((id-vmin)/(vmax-vmin))*255
            else:
                id=np.zeros_like(id,dtype=np.float64)
        id=id.astype(np.uint8)
        m=g_mode.get()
        img=Image.fromarray(id,mode='RGB' if m=="RGB" else 'L')
        g_photo=ImageTk.PhotoImage(img)
        g_canvas.delete("all")
        g_canvas.create_image(x0,y0,anchor=tk.NW,image=g_photo,tags="img")
        w=g_width.get(); o=g_off.get(); a=g_align.get()
        ac=" [AC]" if g_autocontrast.get() else ""
        g_status.config(text=f"{g_imgw}x{g_imgh} | view[{x0},{y0}:{x1},{y1}]{ac} | {m} | off:{o} | {g_dtype}({g_itemsize}B) | a:{a} | {os.path.basename(g_fname)}")
    except Exception as e: g_status.config(text=f"Error: {e}")

def on_scroll(*args):
    save_view_state()  # save scroll position
    g_root.after_idle(update_view)

def on_drag_start(e):
    global g_drag_x,g_drag_y
    g_drag_x=e.x; g_drag_y=e.y
    g_canvas.config(cursor="fleur")

def on_drag_move(e):
    global g_drag_x,g_drag_y
    if g_drag_x is None: return
    dx=g_drag_x-e.x; dy=g_drag_y-e.y
    g_drag_x=e.x; g_drag_y=e.y
    g_canvas.xview_scroll(int(dx),"units")
    g_canvas.yview_scroll(int(dy),"units")

def on_drag_end(e):
    global g_drag_x,g_drag_y
    g_drag_x=None; g_drag_y=None
    g_canvas.config(cursor="")
    save_view_state()  # save after drag

def on_width_entry(e):
    try:
        v=int(g_wentry.get())
        if g_fname:
            a=g_align.get(); sz=g_itemsize
            avail=(g_fsize-a)//sz
            v=max(1,min(avail,v))
        else: v=max(1,v)
        g_width.set(v); reload_data()
    except: pass

def on_offset_entry(e):
    try:
        v=int(g_oentry.get())
        if g_fname:
            a=g_align.get(); sz=g_itemsize
            avail=(g_fsize-a)//sz
            v=max(0,min(avail-1,v))
        else: v=max(0,v)
        g_off.set(v); reload_data()
    except: pass

def on_vmin_entry(e):
    try:
        v=float(g_vmin_entry.get())
        g_vmin.set(v)
        save_view_state()
        update_view()
    except: pass

def on_vmax_entry(e):
    try:
        v=float(g_vmax_entry.get())
        g_vmax.set(v)
        save_view_state()
        update_view()
    except: pass

def adj_w(d): 
    v=g_width.get()+d
    if g_fname:
        a=g_align.get(); sz=g_itemsize
        avail=(g_fsize-a)//sz
        v=max(1,min(avail,v))
    else: v=max(1,v)
    g_width.set(v); reload_data()

def adj_o(d):
    if not g_fname: return
    v=g_off.get()+d
    a=g_align.get(); sz=g_itemsize
    avail=(g_fsize-a)//sz
    v=max(0,min(avail-1,v))
    g_off.set(v); reload_data()

def on_autocontrast_toggle():
    save_view_state()
    update_view()

def start_rep(f):
    global g_repeat
    stop_rep(); f()
    g_repeat=g_root.after(300,lambda:cont_rep(f))
def cont_rep(f):
    global g_repeat
    f(); g_repeat=g_root.after(50,lambda:cont_rep(f))
def stop_rep():
    global g_repeat
    if g_repeat: g_root.after_cancel(g_repeat); g_repeat=None

def mk_btn(p,t,f):
    b=tk.Button(p,text=t,width=3); b.pack(side=tk.LEFT)
    b.bind('<ButtonPress-1>',lambda e:start_rep(f))
    b.bind('<ButtonRelease-1>',lambda e:stop_rep())
    return b

def on_closing():
    """Save state before closing"""
    save_view_state()
    g_root.destroy()

def main():
    global g_depth,g_align,g_width,g_off,g_mode,g_canvas,g_status,g_flabel
    global g_wentry,g_oentry,g_root,g_autocontrast,g_vmin,g_vmax
    global g_vmin_entry,g_vmax_entry
    ensure_view_dir()
    g_root=tk.Tk(); g_root.title("Binary Image Viewer")
    g_root.protocol("WM_DELETE_WINDOW",on_closing)
    # file
    f=ttk.Frame(g_root); f.pack(side=tk.TOP,fill=tk.X,padx=5,pady=5)
    ttk.Button(f,text="Open File",command=open_dlg).pack(side=tk.LEFT)
    g_flabel=ttk.Label(f,text="No file"); g_flabel.pack(side=tk.LEFT,padx=10)
    # depth/align/mode
    f=ttk.Frame(g_root); f.pack(side=tk.TOP,fill=tk.X,padx=5,pady=5)
    ttk.Label(f,text="Depth:").pack(side=tk.LEFT)
    g_depth=tk.StringVar(value="uint8")
    c=ttk.Combobox(f,textvariable=g_depth,
        values=["uint8","uint16","uint32","uint64","int8","int16","int32","int64","float32","float64"],
        state="readonly",width=10)
    c.pack(side=tk.LEFT,padx=5); c.bind("<<ComboboxSelected>>",lambda e:reload_data())
    ttk.Label(f,text="Align:").pack(side=tk.LEFT,padx=(20,0))
    g_align=tk.IntVar(value=0)
    s=ttk.Spinbox(f,from_=0,to=100000,width=8,textvariable=g_align,command=reload_data)
    s.pack(side=tk.LEFT,padx=5); s.bind('<KeyRelease>',lambda e:reload_data())
    ttk.Label(f,text="Mode:").pack(side=tk.LEFT,padx=(20,0))
    g_mode=tk.StringVar(value="Grayscale")
    mc=ttk.Combobox(f,textvariable=g_mode,values=["Grayscale","RGB"],state="readonly",width=10)
    mc.pack(side=tk.LEFT,padx=5); mc.bind("<<ComboboxSelected>>",lambda e:reload_data())
    # contrast controls
    f=ttk.Frame(g_root); f.pack(side=tk.TOP,fill=tk.X,padx=5,pady=5)
    g_autocontrast=tk.BooleanVar(value=False)
    ac=ttk.Checkbutton(f,text="Auto Contrast",variable=g_autocontrast,command=on_autocontrast_toggle)
    ac.pack(side=tk.LEFT)
    ttk.Label(f,text="Min:").pack(side=tk.LEFT,padx=(20,0))
    g_vmin=tk.DoubleVar(value=0.0)
    g_vmin_entry=ttk.Entry(f,width=15)
    g_vmin_entry.pack(side=tk.LEFT,padx=5)
    g_vmin_entry.insert(0,"0.0")
    g_vmin_entry.bind('<Return>',on_vmin_entry)
    g_vmin_entry.bind('<FocusOut>',on_vmin_entry)
    ttk.Label(f,text="Max:").pack(side=tk.LEFT,padx=(10,0))
    g_vmax=tk.DoubleVar(value=255.0)
    g_vmax_entry=ttk.Entry(f,width=15)
    g_vmax_entry.pack(side=tk.LEFT,padx=5)
    g_vmax_entry.insert(0,"255.0")
    g_vmax_entry.bind('<Return>',on_vmax_entry)
    g_vmax_entry.bind('<FocusOut>',on_vmax_entry)
    # width
    f=ttk.Frame(g_root); f.pack(side=tk.TOP,fill=tk.X,padx=5,pady=5)
    ttk.Label(f,text="Width:").pack(side=tk.LEFT)
    mk_btn(f,"<<",lambda:adj_w(-10)); mk_btn(f,"<",lambda:adj_w(-1))
    g_width=tk.IntVar(value=1280)
    g_wentry=ttk.Entry(f,width=10); g_wentry.pack(side=tk.LEFT,padx=5)
    g_wentry.insert(0,"1280")
    g_wentry.bind('<Return>',on_width_entry)
    g_wentry.bind('<FocusOut>',on_width_entry)
    mk_btn(f,">",lambda:adj_w(1)); mk_btn(f,">>",lambda:adj_w(10))
    # offset
    f=ttk.Frame(g_root); f.pack(side=tk.TOP,fill=tk.X,padx=5,pady=5)
    ttk.Label(f,text="Offset:").pack(side=tk.LEFT)
    mk_btn(f,"<<",lambda:adj_o(-100)); mk_btn(f,"<",lambda:adj_o(-1))
    g_off=tk.IntVar(value=0)
    g_oentry=ttk.Entry(f,width=10); g_oentry.pack(side=tk.LEFT,padx=5)
    g_oentry.insert(0,"0")
    g_oentry.bind('<Return>',on_offset_entry)
    g_oentry.bind('<FocusOut>',on_offset_entry)
    mk_btn(f,">",lambda:adj_o(1)); mk_btn(f,">>",lambda:adj_o(100))
    # canvas with scrollbars
    cf=ttk.Frame(g_root); cf.pack(padx=5,pady=5,fill=tk.BOTH,expand=True)
    g_canvas=tk.Canvas(cf,bg='black',xscrollincrement=1,yscrollincrement=1)
    hbar=ttk.Scrollbar(cf,orient=tk.HORIZONTAL,command=g_canvas.xview)
    vbar=ttk.Scrollbar(cf,orient=tk.VERTICAL,command=g_canvas.yview)
    g_canvas.config(xscrollcommand=lambda *a:(hbar.set(*a),on_scroll()),
                    yscrollcommand=lambda *a:(vbar.set(*a),on_scroll()))
    g_canvas.grid(row=0,column=0,sticky='nsew')
    hbar.grid(row=1,column=0,sticky='ew')
    vbar.grid(row=0,column=1,sticky='ns')
    cf.grid_rowconfigure(0,weight=1)
    cf.grid_columnconfigure(0,weight=1)
    g_canvas.bind('<Configure>',update_view)
    g_canvas.bind('<ButtonPress-1>',on_drag_start)
    g_canvas.bind('<B1-Motion>',on_drag_move)
    g_canvas.bind('<ButtonRelease-1>',on_drag_end)
    # status
    g_status=ttk.Label(g_root,text="Load file",relief=tk.SUNKEN)
    g_status.pack(side=tk.BOTTOM,fill=tk.X)
    if len(sys.argv)>1: load_file(sys.argv[1])
    g_root.mainloop()

if __name__=="__main__": main()
