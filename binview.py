#!/usr/bin/env python3
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog
import sys, os, json, hashlib

g_notebook=None
g_tabs={}  # tab_id -> tab_state dict
g_view_dir=os.path.expanduser("~/.binview")
g_repeat_id=None
g_repeat_func=None

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

def save_view_state(tab):
    """Save current view state for the file"""
    if not tab['fname']: return
    try:
        ensure_view_dir()
        state={
            'filepath': tab['fname'],
            'depth': tab['depth'].get(),
            'align': tab['align'].get(),
            'width': tab['width'].get(),
            'offset': tab['offset'].get(),
            'mode': tab['mode'].get(),
            'swap_endian': tab['swap_endian'].get(),
            'autocontrast': tab['autocontrast'].get(),
            'vmin': tab['vmin'].get(),
            'vmax': tab['vmax'].get(),
            'scroll_x': tab['canvas'].canvasx(0),
            'scroll_y': tab['canvas'].canvasy(0)
        }
        vfile=os.path.join(g_view_dir,file_hash(tab['fname'])+'.json')
        with open(vfile,'w') as f: json.dump(state,f,indent=2)
    except Exception as e: print(f"Save view error: {e}")

def load_view_state(fpath):
    """Load saved view state for the file"""
    try:
        vfile=os.path.join(g_view_dir,file_hash(fpath)+'.json')
        if not os.path.exists(vfile): return None
        with open(vfile,'r') as f: state=json.load(f)
        if state.get('filepath')==fpath: return state
    except Exception as e: print(f"Load view error: {e}")
    return None

def get_current_tab():
    """Get current tab state"""
    try:
        tab_id=g_notebook.select()
        return g_tabs.get(tab_id)
    except: return None

def close_current_tab():
    """Close the currently selected tab"""
    try:
        tab_id=g_notebook.select()
        if tab_id in g_tabs:
            tab=g_tabs[tab_id]
            save_view_state(tab)
            del g_tabs[tab_id]
        g_notebook.forget(tab_id)
    except: pass

def load_file(f):
    """Load file in new tab"""
    try:
        fsize=os.path.getsize(f)
        fname=os.path.basename(f)
        
        # create new tab
        tab_frame=ttk.Frame(g_notebook)
        tab_id=str(tab_frame)
        g_notebook.add(tab_frame,text=fname)
        g_notebook.select(tab_frame)
        
        # create tab state
        tab=create_tab_state(tab_frame,f,fsize)
        g_tabs[tab_id]=tab
        
        # load saved state
        state=load_view_state(f)
        if state:
            apply_view_state(tab,state)
        else:
            reload_data(tab)
    except Exception as e: print(f"Load file error: {e}")

def create_tab_state(parent,fname,fsize):
    """Create UI and state for a tab"""
    tab={'fname':fname,'fsize':fsize,'photo':None,
         'imgw':0,'imgh':0,'itemsize':0,'dtype':None,'drag_x':None,'drag_y':None}
    
    # controls frame
    ctrl=ttk.Frame(parent); ctrl.pack(side=tk.TOP,fill=tk.X,padx=5,pady=5)
    
    # depth/align/mode row
    ttk.Label(ctrl,text="Depth:").pack(side=tk.LEFT)
    tab['depth']=tk.StringVar(value="uint8")
    c=ttk.Combobox(ctrl,textvariable=tab['depth'],
        values=["uint8","uint16","uint32","uint64","int8","int16","int32","int64","float32","float64"],
        state="readonly",width=10)
    c.pack(side=tk.LEFT,padx=5)
    c.bind("<<ComboboxSelected>>",lambda e:reload_data(tab))
    
    ttk.Label(ctrl,text="Align:").pack(side=tk.LEFT,padx=(20,0))
    tab['align']=tk.IntVar(value=0)
    s=ttk.Spinbox(ctrl,from_=0,to=100000,width=8,textvariable=tab['align'],
                  command=lambda:reload_data(tab))
    s.pack(side=tk.LEFT,padx=5)
    s.bind('<KeyRelease>',lambda e:reload_data(tab))
    
    ttk.Label(ctrl,text="Mode:").pack(side=tk.LEFT,padx=(20,0))
    tab['mode']=tk.StringVar(value="Grayscale")
    mc=ttk.Combobox(ctrl,textvariable=tab['mode'],values=["Grayscale","RGB"],
                    state="readonly",width=10)
    mc.pack(side=tk.LEFT,padx=5)
    mc.bind("<<ComboboxSelected>>",lambda e:reload_data(tab))
    
    tab['swap_endian']=tk.BooleanVar(value=False)
    se=ttk.Checkbutton(ctrl,text="Swap Endian",variable=tab['swap_endian'],
                       command=lambda:reload_data(tab))
    se.pack(side=tk.LEFT,padx=(20,0))
    
    # contrast row
    ctrl2=ttk.Frame(parent); ctrl2.pack(side=tk.TOP,fill=tk.X,padx=5,pady=5)
    tab['autocontrast']=tk.BooleanVar(value=False)
    ac=ttk.Checkbutton(ctrl2,text="Auto Contrast",variable=tab['autocontrast'],
                       command=lambda:on_autocontrast_toggle(tab))
    ac.pack(side=tk.LEFT)
    
    ttk.Label(ctrl2,text="Min:").pack(side=tk.LEFT,padx=(20,0))
    tab['vmin']=tk.DoubleVar(value=0.0)
    tab['vmin_entry']=ttk.Entry(ctrl2,width=18)
    tab['vmin_entry'].pack(side=tk.LEFT,padx=5)
    tab['vmin_entry'].insert(0,"0.0")
    tab['vmin_entry'].bind('<Return>',lambda e:on_vmin_entry(tab,e))
    tab['vmin_entry'].bind('<FocusOut>',lambda e:on_vmin_entry(tab,e))
    
    ttk.Label(ctrl2,text="Max:").pack(side=tk.LEFT,padx=(10,0))
    tab['vmax']=tk.DoubleVar(value=255.0)
    tab['vmax_entry']=ttk.Entry(ctrl2,width=18)
    tab['vmax_entry'].pack(side=tk.LEFT,padx=5)
    tab['vmax_entry'].insert(0,"255.0")
    tab['vmax_entry'].bind('<Return>',lambda e:on_vmax_entry(tab,e))
    tab['vmax_entry'].bind('<FocusOut>',lambda e:on_vmax_entry(tab,e))
    
    # width row
    ctrl3=ttk.Frame(parent); ctrl3.pack(side=tk.TOP,fill=tk.X,padx=5,pady=5)
    ttk.Label(ctrl3,text="Width:").pack(side=tk.LEFT)
    mk_btn(ctrl3,"<<",lambda:adj_w(tab,-10))
    mk_btn(ctrl3,"<",lambda:adj_w(tab,-1))
    tab['width']=tk.IntVar(value=1280)
    tab['wentry']=ttk.Entry(ctrl3,width=10)
    tab['wentry'].pack(side=tk.LEFT,padx=5)
    tab['wentry'].insert(0,"1280")
    tab['wentry'].bind('<Return>',lambda e:on_width_entry(tab,e))
    tab['wentry'].bind('<FocusOut>',lambda e:on_width_entry(tab,e))
    mk_btn(ctrl3,">",lambda:adj_w(tab,1))
    mk_btn(ctrl3,">>",lambda:adj_w(tab,10))
    
    # offset row
    ctrl4=ttk.Frame(parent); ctrl4.pack(side=tk.TOP,fill=tk.X,padx=5,pady=5)
    ttk.Label(ctrl4,text="Offset:").pack(side=tk.LEFT)
    mk_btn(ctrl4,"<<",lambda:adj_o(tab,-100))
    mk_btn(ctrl4,"<",lambda:adj_o(tab,-1))
    tab['offset']=tk.IntVar(value=0)
    tab['oentry']=ttk.Entry(ctrl4,width=10)
    tab['oentry'].pack(side=tk.LEFT,padx=5)
    tab['oentry'].insert(0,"0")
    tab['oentry'].bind('<Return>',lambda e:on_offset_entry(tab,e))
    tab['oentry'].bind('<FocusOut>',lambda e:on_offset_entry(tab,e))
    mk_btn(ctrl4,">",lambda:adj_o(tab,1))
    mk_btn(ctrl4,">>",lambda:adj_o(tab,100))
    
    # canvas with scrollbars
    cf=ttk.Frame(parent); cf.pack(padx=5,pady=5,fill=tk.BOTH,expand=True)
    tab['canvas']=tk.Canvas(cf,bg='black',xscrollincrement=1,yscrollincrement=1)
    hbar=ttk.Scrollbar(cf,orient=tk.HORIZONTAL,command=tab['canvas'].xview)
    vbar=ttk.Scrollbar(cf,orient=tk.VERTICAL,command=tab['canvas'].yview)
    tab['canvas'].config(
        xscrollcommand=lambda *a:(hbar.set(*a),on_scroll(tab)),
        yscrollcommand=lambda *a:(vbar.set(*a),on_scroll(tab)))
    tab['canvas'].grid(row=0,column=0,sticky='nsew')
    hbar.grid(row=1,column=0,sticky='ew')
    vbar.grid(row=0,column=1,sticky='ns')
    cf.grid_rowconfigure(0,weight=1)
    cf.grid_columnconfigure(0,weight=1)
    tab['canvas'].bind('<Configure>',lambda e:update_view(tab))
    tab['canvas'].bind('<ButtonPress-1>',lambda e:on_drag_start(tab,e))
    tab['canvas'].bind('<B1-Motion>',lambda e:on_drag_move(tab,e))
    tab['canvas'].bind('<ButtonRelease-1>',lambda e:on_drag_end(tab,e))
    
    # status
    tab['status']=ttk.Label(parent,text="Loading...",relief=tk.SUNKEN)
    tab['status'].pack(side=tk.BOTTOM,fill=tk.X)
    
    return tab

def apply_view_state(tab,state):
    """Apply saved view state"""
    try:
        tab['depth'].set(state.get('depth','uint8'))
        tab['align'].set(state.get('align',0))
        tab['width'].set(state.get('width',1280))
        tab['offset'].set(state.get('offset',0))
        tab['mode'].set(state.get('mode','Grayscale'))
        tab['swap_endian'].set(state.get('swap_endian',False))
        tab['autocontrast'].set(state.get('autocontrast',False))
        
        dt=np.dtype(tab['depth'].get())
        dmin,dmax=get_default_range(dt)
        tab['vmin'].set(state.get('vmin',dmin))
        tab['vmax'].set(state.get('vmax',dmax))
        update_contrast_entries(tab)
        
        # reload data inline
        a=tab['align'].get()
        tab['dtype']=dt; tab['itemsize']=tab['dtype'].itemsize
        w=tab['width'].get(); o=tab['offset'].get(); m=tab['mode'].get()
        ch=3 if m=="RGB" else 1
        avail=(tab['fsize']-a)//tab['itemsize']
        w=max(1,min(avail,w)); o=max(0,min(avail-1,o))
        tab['width'].set(w); tab['offset'].set(o)
        tab['wentry'].delete(0,tk.END); tab['wentry'].insert(0,str(w))
        tab['oentry'].delete(0,tk.END); tab['oentry'].insert(0,str(o))
        avail_after=avail-o
        h=avail_after//(w*ch)
        tab['imgw']=w; tab['imgh']=h
        tab['canvas'].config(scrollregion=(0,0,w,h))
        
        # apply scroll
        def apply_scroll():
            sx=state.get('scroll_x',0); sy=state.get('scroll_y',0)
            if tab['imgw']>0 and tab['imgh']>0:
                tab['canvas'].xview_moveto(sx/tab['imgw'] if tab['imgw']>0 else 0)
                tab['canvas'].yview_moveto(sy/tab['imgh'] if tab['imgh']>0 else 0)
        tab['canvas'].after(100,apply_scroll)
        tab['canvas'].after_idle(lambda:update_view(tab))
    except Exception as e: print(f"Apply view error: {e}")

def update_contrast_entries(tab):
    tab['vmin_entry'].delete(0,tk.END)
    tab['vmin_entry'].insert(0,str(tab['vmin'].get()))
    tab['vmax_entry'].delete(0,tk.END)
    tab['vmax_entry'].insert(0,str(tab['vmax'].get()))

def reload_data(tab):
    try:
        a=tab['align'].get()
        old_dtype=tab['dtype']
        tab['dtype']=np.dtype(tab['depth'].get()); tab['itemsize']=tab['dtype'].itemsize
        if old_dtype!=tab['dtype']:
            dmin,dmax=get_default_range(tab['dtype'])
            tab['vmin'].set(dmin); tab['vmax'].set(dmax)
            update_contrast_entries(tab)
        w=tab['width'].get(); o=tab['offset'].get(); m=tab['mode'].get()
        ch=3 if m=="RGB" else 1
        avail=(tab['fsize']-a)//tab['itemsize']
        w=max(1,min(avail,w)); o=max(0,min(avail-1,o))
        tab['width'].set(w); tab['offset'].set(o)
        tab['wentry'].delete(0,tk.END); tab['wentry'].insert(0,str(w))
        tab['oentry'].delete(0,tk.END); tab['oentry'].insert(0,str(o))
        avail_after=avail-o
        h=avail_after//(w*ch)
        tab['imgw']=w; tab['imgh']=h
        tab['canvas'].config(scrollregion=(0,0,w,h))
        save_view_state(tab)
        tab['canvas'].after_idle(lambda:update_view(tab))
    except Exception as e: tab['status'].config(text=f"Error: {e}")

def read_visible_region(tab,x0,y0,x1,y1):
    if not tab['fname'] or tab['imgw']==0 or tab['imgh']==0: return None
    try:
        w=tab['imgw']; o=tab['offset'].get(); m=tab['mode'].get(); a=tab['align'].get()
        ch=3 if m=="RGB" else 1
        x0=max(0,min(w,x0)); y0=max(0,min(tab['imgh'],y0))
        x1=max(0,min(w,x1)); y1=max(0,min(tab['imgh'],y1))
        if x1<=x0 or y1<=y0: return None
        rw=x1-x0; rh=y1-y0
        if m=="RGB":
            buf=np.zeros((rh,rw,ch),dtype=tab['dtype'])
        else:
            buf=np.zeros((rh,rw),dtype=tab['dtype'])
        with open(tab['fname'],'rb') as f:
            for ly in range(rh):
                gy=y0+ly
                if m=="RGB":
                    line_offset=a+(o+gy*w*ch+x0*ch)*tab['itemsize']
                    f.seek(line_offset)
                    line_bytes=f.read(rw*ch*tab['itemsize'])
                    if len(line_bytes)==rw*ch*tab['itemsize']:
                        line_data=np.frombuffer(line_bytes,dtype=tab['dtype'])
                        buf[ly,:,:]=line_data.reshape((rw,ch))
                else:
                    line_offset=a+(o+gy*w+x0)*tab['itemsize']
                    f.seek(line_offset)
                    line_bytes=f.read(rw*tab['itemsize'])
                    if len(line_bytes)==rw*tab['itemsize']:
                        buf[ly,:]=np.frombuffer(line_bytes,dtype=tab['dtype'])
        # swap endian if requested
        if tab['swap_endian'].get() and tab['itemsize']>1:
            buf=buf.byteswap()
        return buf
    except Exception as e:
        tab['status'].config(text=f"Read error: {e}")
        return None

def update_view(tab,*args):
    if not tab['fname']: return
    cw=tab['canvas'].winfo_width(); ch=tab['canvas'].winfo_height()
    if cw<=1 or ch<=1: return
    x0=int(tab['canvas'].canvasx(0)); y0=int(tab['canvas'].canvasy(0))
    x1=int(tab['canvas'].canvasx(cw)); y1=int(tab['canvas'].canvasy(ch))
    id=read_visible_region(tab,x0,y0,x1,y1)
    if id is None: return
    try:
        if tab['autocontrast'].get():
            vmin=float(np.min(id)); vmax=float(np.max(id))
            tab['vmin'].set(vmin); tab['vmax'].set(vmax)
            update_contrast_entries(tab)
            if vmax>vmin:
                id=((id.astype(np.float64)-vmin)/(vmax-vmin))*255
            else:
                id=np.zeros_like(id,dtype=np.float64)
        else:
            vmin=tab['vmin'].get(); vmax=tab['vmax'].get()
            if vmax>vmin:
                id=np.clip(id.astype(np.float64),vmin,vmax)
                id=((id-vmin)/(vmax-vmin))*255
            else:
                id=np.zeros_like(id,dtype=np.float64)
        id=id.astype(np.uint8)
        m=tab['mode'].get()
        img=Image.fromarray(id,mode='RGB' if m=="RGB" else 'L')
        tab['photo']=ImageTk.PhotoImage(img)
        tab['canvas'].delete("all")
        tab['canvas'].create_image(x0,y0,anchor=tk.NW,image=tab['photo'],tags="img")
        w=tab['width'].get(); o=tab['offset'].get(); a=tab['align'].get()
        ac=" [AC]" if tab['autocontrast'].get() else ""
        se=" [SE]" if tab['swap_endian'].get() else ""
        tab['status'].config(text=f"{tab['imgw']}x{tab['imgh']} | view[{x0},{y0}:{x1},{y1}]{ac}{se} | {m} | off:{o} | {tab['dtype']}({tab['itemsize']}B) | a:{a} | {os.path.basename(tab['fname'])}")
    except Exception as e: tab['status'].config(text=f"Error: {e}")

def on_scroll(tab,*args):
    save_view_state(tab)
    tab['canvas'].after_idle(lambda:update_view(tab))

def on_drag_start(tab,e):
    tab['drag_x']=e.x; tab['drag_y']=e.y
    tab['canvas'].config(cursor="fleur")

def on_drag_move(tab,e):
    if tab['drag_x'] is None: return
    dx=tab['drag_x']-e.x; dy=tab['drag_y']-e.y
    tab['drag_x']=e.x; tab['drag_y']=e.y
    tab['canvas'].xview_scroll(int(dx),"units")
    tab['canvas'].yview_scroll(int(dy),"units")

def on_drag_end(tab,e):
    tab['drag_x']=None; tab['drag_y']=None
    tab['canvas'].config(cursor="")
    save_view_state(tab)

def on_width_entry(tab,e):
    try:
        v=int(tab['wentry'].get())
        if tab['fname']:
            a=tab['align'].get(); sz=tab['itemsize']
            avail=(tab['fsize']-a)//sz
            v=max(1,min(avail,v))
        else: v=max(1,v)
        tab['width'].set(v); reload_data(tab)
    except: pass

def on_offset_entry(tab,e):
    try:
        v=int(tab['oentry'].get())
        if tab['fname']:
            a=tab['align'].get(); sz=tab['itemsize']
            avail=(tab['fsize']-a)//sz
            v=max(0,min(avail-1,v))
        else: v=max(0,v)
        tab['offset'].set(v); reload_data(tab)
    except: pass

def on_vmin_entry(tab,e):
    try:
        v=float(tab['vmin_entry'].get())
        tab['vmin'].set(v)
        save_view_state(tab)
        update_view(tab)
    except: pass

def on_vmax_entry(tab,e):
    try:
        v=float(tab['vmax_entry'].get())
        tab['vmax'].set(v)
        save_view_state(tab)
        update_view(tab)
    except: pass

def adj_w(tab,d):
    v=tab['width'].get()+d
    if tab['fname']:
        a=tab['align'].get(); sz=tab['itemsize']
        avail=(tab['fsize']-a)//sz
        v=max(1,min(avail,v))
    else: v=max(1,v)
    tab['width'].set(v); reload_data(tab)

def adj_o(tab,d):
    if not tab['fname']: return
    v=tab['offset'].get()+d
    a=tab['align'].get(); sz=tab['itemsize']
    avail=(tab['fsize']-a)//sz
    v=max(0,min(avail-1,v))
    tab['offset'].set(v); reload_data(tab)

def on_autocontrast_toggle(tab):
    save_view_state(tab)
    update_view(tab)

def start_rep(root,f):
    global g_repeat_id,g_repeat_func
    stop_rep()
    g_repeat_func=f
    f()
    g_repeat_id=root.after(300,lambda:cont_rep(root,f))

def cont_rep(root,f):
    global g_repeat_id
    f()
    g_repeat_id=root.after(50,lambda:cont_rep(root,f))

def stop_rep():
    global g_repeat_id,g_repeat_func
    if g_repeat_id:
        g_repeat_func=None
        try:
            root=tk._default_root
            if root: root.after_cancel(g_repeat_id)
        except: pass
        g_repeat_id=None

def mk_btn(p,t,f):
    b=tk.Button(p,text=t,width=3)
    b.pack(side=tk.LEFT)
    root=p.winfo_toplevel()
    b.bind('<ButtonPress-1>',lambda e:start_rep(root,f))
    b.bind('<ButtonRelease-1>',lambda e:stop_rep())
    return b

def open_dlg():
    files=filedialog.askopenfilenames(title="Select Binary Files")
    for f in files:
        if f: load_file(f)

def on_closing(root):
    """Save all tab states before closing"""
    for tab in g_tabs.values():
        save_view_state(tab)
    root.destroy()

def main():
    global g_notebook
    ensure_view_dir()
    root=tk.Tk()
    root.title("Binary Image Viewer")
    root.protocol("WM_DELETE_WINDOW",lambda:on_closing(root))
    
    # bind Ctrl+W to close tab
    root.bind('<Control-w>',lambda e:close_current_tab())
    
    # menu/toolbar
    toolbar=ttk.Frame(root)
    toolbar.pack(side=tk.TOP,fill=tk.X,padx=5,pady=5)
    ttk.Button(toolbar,text="Open File(s)",command=open_dlg).pack(side=tk.LEFT)
    
    # notebook for tabs
    g_notebook=ttk.Notebook(root)
    g_notebook.pack(fill=tk.BOTH,expand=True,padx=5,pady=5)
    
    # load files from command line
    if len(sys.argv)>1:
        for f in sys.argv[1:]:
            load_file(f)
    
    root.mainloop()

if __name__=="__main__": main()
