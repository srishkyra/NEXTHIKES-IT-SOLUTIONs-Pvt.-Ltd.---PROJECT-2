
from __future__ import annotations
import ast, math, operator as op, random, re, statistics, tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable, Dict, Optional, Any

# ─────────────────────────────────────────────
# Font & Theme
# ─────────────────────────────────────────────
APP_FONT = "Segoe UI"

DARK = {
    "bg":"#000000","surface":"#111111","surface2":"#1C1C1E","surface3":"#2C2C2E",
    "sci":"#1E1E1F","sci_hover":"#2E2E30","grey":"#7C7C7C","grey_hover":"#8F8F8F",
    "text":"#F8F8F8","muted":"#A9A9A9","green":"#33D2BF","green_hover":"#1CC2B1",
    "green_dark":"#239184","green_darkhover":"#107A6F","border":"#343437",
    "danger":"#B65854","danger_hover":"#C85953","success":"#30D158",
    "num_hover":"#3A3A3C","sidebar":"#0A0A0A","sidebar_sel":"#1C1C1E","accent":"#FFA4A4",
}
LIGHT = {
    "bg":"#F2F2F7","surface":"#FFFFFF","surface2":"#E5E5EA","surface3":"#D1D1D6",
    "sci":"#E8E8ED","sci_hover":"#D4D4DA","grey":"#7C7C7C","grey_hover":"#8F8F8F",
    "text":"#1C1C1E","muted":"#6C6C70","green":"#1A9E8F","green_hover":"#0D7A6E",
    "green_dark":"#0B6B60","green_darkhover":"#094F47","border":"#C7C7CC",
    "danger":"#B65854","danger_hover":"#C85953","success":"#34C759",
    "num_hover":"#C8C8CE","sidebar":"#E0E0E5","sidebar_sel":"#FFFFFF","accent":"#FF6B6B",
}
T: dict = DARK


# ─────────────────────────────────────────────
# ProButton — theme-key-aware rounded button
# ─────────────────────────────────────────────
class ProButton(tk.Canvas):
    """
    bg_color / hover_color / fg_color accept EITHER:
      - a theme key string  e.g. "green", "surface3"
      - a literal hex color e.g. "#FF0000", "white"
    The draw method resolves keys via T at paint-time so theme changes work.
    """
    def __init__(self, master, text, command=None,
                 bg_color="surface3", hover_color="num_hover", fg_color="text",
                 font_size=16, font_weight="normal", radius=34, min_height=62, **kwargs):
        super().__init__(master, bg=master.cget("bg") if hasattr(master, "cget") else T["bg"], height=min_height, highlightthickness=0, bd=0, **kwargs)
        self.text       = text
        self.command    = command
        self.bg_key     = bg_color
        self.hover_key  = hover_color
        self.fg_key     = fg_color
        self.radius     = radius
        self.font_size  = font_size
        self.font_weight= font_weight
        self.hovered    = False
        self.configure(cursor="hand2")
        self.bind("<Configure>", lambda _: self._draw())
        self.bind("<Enter>",    lambda _: self._set_hover(True))
        self.bind("<Leave>",    lambda _: self._set_hover(False))
        self.bind("<Button-1>", lambda _: self.command() if self.command else None)

    @staticmethod
    def _resolve(key: str) -> str:
        return T.get(key, key)   # if not a theme key, treat as literal color

    def set_text(self, t: str):
        self.text = t; self._draw()

    def set_colors(self, bg_key: str, hover_key: str, fg_key: str):
        self.bg_key = bg_key; self.hover_key = hover_key; self.fg_key = fg_key
        self._draw()

    def refresh(self):
        self.configure(bg=T["bg"])
        self._draw()

    def _set_hover(self, on: bool):
        self.hovered = on; self._draw()

    def _round_rect(self, x1,y1,x2,y2,r,**kw):
        r = min(r, max(1,(y2-y1)//2), max(1,(x2-x1)//2))
        pts = [x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
               x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
               x1,y2, x1,y2-r, x1,y1+r, x1,y1]
        self.create_polygon(pts, smooth=True, **kw)

    def _draw(self):
        self.delete("all")
        w = max(self.winfo_width(), 20); h = max(self.winfo_height(), 20)
        bg = self._resolve(self.hover_key if self.hovered else self.bg_key)
        fg = self._resolve(self.fg_key)
        self.configure(bg=T.get("bg","#000000"))
        self._round_rect(2,2,w-2,h-2, self.radius, fill=bg, outline=T["border"])
        self.create_text(w/2, h/2, text=self.text, fill=fg,
                         font=(APP_FONT, self.font_size, self.font_weight),
                         justify="center")


# ─────────────────────────────────────────────
# Safe Evaluator & Engine
# ─────────────────────────────────────────────
class SafeEval(ast.NodeVisitor):
    def __init__(self, names, functions):
        self.names=names; self.functions=functions
        self.bin_ops={ast.Add:op.add,ast.Sub:op.sub,ast.Mult:op.mul,
                      ast.Div:op.truediv,ast.Mod:op.mod,ast.Pow:op.pow}
        self.unary_ops={ast.UAdd:op.pos,ast.USub:op.neg}
    def visit_Expression(self,n): return self.visit(n.body)
    def visit_Constant(self,n):
        if isinstance(n.value,(int,float)): return float(n.value)
        raise ValueError("Numbers only")
    def visit_Name(self,n):
        if n.id in self.names: return float(self.names[n.id])
        raise ValueError(f"Unknown: {n.id}")
    def visit_BinOp(self,n):
        ot=type(n.op)
        if ot not in self.bin_ops: raise ValueError("Unsupported op")
        l,r=self.visit(n.left),self.visit(n.right)
        if isinstance(n.op,ast.Pow) and abs(r)>10000: raise ValueError("Power too large")
        return float(self.bin_ops[ot](l,r))
    def visit_UnaryOp(self,n):
        ot=type(n.op)
        if ot not in self.unary_ops: raise ValueError("Unsupported unary")
        return float(self.unary_ops[ot](self.visit(n.operand)))
    def visit_Call(self,n):
        if not isinstance(n.func,ast.Name): raise ValueError("Bad call")
        fn=n.func.id
        if fn not in self.functions: raise ValueError(f"Unknown fn: {fn}")
        result=self.functions[fn](*[self.visit(a) for a in n.args])
        return result if isinstance(result,(int,float)) else float(result)
    def generic_visit(self,n): raise ValueError(f"Unsupported: {type(n).__name__}")


class Engine:
    @staticmethod
    def _fact(v):
        if v<0 or int(v)!=v: raise ValueError("Need non-negative integer")
        if v>170: raise ValueError("Too large (max 170)")
        return math.factorial(int(v))
    @staticmethod
    def _root(r,x):
        if r==0: raise ValueError("Root=0")
        if x<0 and int(r)%2==0: raise ValueError("Even root of negative")
        return (-((-x)**(1/r))) if x<0 else x**(1/r)
    @staticmethod
    def _preprocess(e):
        e=e.strip()
        for a,b in [("×","*"),("÷","/"),("−","-"),("π","pi"),("𝑒","e"),("^","**"),("√","sqrt")]:
            e=e.replace(a,b)
        e=re.sub(r'(\d+(?:\.\d+)?)[eE]([+-]?\d+)',lambda m:str(float(m.group(0))),e)
        e=re.sub(r'(\d|\))([A-Za-z\(])',r'\1*\2',e)
        e=re.sub(r"(?<![A-Za-z_])(\d+(?:\.\d+)?)%",r"(\1/100)",e)
        pat=re.compile(r"(\d+(?:\.\d+)?)!")
        while pat.search(e): e=pat.sub(r"factorial(\1)",e)
        return e
    @staticmethod
    def evaluate(expr, angle="RAD"):
        expr=expr.strip()
        if not expr: return "0"
        def trig(f): return lambda x:f(math.radians(x)) if angle=="DEG" else f(x)
        def itrig(f): return lambda x:math.degrees(f(x)) if angle=="DEG" else f(x)
        fns={
            "sin":trig(math.sin),"cos":trig(math.cos),"tan":trig(math.tan),
            "asin":itrig(math.asin),"acos":itrig(math.acos),"atan":itrig(math.atan),
            "sinh":math.sinh,"cosh":math.cosh,"tanh":math.tanh,
            "asinh":math.asinh,"acosh":math.acosh,"atanh":math.atanh,
            "ln":math.log,"log":math.log10,"log10":math.log10,"log2":math.log2,
            "sqrt":math.sqrt,"cbrt":lambda x:math.copysign(abs(x)**(1/3),x),
            "root":Engine._root,"exp":math.exp,"abs":abs,"factorial":Engine._fact,
            "ceil":math.ceil,"floor":math.floor,"round":round,
            "gcd":lambda a,b:math.gcd(int(a),int(b)),"lcm":lambda a,b:math.lcm(int(a),int(b)),
        }
        names={"pi":math.pi,"e":math.e,"rand":random.random(),"inf":math.inf}
        try:
            proc=Engine._preprocess(expr)
            res=SafeEval(names,fns).visit(ast.parse(proc,mode="eval"))
            if math.isnan(res) or math.isinf(res): return "Math Error"
            if isinstance(res,float) and abs(res)>1e15: return "Math Error"
            if abs(res-round(res))<1e-12: return str(int(round(res)))
            return f"{res:.12g}"
        except ZeroDivisionError: return "Division by Zero"
        except Exception as ex: return f"Error: {ex}"


# ─────────────────────────────────────────────
# Converter data
# ─────────────────────────────────────────────
@dataclass(frozen=True)
class CatData:
    name:str; units:Dict[str,float]; kind:str="linear"; note:str=""

CONVERTERS={
    "Length":   CatData("Length",{"Kilometer":1000,"Meter":1,"Centimeter":0.01,"Millimeter":0.001,
                    "Mile":1609.344,"Yard":0.9144,"Foot":0.3048,"Inch":0.0254,"Nautical Mile":1852}),
    "Weight":   CatData("Weight",{"Tonne":1000,"Kilogram":1,"Gram":0.001,"Milligram":1e-6,
                    "Pound":0.45359237,"Ounce":0.028349523,"Stone":6.35029}),
    "Temperature": CatData("Temperature",{"Celsius":1,"Fahrenheit":1,"Kelvin":1},kind="temperature"),
    "Area":     CatData("Area",{"Sq Kilometer":1e6,"Sq Meter":1,"Hectare":1e4,
                    "Acre":4046.856,"Sq Foot":0.092903,"Sq Inch":6.4516e-4,"Sq Mile":2589988.1}),
    "Volume":   CatData("Volume",{"Cubic Meter":1,"Liter":0.001,"Milliliter":1e-6,
                    "Gallon(US)":0.003785412,"Cup(US)":2.365882e-4,"Cubic Foot":0.028316847}),
    "Speed":    CatData("Speed",{"m/s":1,"km/h":1/3.6,"mph":0.44704,"Knot":0.514444,"ft/s":0.3048}),
    "Pressure": CatData("Pressure",{"Pascal":1,"Kilopascal":1000,"Bar":1e5,
                    "Atmosphere":101325,"PSI":6894.757,"mmHg":133.322}),
    "Power":    CatData("Power",{"Watt":1,"Kilowatt":1000,"Horsepower":745.700,"BTU/hr":0.293071}),
    "Energy":   CatData("Energy",{"Joule":1,"Kilojoule":1000,"Calorie":4.184,
                    "Kilocalorie":4184,"kWh":3600000,"BTU":1055.056}),
    "Number System": CatData("Number System",{"Binary":2,"Octal":8,"Decimal":10,"Hexadecimal":16},kind="number"),
    "Currency": CatData("Currency",
                {"USD":1.0,"INR":0.012,"EUR":1.08,"GBP":1.27,"CAD":0.74,
                 "AUD":0.65,"JPY":0.0067,"AED":0.27,"SAR":0.27},
                note="⚠ Offline demo rates — USD as base."),
}

LIVE_RATES: dict = {}
LIVE_RATES_TIMESTAMP: float = 0.0
EXCHANGE_API_KEY = "99192cb610c9278c5b726ec2"

def fetch_live_rates() -> bool:
    """Fetch live USD-base rates. Returns True on success."""
    import urllib.request, json, time
    global LIVE_RATES, LIVE_RATES_TIMESTAMP
    try:
        url = f"https://v6.exchangerate-api.com/v6/{EXCHANGE_API_KEY}/latest/USD"
        try:
            import ssl, certifi # type: ignore
            ctx = ssl.create_default_context(cafile=certifi.where())
            resp_cm = urllib.request.urlopen(url, timeout=5, context=ctx)
        except Exception:
            resp_cm = urllib.request.urlopen(url, timeout=5)
        with resp_cm as resp:
            data = json.loads(resp.read().decode())
        if data.get("result") == "success":
            LIVE_RATES = data["conversion_rates"]
            LIVE_RATES_TIMESTAMP = time.time()
            return True
    except:
        pass
    return False

def conv_temp(v,fr,to):
    c = v if fr=="Celsius" else (v-32)*5/9 if fr=="Fahrenheit" else v-273.15
    if to=="Celsius": return c
    if to=="Fahrenheit": return c*9/5+32
    return c+273.15

def conv_num(v,fr,to):
    bases={"Binary":2,"Octal":8,"Decimal":10,"Hexadecimal":16}
    try:
        d=int(v.strip(),bases[fr])
        if to=="Binary": return bin(d)[2:]
        if to=="Octal":  return oct(d)[2:]
        if to=="Hexadecimal": return hex(d)[2:].upper()
        return str(d)
    except: return "Invalid input"


# ─────────────────────────────────────────────
# Helper: themed Label / Entry / Frame builders
# ─────────────────────────────────────────────
def tframe(parent, **kw):
    return tk.Frame(parent, bg=T["bg"], **kw)

def tlabel(parent, text="", size=10, bold=False, muted=False, fg_key=None, **kw):
    fg = T[fg_key] if fg_key else (T["muted"] if muted else T["text"])
    wt = "bold" if bold else "normal"
    return tk.Label(parent, text=text, bg=T["bg"], fg=fg,
                    font=(APP_FONT,size,wt), **kw)

def tentry(parent, var, size=12):
    e = tk.Entry(parent, textvariable=var, bg=T["surface2"], fg=T["text"],
                    insertbackground=T["text"], relief="flat",
                    font=(APP_FONT,size), highlightthickness=1,
                    highlightcolor=T["green"], highlightbackground=T["border"])
    e.bind("<Button-1>", lambda _: e.focus_set())
    return e

def tresult(parent, var, size=12):
    outer = tk.Frame(parent, bg=T["border"], padx=1, pady=1)
    tk.Label(outer, textvariable=var, bg=T["surface3"], fg=T["green"],
             font=(APP_FONT, size, "bold"), padx=14, pady=12,
             anchor="w", justify="left", wraplength=480).pack(fill="both", expand=True)
    return outer

def calc_btn(parent, label, cmd, app=None):
    if app is not None:
        app.current_calc_fn = cmd
    return ProButton(parent, label, command=cmd,
                     bg_color="green", hover_color="green_hover",
                     fg_color="text", font_size=12, min_height=40, radius=20)


# ─────────────────────────────────────────────
# Main Application
# ─────────────────────────────────────────────
class UltraCalc:
    # Fixed dimensions
    WIN_W  = 900
    WIN_H  = 615
    SIDE_W = 200

    MODES = [
        ("Basic",        "🔢"),
        ("Scientific",   "∫"),
        ("Statistics",   "σ"),
        ("Health",       "♥"),
        ("Finance",      "₹"),
        ("Trigonometry", "△"),
        ("Programming",  "</>"),
        ("Eq Solver",    "=x"),
        ("Converter",    "⇄"),
    ]

    # ── init ─────────────────────────────────
    def __init__(self, root: tk.Tk):
        global T
        self.root = root
        self.root.title("Next Hikes IT Solutions — Calculator")
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}")
        self.root.resizable(False, False)
        self.root.configure(bg=T["bg"])

        # State
        self.is_dark      = True
        self.current_mode = "Basic"
        self.angle_mode   = "DEG"
        self.memory       = 0.0
        self.history: list[str] = []
        self.second_mode  = False
        self.current_calc_fn: Optional[Callable] = None
        self.sci_btns: Dict[str, ProButton] = {}

        # Shared display StringVars (ONLY used by Basic & Scientific)
        self.expression = tk.StringVar(value="")
        self.display    = tk.StringVar(value="0")
        self.preview    = tk.StringVar(value="Ready")

        # Widget registries for theme refresh
        self._labels:  list[tk.Label]  = []
        self._frames:  list[tk.Frame]  = []

        self._style_setup()
        self._build()
        self._bind_keys()

    # ── TTK style ────────────────────────────
    def _style_setup(self):
        self.style = ttk.Style()
        try: self.style.theme_use("clam")
        except: pass
        self._apply_combo_style()

    def _apply_combo_style(self):
        self.style.configure("C.TCombobox",
            fieldbackground=T["surface2"], background=T["surface2"],
            foreground=T["text"], arrowcolor=T["text"],
            selectbackground=T["surface2"], selectforeground=T["text"])
        self.style.map("C.TCombobox", fieldbackground=[("readonly", T["surface2"])])

    # ── Layout ───────────────────────────────
    def _build(self):
        self.root.columnconfigure(0, minsize=self.SIDE_W, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()

    # ── Sidebar ──────────────────────────────
    def _build_sidebar(self):
        self.sidebar = tk.Frame(self.root, bg=T["sidebar"], width=self.SIDE_W)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.columnconfigure(0, weight=1)
        self.sidebar.rowconfigure(1, weight=1)

        # Brand
        brand = tk.Label(self.sidebar, text="Calculator",
                         bg=T["sidebar"], fg=T["green"],
                         font=(APP_FONT,20,"bold"), justify="center")
        brand.grid(row=0, column=0, pady=(16,10))
        self._labels.append(brand)
        self._sb_brand = brand

        # Nav frame
        nav = tk.Frame(self.sidebar, bg=T["sidebar"])
        nav.grid(row=1, column=0, sticky="nsew")
        nav.columnconfigure(0, weight=1)
        self._sb_nav = nav
        self._sb_nav_frame = nav

        self.sidebar_btns: Dict[str, tk.Label] = {}
        for i,(name,icon) in enumerate(self.MODES):
            f = tk.Frame(nav, bg=T["sidebar"])
            f.grid(row=i, column=0, sticky="ew", padx=6, pady=1)
            lbl = tk.Label(f, text=f"{icon}  {name}", bg=T["sidebar"],
                           fg=T["text"], font=(APP_FONT,11),
                           justify="center", padx=20, pady=18, cursor="hand2")
            lbl.pack(fill="x")
            lbl.bind("<Button-1>", lambda _,n=name: self.switch_mode(n))
            lbl.bind("<Enter>",    lambda _,l=lbl: self._sb_hover(l, True))
            lbl.bind("<Leave>",    lambda _,l=lbl: self._sb_hover(l, False))
            self.sidebar_btns[name] = lbl

        # Bottom area
        self._sb_bot = tk.Frame(self.sidebar, bg=T["sidebar"])
        self._sb_bot.grid(row=2, column=0, sticky="ew", padx=8, pady=10)
        bot = self._sb_bot

        self.hist_btn = ProButton(bot, "◷  History", command=self.open_history,
            bg_color="surface2", hover_color="sci_hover", fg_color="text",
            font_size=11, min_height=34, radius=17)
        self.hist_btn.pack(fill="x")

        self._highlight_sidebar("Basic")

    def _sb_hover(self, lbl, entering):
        name = next((n for n,l in self.sidebar_btns.items() if l==lbl), None)
        is_sel = (name == self.current_mode)
        if entering:
            lbl.configure(bg=T["sci_hover"])
        else:
            lbl.configure(bg=T["sidebar_sel"] if is_sel else T["sidebar"])

    def _highlight_sidebar(self, mode):
        for name,lbl in self.sidebar_btns.items():
            sel = (name==mode)
            lbl.configure(
                bg=T["sidebar_sel"] if sel else T["sidebar"],
                fg=T["green"] if sel else T["text"],
                font=(APP_FONT,10,"bold" if sel else "normal"))

    # ── Main area ────────────────────────────
    def _build_main(self):
        self.main_frame = tk.Frame(self.root, bg=T["bg"])
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(2, weight=1)
        self._frames.append(self.main_frame)

        self._build_topbar()
        self._build_display()

        self.content = tk.Frame(self.main_frame, bg=T["bg"])
        self.content.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0,12))
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)
        self._frames.append(self.content)

        self.switch_mode("Basic")

    def _build_topbar(self):
        bar = tk.Frame(self.main_frame, bg=T["bg"])
        bar.grid(row=0, column=0, sticky="ew", padx=14, pady=(10,2))
        self._frames.append(bar)

        self.lbl_mode_name = tk.Label(bar, text="Basic Calculator",
            bg=T["bg"], fg=T["text"], font=(APP_FONT,13,"bold"))
        self.lbl_mode_name.pack(side="left")
        self._labels.append(self.lbl_mode_name)

        self.rad_btn = ProButton(bar, self.angle_mode, command=self.toggle_angle,
            bg_color="surface2", hover_color="sci_hover", fg_color="green",
            font_size=11, font_weight="bold", min_height=30, radius=15, width=58)
        self.rad_btn.pack(side="right", padx=(4,0))

        self.copy_btn = ProButton(bar, "⎘ Copy", command=self.copy_result,
            bg_color="surface2", hover_color="sci_hover",
            fg_color="text", font_size=10, min_height=30,
            radius=15, width=70)
        self.copy_btn.pack(side="right", padx=(4,0))

        self.theme_btn = ProButton(bar, "☀", command=self.toggle_theme,
            bg_color="surface2", hover_color="sci_hover", fg_color="text",
            font_size=11, font_weight="bold", min_height=30, radius=15, width=58)
        self.theme_btn.pack(side="right", padx=(4,0))

    def _build_display(self):
        df = tk.Frame(self.main_frame, bg=T["bg"])
        df.grid(row=1, column=0, sticky="ew", padx=14, pady=(0,6))
        self._frames.append(df)

        self.lbl_expr = tk.Label(df, textvariable=self.expression,
            bg=T["bg"], fg=T["muted"], font=(APP_FONT,11),
            anchor="e", justify="right", wraplength=640, height=1)
        self.lbl_expr.pack(fill="x")
        self._labels.append(self.lbl_expr)

        self.lbl_disp = tk.Label(df, textvariable=self.display,
            bg=T["bg"], fg=T["text"], font=(APP_FONT,42,"bold"),
            anchor="e", justify="right", wraplength=650)
        self.display.trace_add("write", self._auto_resize_display)

        self.lbl_disp.pack(fill="x")
        self._labels.append(self.lbl_disp)

        srow = tk.Frame(df, bg=T["bg"])
        srow.pack(fill="x")
        self._frames.append(srow)

        self.lbl_angle = tk.Label(srow, text=f"  {self.angle_mode}",
            bg=T["bg"], fg=T["green"], font=(APP_FONT,9,"bold"))
        self.lbl_angle.pack(side="left")
        self._labels.append(self.lbl_angle)

        self.lbl_mem = tk.Label(srow, text="",
            bg=T["bg"], fg=T["success"], font=(APP_FONT,9,"bold"))
        self.lbl_mem.pack(side="left", padx=6)
        self._labels.append(self.lbl_mem)

        self.lbl_prev = tk.Label(srow, textvariable=self.preview,
            bg=T["bg"], fg=T["muted"], font=(APP_FONT,9))
        self.lbl_prev.pack(side="right")
        self._labels.append(self.lbl_prev)

    # ── Mode switcher ────────────────────────
    def switch_mode(self, mode):
        self.current_mode = mode
        self.expression.set("")
        self.display.set("0")
        self.preview.set("Ready")
        self.second_mode = False
        self.sci_btns.clear()
        self.current_calc_fn = None
        self.root.unbind("<Key>")
        if mode != "Programming":
            self.root.bind("<Key>", self._on_key)

        for w in self.content.winfo_children(): w.destroy()
        self._highlight_sidebar(mode)
        titles = {
        "Basic":"Basic Calculator","Scientific":"Scientific Calculator",
        "Statistics":"Statistics Calculator","Health":"Health & BMI",
        "Finance":"Finance Calculator","Trigonometry":"Trigonometry",
        "Programming":"Programmer Calculator","Eq Solver":"Equation Solver",
        "Converter":"Unit & Currency Converter",
    }
        self.lbl_mode_name.configure(text=titles.get(mode, mode))
        dispatch = {
        "Basic":self._render_basic,"Scientific":self._render_scientific,
        "Statistics":self._render_statistics,"Health":self._render_health,
        "Finance":self._render_finance,"Trigonometry":self._render_trig,
        "Programming":self._render_programming,"Eq Solver":self._render_eq_solver,
        "Converter":self._render_converter,
    }
        dispatch.get(mode, self._render_basic)(self.content)

    # ────────────────────────────────────────
    # Button factories
    # ────────────────────────────────────────
    def _main_btn(self, parent, lbl):
        cmd = lambda l=lbl: self.handle(l)
        if lbl == "=":
            return ProButton(parent, lbl, cmd, "green_dark","green_darkhover","text",22,min_height=54,radius=27)
        if lbl in {"÷","×","−","+"}:
            return ProButton(parent, lbl, cmd, "green","green_hover","text",22,min_height=54,radius=27)
        if lbl == "AC":
            return ProButton(parent, lbl, cmd, "danger","danger_hover","text",16,min_height=54,radius=27)
        if lbl in {"%","⌫"}:
            return ProButton(parent, lbl, cmd, "grey","grey_hover","text",16,min_height=54,radius=27)
        return ProButton(parent, lbl, cmd, "surface3","num_hover","text",20,min_height=54,radius=27)

    def _sci_btn(self, parent, lbl, cmd):
        return ProButton(parent, lbl, cmd, "sci","sci_hover","text",11,min_height=42,radius=21)

    def _tab_btn(self, parent, name, cmd, active=False):
        return ProButton(parent, name, cmd,
            "green" if active else "surface2",
            "green_hover" if active else "sci_hover",
            "text", 10, min_height=30, radius=15)
    
    def _scrollable(self, parent):
        outer = tk.Frame(parent, bg=T["bg"])
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        canvas = tk.Canvas(outer, bg=T["bg"], highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")

        # ── Thin custom scrollbar ──
        sb_canvas = tk.Canvas(outer, width=6, bg=T["surface2"],
                            highlightthickness=0, cursor="arrow")
        sb_canvas.grid(row=0, column=1, sticky="ns", padx=(2, 0))
        sb_canvas.create_rectangle(0, 0, 6, 40,
                    fill=T["grey"], outline="", tags="thumb")

        inner = tk.Frame(canvas, bg=T["bg"])
        win = canvas.create_window((0, 0), window=inner, anchor="nw")

        _bound = set()

        def _update_thumb(*_):
            lo, hi = canvas.yview()
            h = sb_canvas.winfo_height()
            if h < 2:
                return
            ty1 = int(lo * h)
            ty2 = max(ty1 + 16, int(hi * h))
            sb_canvas.coords("thumb", 1, ty1, 5, ty2)
            sb_canvas.itemconfig("thumb",
                fill=T["grey"] if (hi - lo) >= 0.999 else T["muted"])

        def _on_scroll(e):
            canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
            _update_thumb()

        def _bind_scroll(widget):
            wid = str(widget)
            if wid in _bound:
                return
            _bound.add(wid)
            widget.bind("<MouseWheel>", _on_scroll)
            for child in widget.winfo_children():
                _bind_scroll(child)

        def _on_inner_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            _update_thumb()
            _bind_scroll(inner)

        def _on_canvas_resize(e):
            canvas.itemconfig(win, width=e.width)
            _update_thumb()

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_resize)
        canvas.bind("<MouseWheel>", _on_scroll)
        sb_canvas.bind("<MouseWheel>", _on_scroll)

        # Thumb drag
        _drag = [0, 0.0]
        def _thumb_press(e):
            _drag[0] = e.y
            _drag[1] = canvas.yview()[0]
        def _thumb_drag(e):
            h = sb_canvas.winfo_height()
            if h < 2:
                return
            canvas.yview_moveto(_drag[1] + (e.y - _drag[0]) / h)
            _update_thumb()
        sb_canvas.tag_bind("thumb", "<ButtonPress-1>", _thumb_press)
        sb_canvas.tag_bind("thumb", "<B1-Motion>", _thumb_drag)
        sb_canvas.bind("<ButtonPress-1>", lambda e: (
            canvas.yview_moveto(e.y / max(sb_canvas.winfo_height(), 1)),
            _update_thumb()
        ))

        return inner
    # ────────────────────────────────────────
    # BASIC
    # ────────────────────────────────────────
    def _render_basic(self, parent):
        pad = tk.Frame(parent, bg=T["bg"])
        pad.pack(fill="both", expand=True)
        rows = [["AC","%","⌫","÷"],["7","8","9","×"],
                ["4","5","6","−"],["1","2","3","+"],[" ±","0",".","="]]
        for c in range(4): pad.columnconfigure(c, weight=1, uniform="b")
        for r in range(5): pad.rowconfigure(r, weight=1, uniform="b")
        for ri,row in enumerate(rows):
            for ci,lbl in enumerate(row):
                self._main_btn(pad, lbl.strip()).grid(row=ri,column=ci,padx=5,pady=5,sticky="nsew")

    # ────────────────────────────────────────
    # SCIENTIFIC
    # ────────────────────────────────────────
    def _render_scientific(self, parent):
        outer = tk.Frame(parent, bg=T["bg"])
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=2)
        outer.rowconfigure(1, weight=3)

        sf = tk.Frame(outer, bg=T["bg"])
        sf.grid(row=0, column=0, sticky="nsew", pady=(0,4))
        for c in range(6): sf.columnconfigure(c, weight=1, uniform="s")
        for r in range(6): sf.rowconfigure(r, weight=1, uniform="s")

        sci_rows = [
            [("(",    lambda: self.ins("(")),          (")",    lambda: self.ins(")")),
             ("mc",   lambda: self.mem("mc")),         ("m+",   lambda: self.mem("m+")),
             ("m−",   lambda: self.mem("m−")),         ("mr",   lambda: self.mem("mr"))],
            [("x²",   lambda: self.wrap("({x})^2")),  ("x³",   lambda: self.wrap("({x})^3")),
             ("xʸ",   lambda: self.ins("^")),          ("eˣ",   lambda: self.ins("exp(")),
             ("10ˣ",  lambda: self.ins("10^(")),       ("1/x",  lambda: self.wrap("1/({x})"))],
            [("2nd",  self._toggle_2nd),               ("²√x",  lambda: self.ins("sqrt(")),
             ("³√x",  lambda: self.ins("cbrt(")),      ("ʸ√x",  lambda: self.ins("root(")),
             ("log",  lambda: self.ins("log(")),       ("round",lambda: self.ins("round("))],
            [("sin",  lambda: self._trig("sin")),      ("cos",  lambda: self._trig("cos")),
             ("tan",  lambda: self._trig("tan")),      ("x!",   lambda: self.ins("!")),
             ("π",    lambda: self.ins("π")),          (",",    lambda: self.ins(","))],
            [("sinh", lambda: self._hyp("sinh")),      ("cosh", lambda: self._hyp("cosh")),
             ("tanh", lambda: self._hyp("tanh")),      ("abs",  lambda: self.ins("abs(")),
             ("Rand", lambda: self.ins("rand")),       ("𝑒",    lambda: self.ins("𝑒"))],
            [("ln",   lambda: self.ins("ln(")),        ("ceil", lambda: self.ins("ceil(")),
             ("floor",lambda: self.ins("floor(")),     ("EE",   lambda: self.ins("e")),
             ("lcm",  lambda: self.ins("lcm(")),     ("gcd",  lambda: self.ins("gcd("))],
        ]
        for ri, row in enumerate(sci_rows):
            for ci, (lbl, cmd) in enumerate(row):
                b = ProButton(sf, lbl, command=cmd,
                              bg_color="sci", hover_color="sci_hover", fg_color="text",
                              font_size=10, min_height=46, radius=19)
                b.grid(row=ri, column=ci, padx=2, pady=2, sticky="nsew")
                self.sci_btns[lbl] = b
        
        bf = tk.Frame(outer, bg=T["bg"])
        bf.grid(row=1, column=0, sticky="nsew")
        for c in range(6): bf.columnconfigure(c, weight=1, uniform="b")
        for r in range(5): bf.rowconfigure(r, weight=1, uniform="b")

        basic_rows = [["AC","%","⌫","÷"],["7","8","9","×"],
                      ["4","5","6","−"],["1","2","3","+"],[" ±","0",".","="]]
        for ri, row in enumerate(basic_rows):
            for ci, lbl in enumerate(row):
                self._main_btn(bf, lbl.strip()).grid(
                    row=ri, column=ci*1, columnspan=1,
                    padx=3, pady=3, sticky="nsew")

        for c in range(4): bf.columnconfigure(c, weight=400, uniform="b")
        for c in range(4, 6): bf.columnconfigure(c, weight=2, uniform="b")

    def _toggle_2nd(self):
        self.second_mode = not self.second_mode
        on = self.second_mode
        if "2nd" in self.sci_btns:
            self.sci_btns["2nd"].set_colors(
                "green" if on else "sci",
                "green_hover" if on else "sci_hover",
                "text")
        for k,v in {"sin":"sin⁻¹","cos":"cos⁻¹","tan":"tan⁻¹",
                    "sinh":"sinh⁻¹","cosh":"cosh⁻¹","tanh":"tanh⁻¹"}.items():
            if k in self.sci_btns: self.sci_btns[k].set_text(v if on else k)

    def _trig(self, base): self.ins(f"a{base}(" if self.second_mode else f"{base}(")
    def _hyp(self, base):  self.ins(f"a{base}(" if self.second_mode else f"{base}(")

    # ────────────────────────────────────────
    # STATISTICS  (isolated StringVars)
    # ────────────────────────────────────────
    def _render_statistics(self, parent):
        frame = tk.Frame(parent, bg=T["bg"])
        frame.pack(fill="both", expand=True)

        tlabel(frame,"Enter comma-separated numbers:",size=10,muted=True).pack(anchor="w",pady=(0,4))
        inp = tk.StringVar()
        tentry(frame, inp, 13).pack(fill="x", ipady=7, pady=(0,8))


        def calc():
            raw = inp.get().strip()
            if not raw: return
            try:
                nums=[float(x.strip()) for x in raw.split(",") if x.strip()]
                if not nums: return
                n=len(nums)
                total=sum(nums)
                mean=total/n
                sorted_nums=sorted(nums)
                med=statistics.median(nums)

                from collections import Counter
                freq=Counter(nums)
                max_freq=max(freq.values())
                if max_freq==1:
                    mode_s="No repeating values"
                else:
                    modes=[x for x,c in freq.items() if c==max_freq]
                    mode_s=", ".join(str(int(x) if x==int(x) else x) for x in sorted(modes))
                    mode_s+=f" (×{max_freq})"

                pop_var=sum((x-mean)**2 for x in nums)/n
                pop_std=math.sqrt(pop_var)
                samp_var=sum((x-mean)**2 for x in nums)/(n-1) if n>1 else None
                samp_std=math.sqrt(samp_var) if n>1 else None

                try:
                    geo_s=f"{math.exp(sum(math.log(x) for x in nums)/n):.10g}" if all(x>0 for x in nums) else "N/A"
                except: geo_s="N/A"
                sorted_s=", ".join(str(int(x) if x==int(x) else x) for x in sorted_nums)

                self.show_result(
                    f"Count: {n}\n"
                    f"Sum: {total:.10g}\n"
                    f"Mean: {mean:.10g}\n"
                    f"Median: {med:.10g}\n"
                    f"Mode: {mode_s}\n"
                    f"Largest: {max(nums):.10g}\n"
                    f"Smallest: {min(nums):.10g}\n"
                    f"Range: {max(nums)-min(nums):.10g}\n"
                    f"Std Dev: {pop_std:.10g}\n"
                    f"Variance: {pop_var:.10g}\n"
                    f"Samp StdD: {'N/A' if samp_std is None else f'{samp_std:.10g}'}\n"
                    f"Samp Var: {'N/A' if samp_var is None else f'{samp_var:.10g}'}\n"
                    f"Geo Mean: {geo_s}\n",
                    label=f"Stats ({n} values)"
                )
            except Exception as ex:
                self.show_result(f"Error: {ex}", label="Statistics")
            
        btn_row = tk.Frame(frame, bg=T["bg"])
        btn_row.pack(fill="x", pady=4)
        btn_row.columnconfigure(0, weight=3)
        btn_row.columnconfigure(1, weight=1)

        calc_btn(btn_row, "Calculate Statistics", calc, app=self).grid(row=0, column=0, sticky="ew", padx=(0,4))
        ProButton(btn_row, "Clear", command=lambda: [inp.set(""), self.display.set("0"), self.expression.set(""), self.preview.set("Ready")],
            bg_color="danger", hover_color="danger_hover", fg_color="text",
            font_size=12, min_height=40, radius=20).grid(row=0, column=1, sticky="ew")

    # ────────────────────────────────────────
    # HEALTH  (isolated StringVars per sub-tab)
    # ────────────────────────────────────────
    def _render_health(self, parent):
        frame=tk.Frame(parent,bg=T["bg"])
        frame.pack(fill="both",expand=True)
        tabs={"BMI":self._health_bmi,"BMR":self._health_bmr,
              "Body Fat":self._health_bodyfat,"Calories":self._health_calories}
        tab_bar=tk.Frame(frame,bg=T["bg"])
        tab_bar.pack(fill="x",pady=(0,8))
        tab_btns={}
        cf=tk.Frame(frame,bg=T["bg"])
        cf.pack(fill="both",expand=True)
        cf.pack_propagate(False)

        def switch(name):
            # Point 3: clear top display when switching tabs
            self.display.set("0"); self.expression.set(""); self.preview.set("Ready")
            for n,b in tab_btns.items():
                b.set_colors("green" if n==name else "surface2",
                             "green_hover" if n==name else "sci_hover","text")
            for w in cf.winfo_children(): w.destroy()
            tabs[name](cf)

        row1=tk.Frame(tab_bar,bg=T["bg"]); row1.pack(fill="x",pady=(0,3))
        row2=tk.Frame(tab_bar,bg=T["bg"]); row2.pack(fill="x")
        names=list(tabs.keys())
        for c in range(2): row1.columnconfigure(c,weight=1,uniform="ht")
        for c in range(2): row2.columnconfigure(c,weight=1,uniform="ht")
        for i,name in enumerate(names):
            row,col=(row1,i) if i<2 else (row2,i-2)
            b=self._tab_btn(row,name,lambda n=name:switch(n))
            b.grid(row=0,column=col,sticky="ew",padx=3,pady=0)
            tab_btns[name]=b

        # Point 3: open BMI by default
        switch("BMI")

    def _h_field(self, parent, label, hint=""):
        # Point 4: tighter spacing
        tlabel(parent,label,size=10,muted=True).pack(anchor="w",pady=(4,1),fill="x")
        var=tk.StringVar()
        tentry(parent,var,13).pack(fill="x",ipady=5)
        if hint: tlabel(parent,hint,size=8,muted=True).pack(anchor="w",fill="x")
        return var

    def _h_result(self, parent):
        var=tk.StringVar(value="")
        tresult(parent,var,13).pack(fill="x",pady=6)
        return var

    def _h_clear_btn(self, parent, fields, res_var):
        """Shared clear button for all health tabs."""
        def do_clear():
            for fv in fields: fv.set("")
            res_var.set("")
            self.display.set("0"); self.expression.set(""); self.preview.set("Ready")
        ProButton(parent,"Clear",command=do_clear,
            bg_color="danger",hover_color="danger_hover",fg_color="text",
            font_size=12,min_height=40,radius=20).pack(fill="x",pady=(2,4))

    def _health_bmi(self, parent):
        parent=self._full_frame(parent)
        w_var=self._h_field(parent,"Weight (kg)")
        h_var=self._h_field(parent,"Height (cm)")
        res=tk.StringVar(value="")
        res_box=tresult(parent,res,13)
        def on_change(*_):
            if res.get(): res_box.pack(fill="x",pady=(4,0))
            else: res_box.pack_forget()
        res.trace_add("write",on_change)
        def calc():
            try:
                if not w_var.get().strip() or not h_var.get().strip():
                    msg="⚠ Please enter both weight and height."
                    res.set(msg); self.show_result(msg,label="BMI"); return
                w=float(w_var.get()); h=float(h_var.get())
                if w<=0 or h<=0: raise ValueError("Values must be positive")
                bmi=w/((h/100)**2)
                # Bug fix: use strict < for boundaries, no rounding artefacts
                # 25.00 should be Overweight (bmi < 25 is Normal, so 25.00 is Overweight)
                # 29.98 should be Overweight (bmi < 30, so correct)
                if bmi<18.5:   cat="Underweight"
                elif bmi<25.0: cat="Normal weight"
                elif bmi<30.0: cat="Overweight"
                else:          cat="Obese"
                msg = f"BMI: {bmi:.4f}  →  {cat}"
                res.set(msg); self.show_result(msg,label=f"{w} kg  /  {h} cm")
            except ValueError as ex:
                msg=f"Error: {ex}"
                res.set(msg); self.show_result(msg,label="BMI")
            except Exception:
                msg="Invalid input"
                res.set(msg); self.show_result(msg,label="BMI")
        calc_btn(parent,"Calculate BMI",calc,app=self).pack(fill="x",pady=(6,2))
        self._h_clear_btn(parent,[w_var,h_var],res)

    def _health_bmr(self, parent):
        parent=self._full_frame(parent)
        w=self._h_field(parent,"Weight (kg)")
        h=self._h_field(parent,"Height (cm)")
        a=self._h_field(parent,"Age (years)")
        g=tk.StringVar(value="Male")
        tlabel(parent,"Gender",size=10,muted=True).pack(anchor="w",pady=(4,1))
        ttk.Combobox(parent,textvariable=g,values=["Male","Female"],
                     state="readonly",font=(APP_FONT,12),style="C.TCombobox").pack(fill="x",ipady=4)
        res=tk.StringVar(value="")
        res_box=tresult(parent,res,13)
        def on_change(*_):
            if res.get(): res_box.pack(fill="x",pady=(4,0))
            else: res_box.pack_forget()
        res.trace_add("write",on_change)
        def calc():
            try:
                if not all(v.get().strip() for v in [w,h,a]):
                    msg="⚠ Please fill in all fields."
                    res.set(msg); self.show_result(msg,label="BMR"); return
                wv,hv,av=float(w.get()),float(h.get()),float(a.get())
                if wv<=0 or hv<=0 or av<=0: raise ValueError("All values must be positive")
                bmr=10*wv+6.25*hv-5*av+(5 if g.get()=="Male" else -161)
                msg=(f"BMR: {bmr:.1f} kcal/day\n"
                     f"Sedentary: {bmr*1.2:.0f}\n  Light: {bmr*1.375:.0f}\n"
                     f"Moderate: {bmr*1.55:.0f}\n  Very active: {bmr*1.725:.0f}\n"
                     f"Extra active: {bmr*1.9:.0f}")
                res.set(msg); self.show_result(msg,label=f"BMR  {wv}kg {hv}cm {av}yrs")
            except ValueError as ex:
                msg=f"Error: {ex}"
                res.set(msg); self.show_result(msg,label="BMR")
            except Exception:
                msg="Invalid input"
                res.set(msg); self.show_result(msg,label="BMR")
        calc_btn(parent,"Calculate BMR",calc,app=self).pack(fill="x",pady=(6,2))
        self._h_clear_btn(parent,[w,h,a],res)

    def _health_bodyfat(self, parent):
        parent=self._full_frame(parent)
        tlabel(parent,"US Navy Method",size=10,bold=True,fg_key="green").pack(anchor="w",pady=(0,4))
        h =self._h_field(parent,"Height (cm)")
        nc=self._h_field(parent,"Neck circumference (cm)")
        wa=self._h_field(parent,"Waist circumference (cm)")
        hp=self._h_field(parent,"Hip circumference (cm) — females only")
        g=tk.StringVar(value="Male")
        tlabel(parent,"Gender",size=10,muted=True).pack(anchor="w",pady=(4,1))
        ttk.Combobox(parent,textvariable=g,values=["Male","Female"],
                     state="readonly",font=(APP_FONT,12),style="C.TCombobox").pack(fill="x",ipady=4)
        res=tk.StringVar(value="")
        res_box=tresult(parent,res,13)
        def on_change(*_):
            if res.get(): res_box.pack(fill="x",pady=(4,0))
            else: res_box.pack_forget()
        res.trace_add("write",on_change)
        def calc():
            try:
                if not all(v.get().strip() for v in [h,nc,wa]):
                    msg="⚠ Please fill in all required fields."
                    res.set(msg); self.show_result(msg,label="Body Fat"); return
                hv,nv,wv=float(h.get()),float(nc.get()),float(wa.get())
                if hv<=0: raise ValueError("Height must be greater than 0")
                if nv<=0: raise ValueError("Neck circumference must be greater than 0")
                if wv<=0: raise ValueError("Waist circumference must be greater than 0")
                if g.get()=="Male":
                    if wv<=nv: raise ValueError("Waist must be greater than neck")
                    bf=495/(1.0324-0.19077*math.log10(wv-nv)+0.15456*math.log10(hv))-450
                else:
                    if not hp.get().strip(): raise ValueError("Hip circumference required for females")
                    hpv=float(hp.get())
                    if hpv<=0: raise ValueError("Hip circumference must be greater than 0")
                    if (wv+hpv)<=nv: raise ValueError("Waist+Hip must exceed neck")
                    bf=495/(1.29579-0.35004*math.log10(wv+hpv-nv)+0.22100*math.log10(hv))-450
                # Bug fix: body fat cannot be negative or above 70% — both are physically impossible
                if bf<0 or bf>70:
                    raise ValueError(f"Result ({bf:.1f}%) is outside a valid range — please check your measurements")
                msg=f"Body Fat: {bf:.1f}%"
                res.set(msg); self.show_result(msg,label="Body Fat %")
            except ValueError as ex:
                msg=f"Error: {ex}"
                res.set(msg); self.show_result(msg,label="Body Fat")
            except Exception:
                msg="Invalid input"
                res.set(msg); self.show_result(msg,label="Body Fat")
        calc_btn(parent,"Calculate Body Fat",calc,app=self).pack(fill="x",pady=(6,2))
        self._h_clear_btn(parent,[h,nc,wa,hp],res)

    def _health_calories(self, parent):
        parent=self._full_frame(parent)
        f =self._h_field(parent,"Fat (g)",   "1 g fat = 9 kcal")
        p =self._h_field(parent,"Protein (g)","1 g protein = 4 kcal")
        c =self._h_field(parent,"Carbs (g)",  "1 g carbs = 4 kcal")
        al=self._h_field(parent,"Alcohol (g)","1 g alcohol = 7 kcal")
        res=tk.StringVar(value="")
        res_box=tresult(parent,res,13)
        def on_change(*_):
            if res.get(): res_box.pack(fill="x",pady=(4,0))
            else: res_box.pack_forget()
        res.trace_add("write",on_change)
        def calc():
            try:
                fv=float(f.get() or 0); pv=float(p.get() or 0)
                cv=float(c.get() or 0); av=float(al.get() or 0)
                if any(x<0 for x in [fv,pv,cv,av]):
                    msg="Error: Macro grams cannot be negative"
                    res.set(msg); self.show_result(msg,label="Calories"); return
                total=fv*9+pv*4+cv*4+av*7
                msg=(f"Fat: {fv*9:.1f}   Protein: {pv*4:.1f}\n"
                     f"Carbs: {cv*4:.1f}   Alcohol: {av*7:.1f}\n"
                     f"Total: {total:.1f} kcal")
                res.set(msg); self.show_result(msg,label="Calorie Breakdown")
            except Exception:
                msg="Invalid input"
                res.set(msg); self.show_result(msg,label="Calories")
        calc_btn(parent,"Calculate Calories",calc,app=self).pack(fill="x",pady=(6,2))
        self._h_clear_btn(parent,[f,p,c,al],res)

    # ────────────────────────────────────────
    # FINANCE  (isolated StringVars per sub-tab)
    # ────────────────────────────────────────
    def _render_finance(self, parent):
        tabs={"Simple Interest":self._fin_si,"Compound Interest":self._fin_ci,
             "EMI":self._fin_emi,"ROI":self._fin_roi,"Discount":self._fin_disc,
             "TVM":self._fin_tvm}
        tab_bar=tk.Frame(parent,bg=T["bg"]); tab_bar.pack(fill="x",pady=(0,8))
        tab_btns={}
        cf=tk.Frame(parent,bg=T["bg"]); cf.pack(fill="both",expand=True)
        cf.pack_propagate(False)

        def switch(name):
            # Clear top display when switching tabs
            self.display.set("0")
            self.expression.set("")
            self.preview.set("Ready")
            for n,b in tab_btns.items():
                b.set_colors("green" if n==name else "surface2",
                             "green_hover" if n==name else "sci_hover","text")
            for w in cf.winfo_children(): w.destroy()
            tabs[name](cf)

        row1=tk.Frame(tab_bar,bg=T["bg"]); row1.pack(fill="x",pady=(0,3))
        row2=tk.Frame(tab_bar,bg=T["bg"]); row2.pack(fill="x")
        names=list(tabs.keys())
        for c in range(3): row1.columnconfigure(c,weight=1,uniform="ft")
        for c in range(3): row2.columnconfigure(c,weight=1,uniform="ft")
        for i,name in enumerate(names):
            row,col=(row1,i) if i<3 else (row2,i-3)
            b=self._tab_btn(row,name,lambda n=name:switch(n))
            b.grid(row=0,column=col,sticky="ew",padx=2,pady=0)
            tab_btns[name]=b

        # Point 3: open Simple Interest by default
        switch("Simple Interest")

    def _f_field(self, parent, label):
        tlabel(parent,label,size=10,muted=True).pack(anchor="w",pady=(4,1),fill="x")
        var=tk.StringVar()
        tentry(parent,var,13).pack(fill="x",ipady=5)
        return var

    def _f_result(self, parent):
        var=tk.StringVar(value="")
        tresult(parent,var,13).pack(fill="x",pady=6)
        return var

    def _full_frame(self, parent):
        f=tk.Frame(parent,bg=T["bg"])
        # Point 4: don't expand to fill screen, just wrap content
        f.pack(fill="x",padx=10,pady=4)
        return f

    def _fin_clear_btn(self, parent, fields, res_var):
        """Shared clear button for all finance tabs."""
        def do_clear():
            for fv in fields: fv.set("")
            res_var.set("")
            self.display.set("0")
            self.expression.set("")
            self.preview.set("Ready")
        ProButton(parent,"Clear",command=do_clear,
            bg_color="danger",hover_color="danger_hover",fg_color="text",
            font_size=12,min_height=40,radius=20).pack(fill="x",pady=(2,4))

    def _fin_si(self, parent):
        parent=self._full_frame(parent)
        p=self._f_field(parent,"Principal amount")
        r=self._f_field(parent,"Annual interest rate (%)")
        t=self._f_field(parent,"Time")
        tenure_unit=tk.StringVar(value="Years")
        uf=tk.Frame(parent,bg=T["bg"]); uf.pack(fill="x",pady=(2,4))
        tlabel(uf,"Time unit:",size=9,muted=True).pack(side="left",padx=(0,8))
        for unit in ["Months","Years"]:
            tk.Radiobutton(uf,text=unit,variable=tenure_unit,value=unit,
                bg=T["bg"],fg=T["text"],selectcolor=T["surface2"],
                activebackground=T["bg"],activeforeground=T["green"],
                font=(APP_FONT,9)).pack(side="left",padx=4)
        res=tk.StringVar(value="")
        res_box=tresult(parent,res,13)
        def on_change(*_):
            if res.get(): res_box.pack(fill="x",pady=(4,0))
            else: res_box.pack_forget()
        res.trace_add("write",on_change)
        def calc():
            try:
                # Bug fix: validate empty fields
                if not p.get().strip() or not r.get().strip() or not t.get().strip():
                    msg="⚠ Please fill in all fields."
                    res.set(msg); self.show_result(msg,label="Simple Interest"); return
                pv,rv,tv_raw=float(p.get()),float(r.get()),float(t.get())
                # Bug fix: P=0 or negative not allowed
                if pv<=0: raise ValueError("Principal must be greater than 0")
                if rv<0: raise ValueError("Rate must be non-negative")
                if tv_raw<=0: raise ValueError("Time must be greater than 0")
                tv=tv_raw/12 if tenure_unit.get()=="Months" else tv_raw
                si=pv*rv*tv/100
                msg=f"Interest: {si:.2f}\nTotal: {pv+si:.2f}"
                res.set(msg)
                self.show_result(msg,label=f"SI  P={pv}  R={rv}%  T={tv_raw} {tenure_unit.get()}")
            except ValueError as ex:
                msg=f"Error: {ex}"
                res.set(msg); self.show_result(msg,label="Simple Interest")
            except Exception:
                msg="Invalid input"
                res.set(msg); self.show_result(msg,label="Simple Interest")
        calc_btn(parent,"Calculate",calc,app=self).pack(fill="x",pady=(6,2))
        self._fin_clear_btn(parent,[p,r,t],res)

    def _fin_ci(self, parent):
        parent=self._full_frame(parent)
        p=self._f_field(parent,"Principal")
        r=self._f_field(parent,"Annual interest rate (%)")
        t=self._f_field(parent,"Time (years)")
        n=self._f_field(parent,"Compounding periods per year")
        res=tk.StringVar(value="")
        res_box=tresult(parent,res,13)
        def on_change(*_):
            if res.get(): res_box.pack(fill="x",pady=(4,0))
            else: res_box.pack_forget()
        res.trace_add("write",on_change)
        def calc():
            try:
                if not all(v.get().strip() for v in [p,r,t,n]):
                    msg="⚠ Please fill in all fields."
                    res.set(msg); self.show_result(msg,label="Compound Interest"); return
                pv,rv,tv,nv=float(p.get()),float(r.get()),float(t.get()),float(n.get())
                # Bug fix: no negative principal
                if pv<=0: raise ValueError("Principal must be greater than 0")
                if rv<0: raise ValueError("Rate must be non-negative")
                if tv<=0: raise ValueError("Time must be greater than 0")
                if nv<=0: raise ValueError("Compounding periods must be greater than 0")
                amt=pv*(1+rv/(100*nv))**(nv*tv)
                msg=f"Interest: {amt-pv:.2f}\nTotal: {amt:.2f}"
                res.set(msg)
                self.show_result(msg,label=f"CI  P={pv}  R={rv}%  T={tv}yr")
            except ValueError as ex:
                msg=f"Error: {ex}"
                res.set(msg); self.show_result(msg,label="Compound Interest")
            except Exception:
                msg="Invalid input"
                res.set(msg); self.show_result(msg,label="Compound Interest")
        calc_btn(parent,"Calculate",calc,app=self).pack(fill="x",pady=(6,2))
        self._fin_clear_btn(parent,[p,r,t,n],res)

    def _fin_emi(self, parent):
        parent=self._full_frame(parent)
        p=self._f_field(parent,"Loan principal")
        r=self._f_field(parent,"Annual interest rate (%)")
        t=self._f_field(parent,"Loan tenure")
        tenure_unit=tk.StringVar(value="Months")
        uf=tk.Frame(parent,bg=T["bg"]); uf.pack(fill="x",pady=(2,4))
        tlabel(uf,"Tenure unit:",size=9,muted=True).pack(side="left",padx=(0,8))
        for unit in ["Months","Years"]:
            tk.Radiobutton(uf,text=unit,variable=tenure_unit,value=unit,
                bg=T["bg"],fg=T["text"],selectcolor=T["surface2"],
                activebackground=T["bg"],activeforeground=T["green"],
                font=(APP_FONT,9)).pack(side="left",padx=4)
        res=tk.StringVar(value="")
        res_box=tresult(parent,res,13)
        def on_change(*_):
            if res.get(): res_box.pack(fill="x",pady=(4,0))
            else: res_box.pack_forget()
        res.trace_add("write",on_change)
        def calc():
            try:
                if not all(v.get().strip() for v in [p,r,t]):
                    msg="⚠ Please fill in all fields."
                    res.set(msg); self.show_result(msg,label="EMI"); return
                pv=float(p.get()); rv=float(r.get())/12/100
                tv_raw=float(t.get())
                if pv<=0: raise ValueError("Principal must be greater than 0")
                if tv_raw<=0: raise ValueError("Tenure must be greater than 0")
                if tenure_unit.get()=="Years":
                    tv=tv_raw*12
                else:
                    if tv_raw!=int(tv_raw): raise ValueError("Tenure in months must be a whole number")
                    tv=int(tv_raw)
                emi=pv/tv if rv==0 else pv*rv*(1+rv)**tv/((1+rv)**tv-1)
                msg=f"EMI: {emi:.2f}/month\nTotal: {emi*tv:.2f}   Interest: {emi*tv-pv:.2f}"
                res.set(msg)
                self.show_result(msg,label=f"EMI  P={pv}  R={float(r.get())}%  {tv_raw} {tenure_unit.get()}")
            except ValueError as ex:
                msg=f"Error: {ex}"
                res.set(msg); self.show_result(msg,label="EMI")
            except Exception:
                msg="Invalid input"
                res.set(msg); self.show_result(msg,label="EMI")
        calc_btn(parent,"Calculate EMI",calc,app=self).pack(fill="x",pady=(6,2))
        self._fin_clear_btn(parent,[p,r,t],res)

    def _fin_roi(self, parent):
        parent=self._full_frame(parent)
        inv=self._f_field(parent,"Initial investment")
        ret=self._f_field(parent,"Final value / returns")
        res=tk.StringVar(value="")
        res_box=tresult(parent,res,13)
        def on_change(*_):
            if res.get(): res_box.pack(fill="x",pady=(4,0))
            else: res_box.pack_forget()
        res.trace_add("write",on_change)
        def calc():
            try:
                if not all(v.get().strip() for v in [inv,ret]):
                    msg="⚠ Please fill in all fields."
                    res.set(msg); self.show_result(msg,label="ROI"); return
                iv,rv=float(inv.get()),float(ret.get())
                if iv<=0: raise ValueError("Initial investment must be greater than zero")
                roi=(rv-iv)/iv*100
                msg=f"ROI: {roi:.2f}%\n{'Gain' if rv>=iv else 'Loss'}: {abs(rv-iv):.2f}"
                res.set(msg)
                self.show_result(msg,label=f"ROI  invested={iv}")
            except ValueError as ex:
                msg=f"Error: {ex}"
                res.set(msg); self.show_result(msg,label="ROI")
            except Exception:
                msg="Invalid input"
                res.set(msg); self.show_result(msg,label="ROI")
        calc_btn(parent,"Calculate ROI",calc,app=self).pack(fill="x",pady=(6,2))
        self._fin_clear_btn(parent,[inv,ret],res)

    def _fin_disc(self, parent):
        parent=self._full_frame(parent)
        p=self._f_field(parent,"Original price")
        d=self._f_field(parent,"Discount (%)")
        res=tk.StringVar(value="")
        res_box=tresult(parent,res,13)
        def on_change(*_):
            if res.get(): res_box.pack(fill="x",pady=(4,0))
            else: res_box.pack_forget()
        res.trace_add("write",on_change)
        def calc():
            try:
                if not all(v.get().strip() for v in [p,d]):
                    msg="⚠ Please fill in all fields."
                    res.set(msg); self.show_result(msg,label="Discount"); return
                pv,dv=float(p.get()),float(d.get())
                if pv<=0: raise ValueError("Price must be greater than 0")
                if not (0<=dv<=100): raise ValueError("Discount must be 0–100%")
                disc=pv*dv/100
                msg=f"Discount: {disc:.2f}\nFinal Price: {pv-disc:.2f}"
                res.set(msg)
                self.show_result(msg,label=f"Discount {dv}% off {pv}")
            except ValueError as ex:
                msg=f"Error: {ex}"
                res.set(msg); self.show_result(msg,label="Discount")
            except Exception:
                msg="Invalid input"
                res.set(msg); self.show_result(msg,label="Discount")
        calc_btn(parent,"Calculate",calc,app=self).pack(fill="x",pady=(6,2))
        self._fin_clear_btn(parent,[p,d],res)

    def _fin_tvm(self, parent):
        parent=self._full_frame(parent)
        tlabel(parent,"Time Value of Money — solve for any variable",size=10,bold=True,fg_key="green").pack(anchor="w",pady=(0,6))
        tvm_tabs=["FV","PV","PMT","N","I/Y"]
        tvm_bar=tk.Frame(parent,bg=T["bg"]); tvm_bar.pack(fill="x",pady=(0,6))
        for c in range(5): tvm_bar.columnconfigure(c,weight=1,uniform="tvm")
        tvm_btns={}
        tvm_cf=tk.Frame(parent,bg=T["bg"]); tvm_cf.pack(fill="x")

        def tvm_switch(name):
            # Clear top display when switching TVM tabs
            self.display.set("0"); self.expression.set(""); self.preview.set("Ready")
            for n,b in tvm_btns.items():
                b.set_colors("green" if n==name else "surface2",
                            "green_hover" if n==name else "sci_hover","text")
            for w in tvm_cf.winfo_children(): w.destroy()
            tvm_panels[name](tvm_cf)

        def row2(p,l1,l2):
            f=tk.Frame(p,bg=T["bg"]); f.pack(fill="x",pady=(0,2))
            f.columnconfigure(0,weight=1,uniform="r"); f.columnconfigure(1,weight=1,uniform="r")
            v1=tk.StringVar(); v2=tk.StringVar()
            def col(lbl,var,c):
                tlabel(f,lbl,size=9,muted=True).grid(row=0,column=c,sticky="w",padx=(0,4) if c==0 else (4,0))
                tentry(f,var,11).grid(row=1,column=c,sticky="ew",ipady=4,padx=(0,4) if c==0 else (4,0))
            col(l1,v1,0); col(l2,v2,1)
            return v1,v2

        def solve_field(p,lbl):
            tlabel(p,f"{lbl}  ← result",size=9,fg_key="green").pack(anchor="w",pady=(4,1))
            var=tk.StringVar()
            e=tk.Entry(p,textvariable=var,state="readonly",
                      bg=T["surface3"],fg=T["green"],readonlybackground=T["surface3"],
                      relief="flat",font=(APP_FONT,13,"bold"),
                      highlightthickness=1,highlightcolor=T["green"],
                      highlightbackground=T["green"])
            e.pack(fill="x",ipady=6)
            return var

        def fmt(v):
            if not (v is not None and abs(v)<1e15): return "Error"
            return f"{v:.4f}"

        def tvm_clear(fields,res_var):
            def do():
                for f in fields: f.set("")
                res_var.set("")
                self.display.set("0"); self.expression.set(""); self.preview.set("Ready")
            return do

        # ── FV ──
        def panel_fv(p):
            pv,iy=row2(p,"Present Value (PV)","Interest Rate I/Y (%/yr)")
            n,pmt=row2(p,"Periods (N)","Payment (PMT) — 0 if none")
            res=solve_field(p,"Future Value (FV)")
            def calc():
                try:
                    if not all(v.get().strip() for v in [pv,iy,n]):
                        msg="⚠ Fill in PV, I/Y and N."
                        res.set(msg); self.show_result(msg,label="TVM"); return
                    pv_=float(pv.get()); r=float(iy.get())/100
                    n_=float(n.get()); pmt_=float(pmt.get() or 0)
                    if r==0: fv=-(pv_+pmt_*n_)
                    else: fv=-(pv_*(1+r)**n_+pmt_*((1+r)**n_-1)/r)
                    res.set(fmt(fv)); self.show_result(f"FV = {fmt(fv)}",label="TVM")
                except ValueError:
                    msg="Error: Invalid input — letters not allowed."
                    res.set(msg); self.show_result(msg,label="TVM")
                except Exception:
                    msg="Error: Could not calculate."
                    res.set(msg); self.show_result(msg,label="TVM")
            calc_btn(p,"Calculate FV",calc,app=self).pack(fill="x",pady=(6,2))
            ProButton(p,"Clear",command=tvm_clear([pv,iy,n,pmt],res),
                bg_color="danger",hover_color="danger_hover",fg_color="text",
                font_size=12,min_height=40,radius=20).pack(fill="x",pady=(2,4))

        # ── PV ──
        def panel_pv(p):
            fv,iy=row2(p,"Future Value (FV)","Interest Rate I/Y (%/yr)")
            n,pmt=row2(p,"Periods (N)","Payment (PMT) — 0 if none")
            res=solve_field(p,"Present Value (PV)")
            def calc():
                try:
                    if not all(v.get().strip() for v in [fv,iy,n]):
                        msg="⚠ Fill in FV, I/Y and N."
                        res.set(msg); self.show_result(msg,label="TVM"); return
                    fv_=float(fv.get()); r=float(iy.get())/100
                    n_=float(n.get()); pmt_=float(pmt.get() or 0)
                    if r==0: pv=-(fv_+pmt_*n_)
                    else: pv=-(fv_/(1+r)**n_+pmt_*(1-(1+r)**-n_)/r)
                    res.set(fmt(pv)); self.show_result(f"PV = {fmt(pv)}",label="TVM")
                except ValueError:
                    msg="Error: Invalid input — letters not allowed."
                    res.set(msg); self.show_result(msg,label="TVM")
                except Exception:
                    msg="Error: Could not calculate."
                    res.set(msg); self.show_result(msg,label="TVM")
            calc_btn(p,"Calculate PV",calc,app=self).pack(fill="x",pady=(6,2))
            ProButton(p,"Clear",command=tvm_clear([fv,iy,n,pmt],res),
                bg_color="danger",hover_color="danger_hover",fg_color="text",
                font_size=12,min_height=40,radius=20).pack(fill="x",pady=(2,4))

        # ── PMT ──
        def panel_pmt(p):
            pv,fv=row2(p,"Present Value (PV)","Future Value (FV) — 0 if none")
            iy,n=row2(p,"Interest Rate I/Y (%/yr)","Periods (N)")
            res=solve_field(p,"Payment (PMT)")
            def calc():
                try:
                    if not all(v.get().strip() for v in [pv,iy,n]):
                        msg="⚠ Fill in PV, I/Y and N."
                        res.set(msg); self.show_result(msg,label="TVM"); return
                    pv_=float(pv.get()); fv_=float(fv.get() or 0)
                    r=float(iy.get())/100/12; n_=float(n.get())
                    if r==0: pmt=-(pv_+fv_)/n_
                    else: pmt=-((pv_*(1+r)**n_+fv_)*r)/((1+r)**n_-1)
                    res.set(fmt(pmt)); self.show_result(f"PMT = {fmt(pmt)}",label="TVM")
                except ValueError:
                    msg="Error: Invalid input — letters not allowed."
                    res.set(msg); self.show_result(msg,label="TVM")
                except Exception:
                    msg="Error: Could not calculate."
                    res.set(msg); self.show_result(msg,label="TVM")
            calc_btn(p,"Calculate PMT",calc,app=self).pack(fill="x",pady=(6,2))
            ProButton(p,"Clear",command=tvm_clear([pv,fv,iy,n],res),
                bg_color="danger",hover_color="danger_hover",fg_color="text",
                font_size=12,min_height=40,radius=20).pack(fill="x",pady=(2,4))

        # ── N ──
        def panel_n(p):
            pv,fv=row2(p,"Present Value (PV)","Future Value (FV)")
            iy,pmt=row2(p,"Interest Rate I/Y (%/yr)","Payment (PMT) — 0 if none")
            res=solve_field(p,"Periods (N)")
            def calc():
                try:
                    if not all(v.get().strip() for v in [pv,fv,iy]):
                        msg="⚠ Fill in PV, FV and I/Y."
                        res.set(msg); self.show_result(msg,label="TVM"); return
                    pv_=float(pv.get()); fv_=float(fv.get())
                    r=float(iy.get())/100; pmt_=float(pmt.get() or 0)
                    import math as _m
                    if r==0:
                        if not pmt_: raise ValueError("Cannot solve N when rate=0 and PMT=0")
                        nv=-(pv_+fv_)/pmt_
                    elif pmt_==0: nv=_m.log(-fv_/pv_)/_m.log(1+r)
                    else: nv=_m.log((-fv_*r+pmt_)/(pv_*r+pmt_))/_m.log(1+r)
                    res.set(f"{nv:.4f} periods")
                    self.show_result(f"N = {nv:.4f} periods",label="TVM")
                except ValueError:
                    msg="Error: Invalid input — letters not allowed."
                    res.set(msg); self.show_result(msg,label="TVM")
                except Exception:
                    msg="Error: Could not calculate."
                    res.set(msg); self.show_result(msg,label="TVM")
            calc_btn(p,"Calculate N",calc,app=self).pack(fill="x",pady=(6,2))
            ProButton(p,"Clear",command=tvm_clear([pv,fv,iy,pmt],res),
                bg_color="danger",hover_color="danger_hover",fg_color="text",
                font_size=12,min_height=40,radius=20).pack(fill="x",pady=(2,4))

        # ── I/Y ──
        def panel_iy(p):
            pv,fv=row2(p,"Present Value (PV)","Future Value (FV)")
            n,pmt=row2(p,"Periods (N)","Payment (PMT) — 0 if none")
            res=solve_field(p,"Interest Rate I/Y (%)")
            def calc():
                try:
                    if not all(v.get().strip() for v in [pv,fv,n]):
                        msg="⚠ Fill in PV, FV and N."
                        res.set(msg); self.show_result(msg,label="TVM"); return
                    pv_=float(pv.get()); fv_=float(fv.get())
                    n_=float(n.get()); pmt_=float(pmt.get() or 0)
                    rate=0.1
                    for _ in range(1000):
                        r1=(1+rate)**n_
                        f=pv_*r1+pmt_*(r1-1)/rate+fv_ if rate!=0 else pv_+pmt_*n_+fv_
                        df=n_*pv_*(1+rate)**(n_-1)+pmt_*((n_*rate*(1+rate)**(n_-1)*(rate)-(r1-1)))/(rate**2) if rate!=0 else 0
                        if df==0: break
                        delta=f/df; rate-=delta
                        if abs(delta)<1e-10: break
                    res.set(f"{rate*100:.4f}% per period")
                    self.show_result(f"I/Y = {rate*100:.4f}%",label="TVM")
                except ValueError:
                    msg="Error: Invalid input — letters not allowed."
                    res.set(msg); self.show_result(msg,label="TVM")
                except Exception:
                    msg="Error: Could not calculate."
                    res.set(msg); self.show_result(msg,label="TVM")
            calc_btn(p,"Calculate I/Y",calc,app=self).pack(fill="x",pady=(6,2))
            ProButton(p,"Clear",command=tvm_clear([pv,fv,n,pmt],res),
                bg_color="danger",hover_color="danger_hover",fg_color="text",
                font_size=12,min_height=40,radius=20).pack(fill="x",pady=(2,4))

        tvm_panels={"FV":panel_fv,"PV":panel_pv,"PMT":panel_pmt,"N":panel_n,"I/Y":panel_iy}
        for i,name in enumerate(tvm_tabs):
            b=self._tab_btn(tvm_bar,name,lambda n=name:tvm_switch(n))
            b.grid(row=0,column=i,sticky="ew",padx=2)
            tvm_btns[name]=b
        tvm_switch("FV")

    # ────────────────────────────────────────
    # TRIGONOMETRY  (isolated StringVar)
    # ────────────────────────────────────────
    def _render_trig(self, parent):
        frame = tk.Frame(parent, bg=T["bg"])
        frame.pack(fill="both", expand=True)

        tabs = ["Trig Values", "Find Side", "Find Angle"]
        tab_btns = {}
        tab_bar = tk.Frame(frame, bg=T["bg"])
        tab_bar.pack(fill="x", pady=(0,8))
        for c in range(3): tab_bar.columnconfigure(c, weight=1, uniform="tr")
        cf = tk.Frame(frame, bg=T["bg"])
        cf.pack(fill="both", expand=True)
        cf.pack_propagate(False)

        def switch(name):
            for n,b in tab_btns.items():
                b.set_colors("green" if n==name else "surface2",
                            "green_hover" if n==name else "sci_hover","text")
            for w in cf.winfo_children(): w.destroy()
            self.display.set("0")
            self.expression.set("")
            self.preview.set("Ready")
            panels[name](cf)

        def safe(fn, *args):
            try:
                r = fn(*args)
                if math.isnan(r) or math.isinf(r):
                    return "undefined"
                if abs(r) > 1e15:
                    exp = int(math.floor(math.log10(abs(r))))
                    mantissa = r / (10**exp)
                    return f"{mantissa:.4f}×10^{exp}"
                return f"{r:.8g}"
            except:
                return "undefined"

        # ── Input field with inline clear button ──
        def tf(p, lbl, hint=""):
            tlabel(p, lbl, size=9, muted=True).pack(anchor="w", pady=(6,1))
            v = tk.StringVar()
            e = tk.Entry(p, textvariable=v, bg=T["surface2"], fg=T["text"],
                        insertbackground=T["text"], relief="flat",
                        font=(APP_FONT,12), highlightthickness=1,
                        highlightcolor=T["green"], highlightbackground=T["border"])
            e.pack(fill="x", ipady=5)
            e.bind("<Button-1>", lambda _: e.focus_set())
            if hint: tlabel(p, hint, size=8, muted=True).pack(anchor="w")
            return v

        # ── Two-column input row, each with clear button ──
        def row2(p, l1, l2):
            f = tk.Frame(p, bg=T["bg"]); f.pack(fill="x")
            f.columnconfigure(0, weight=1, uniform="r")
            f.columnconfigure(1, weight=1, uniform="r")
            v1 = tk.StringVar(); v2 = tk.StringVar()
            def col(lbl, var, c, pad):
                tlabel(f, lbl, size=9, muted=True).grid(row=0, column=c, sticky="w", padx=pad, pady=(6,1))
                e = tk.Entry(f, textvariable=var, bg=T["surface2"], fg=T["text"],
                            insertbackground=T["text"], relief="flat",
                            font=(APP_FONT,12), highlightthickness=1,
                            highlightcolor=T["green"], highlightbackground=T["border"])
                e.grid(row=1, column=c, sticky="ew", ipady=5, padx=pad)
                e.bind("<Button-1>", lambda _: e.focus_set())
            col(l1, v1, 0, (0,4)); col(l2, v2, 1, (4,0))
            return v1, v2

        # ── Reusable full-width Calculate + Clear row ──
     
        def btn_row(p, calc_label, calc_fn, clear_fn):
            calc_btn(p, calc_label, calc_fn, app=self).pack(fill="x", pady=(6,2))
            ProButton(p, "Clear", command=clear_fn,
                bg_color="danger", hover_color="danger_hover", fg_color="text",
                font_size=12, min_height=40, radius=20).pack(fill="x", pady=(0,4))
        
        def res_field(p, lbl):
            tlabel(p, lbl, size=9, fg_key="green").pack(anchor="w", pady=(8,1))
            v = tk.StringVar()
            e = tk.Entry(p, textvariable=v, state="readonly",
                        bg=T["surface3"], fg=T["green"],
                        readonlybackground=T["surface3"], relief="flat",
                        font=(APP_FONT,13,"bold"), highlightthickness=1,
                        highlightcolor=T["green"], highlightbackground=T["green"])
            e.pack(fill="x", ipady=7)
            return v

        def res2(p, l1, l2):
            f = tk.Frame(p, bg=T["bg"]); f.pack(fill="x", pady=(8,0))
            f.columnconfigure(0, weight=1, uniform="r")
            f.columnconfigure(1, weight=1, uniform="r")
            v1 = tk.StringVar(); v2 = tk.StringVar()
            def col(lbl, var, c, pad):
                tlabel(f, lbl, size=9, fg_key="green").grid(row=0, column=c, sticky="w", padx=pad)
                e = tk.Entry(f, textvariable=var, state="readonly",
                            bg=T["surface3"], fg=T["green"],
                            readonlybackground=T["surface3"], relief="flat",
                            font=(APP_FONT,12,"bold"), highlightthickness=1,
                            highlightcolor=T["green"], highlightbackground=T["green"])
                e.grid(row=1, column=c, sticky="ew", ipady=6, padx=pad)
            col(l1, v1, 0, (0,4)); col(l2, v2, 1, (4,0))
            return v1, v2

        def mode_row(p):
            mv = tk.StringVar(value="DEG")
            mf = tk.Frame(p, bg=T["bg"]); mf.pack(fill="x", pady=(0,4))
            tlabel(mf, "Angle unit:", size=9, muted=True).pack(side="left", padx=(0,8))
            for m in ["DEG","RAD","GRAD"]:
                tk.Radiobutton(mf, text=m, variable=mv, value=m,
                    bg=T["bg"], fg=T["text"], selectcolor=T["surface2"],
                    activebackground=T["bg"], activeforeground=T["green"],
                    font=(APP_FONT,9)).pack(side="left", padx=4)
            return mv

        def to_rad(v, mode):
            if mode == "DEG":  return math.radians(v)
            if mode == "GRAD": return v * math.pi / 200
            return v  # RAD — already radians, pass as-is


        # ── Tab 1: Trig Values (no scroll) ──
        def panel_trig(p):
            p = self._full_frame(p)

            mv = tk.StringVar(value="DEG")
            mf = tk.Frame(p, bg=T["bg"]); mf.pack(fill="x", pady=(0,4))
            tlabel(mf, "Angle unit:", size=9, muted=True).pack(side="left", padx=(0,8))
            for m_opt in ["DEG","RAD","GRAD"]:
                tk.Radiobutton(mf, text=m_opt, variable=mv, value=m_opt,
                    bg=T["bg"], fg=T["text"], selectcolor=T["surface2"],
                    activebackground=T["bg"], activeforeground=T["green"],
                    font=(APP_FONT,9)).pack(side="left", padx=4)

            ang = tf(p, "Angle value")

            res_frame = tk.Frame(p, bg=T["bg"])
            res_frame.pack(fill="x", pady=(8,0))
            for c in range(3): res_frame.columnconfigure(c, weight=1, uniform="rv")
            labels = ["sin","cos","tan","csc","sec","cot","sinh","cosh","tanh"]
            res_vars = {}
            for i,lbl in enumerate(labels):
                r,c = divmod(i,3)
                outer = tk.Frame(res_frame, bg=T["border"], padx=1, pady=1)
                outer.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)
                tlabel(outer, lbl, size=9, muted=True).pack(anchor="w", padx=8, pady=(4,0))
                v = tk.StringVar(value="—")
                tk.Label(outer, textvariable=v, bg=T["surface3"], fg=T["green"],
                        font=(APP_FONT,11,"bold"), padx=8, pady=4, anchor="w"
                        ).pack(fill="x")
                res_vars[lbl] = v

            def _reset():
                ang.set("")
                for v in res_vars.values(): v.set("—")

            def calc():
                raw_str = ang.get().strip()
                if not raw_str:
                    for v in res_vars.values(): v.set("—")
                    return
                try:
                    raw = float(raw_str)
                except ValueError:
                    for v in res_vars.values(): v.set("err")
                    return
                m = mv.get()
                r = to_rad(raw, m)
                s, c2 = math.sin(r), math.cos(r)
                res_vars["sin"].set(safe(math.sin, r))
                res_vars["cos"].set(safe(math.cos, r))
                res_vars["tan"].set("undefined" if abs(c2)<1e-12 else safe(math.tan, r))
                res_vars["csc"].set("undefined" if abs(s)<1e-12  else safe(lambda x: 1/math.sin(x), r))
                res_vars["sec"].set("undefined" if abs(c2)<1e-12 else safe(lambda x: 1/math.cos(x), r))
                res_vars["cot"].set("undefined" if abs(s)<1e-12  else safe(lambda x: math.cos(x)/math.sin(x), r))
                hyp_r = math.radians(raw) if m != "RAD" else raw
                res_vars["sinh"].set(safe(math.sinh, hyp_r))
                res_vars["cosh"].set(safe(math.cosh, hyp_r))
                res_vars["tanh"].set(safe(math.tanh, hyp_r))
                self.show_result(
                    f"sin={res_vars['sin'].get()}  cos={res_vars['cos'].get()}  tan={res_vars['tan'].get()}\n"
                    f"csc={res_vars['csc'].get()}  sec={res_vars['sec'].get()}  cot={res_vars['cot'].get()}\n"
                    f"sinh={res_vars['sinh'].get()}  cosh={res_vars['cosh'].get()}  tanh={res_vars['tanh'].get()}",
                    label=f"Trig ({raw} {m})"
                )

            ang.trace_add("write", lambda *_: calc())
            mv.trace_add("write", lambda *_: calc())
            btn_row(p, "Calculate", calc, _reset)

        # ── Tab 2: Find Side ──
        
        def panel_side(p):
            inner = self._scrollable(p)
            p = self._full_frame(inner)
            tlabel(p, "c = hypotenuse   a = opposite   b = adjacent", size=9, muted=True).pack(anchor="w", pady=(0,6))

            # ── Section 1: a + b → c ──
            tlabel(p, "Find hypotenuse c from sides a and b", size=10, bold=True, fg_key="green").pack(anchor="w", pady=(4,2))
            s1a, s1b = row2(p, "Side a (opposite)", "Side b (adjacent)")
            s1c_res = res_field(p, "Hypotenuse c  ← result")

            def calc_c():
                s1c_res.set("—")
                try:
                    a1, b1 = float(s1a.get()), float(s1b.get())
                    if a1 <= 0 or b1 <= 0: raise ValueError("Sides must be greater than 0")
                    r = math.sqrt(a1**2 + b1**2)
                    s1c_res.set(f"{r:.8g}")
                    self.show_result(f"c = {r:.8g}", label="Find Side")
                except ValueError as ex: s1c_res.set(f"Error: {ex}")
                except: s1c_res.set("—")

            def clear_c(): s1a.set(""); s1b.set(""); s1c_res.set("—")
            btn_row(p, "Calculate c", calc_c, clear_c)

            tk.Frame(p, bg=T["border"], height=1).pack(fill="x", pady=8)

            # ── Section 2: a + c → b ──
            tlabel(p, "Find adjacent b from opposite a and hypotenuse c", size=10, bold=True, fg_key="green").pack(anchor="w", pady=(4,2))
            s2a, s2c = row2(p, "Side a (opposite)", "Hypotenuse c")
            s2b_res = res_field(p, "Side b (adjacent)  ← result")

            def calc_b():
                s2b_res.set("—")
                try:
                    a2, c2 = float(s2a.get()), float(s2c.get())
                    if a2 <= 0 or c2 <= 0: raise ValueError("Sides must be greater than 0")
                    if c2 <= a2: raise ValueError("Hypotenuse c must be greater than a")
                    r = math.sqrt(c2**2 - a2**2)
                    s2b_res.set(f"{r:.8g}")
                    self.show_result(f"b = {r:.8g}", label="Find Side")
                except ValueError as ex: s2b_res.set(f"Error: {ex}")
                except: s2b_res.set("—")

            def clear_b(): s2a.set(""); s2c.set(""); s2b_res.set("—")
            btn_row(p, "Calculate b", calc_b, clear_b)

            tk.Frame(p, bg=T["border"], height=1).pack(fill="x", pady=8)

            # ── Section 3: b + c → a ──
            tlabel(p, "Find opposite a from adjacent b and hypotenuse c", size=10, bold=True, fg_key="green").pack(anchor="w", pady=(4,2))
            s3b, s3c = row2(p, "Side b (adjacent)", "Hypotenuse c")
            s3a_res = res_field(p, "Side a (opposite)  ← result")

            def calc_a():
                s3a_res.set("—")
                try:
                    b3, c3 = float(s3b.get()), float(s3c.get())
                    if b3 <= 0 or c3 <= 0: raise ValueError("Sides must be greater than 0")
                    if c3 <= b3: raise ValueError("Hypotenuse c must be greater than b")
                    r = math.sqrt(c3**2 - b3**2)
                    s3a_res.set(f"{r:.8g}")
                    self.show_result(f"a = {r:.8g}", label="Find Side")
                except ValueError as ex: s3a_res.set(f"Error: {ex}")
                except: s3a_res.set("—")

            def clear_a(): s3b.set(""); s3c.set(""); s3a_res.set("—")
            btn_row(p, "Calculate a", calc_a, clear_a)

            tk.Frame(p, bg=T["border"], height=1).pack(fill="x", pady=10)

            # ── Section 4: angle + one side → all sides ──
            tlabel(p, "Find sides from angle + one known side", size=10, bold=True, fg_key="green").pack(anchor="w", pady=(4,2))
            mv = mode_row(p)
            t_ang = tf(p, "Angle θ")
            tlabel(p, "Known side:", size=9, muted=True).pack(anchor="w", pady=(4,1))
            known_frame = tk.Frame(p, bg=T["bg"]); known_frame.pack(fill="x")
            known_frame.columnconfigure(0, weight=1); known_frame.columnconfigure(1, weight=1)
            side_choice = tk.StringVar(value="a")
            known_val = tk.StringVar()
            ttk.Combobox(known_frame, textvariable=side_choice,
                        values=["a (opposite)", "b (adjacent)", "c (hypotenuse)"],
                        state="readonly", font=(APP_FONT,11), style="C.TCombobox"
                        ).grid(row=0, column=0, sticky="ew", padx=(0,4), ipady=4)
            tentry(known_frame, known_val, 11).grid(row=0, column=1, sticky="ew", padx=(4,0), ipady=4)
            ra = res_field(p, "a (opposite)  ← result")
            rb = res_field(p, "b (adjacent)  ← result")
            rc = res_field(p, "c (hypotenuse)  ← result")

            def calc_angle_side():
                ra.set("—"); rb.set("—"); rc.set("—")
                try:
                    ang_v = float(t_ang.get()); r = to_rad(ang_v, mv.get())
                    kv = float(known_val.get()); ch = side_choice.get()[0]
                    if kv <= 0: raise ValueError("Known side must be greater than 0")
                    if ch == "a":
                        a = kv; c_ = a/math.sin(r); b = math.sqrt(c_**2 - a**2)
                    elif ch == "b":
                        b = kv; c_ = b/math.cos(r); a = math.sqrt(c_**2 - b**2)
                    else:
                        c_ = kv; a = c_*math.sin(r); b = c_*math.cos(r)
                    ra.set(f"{a:.8g}"); rb.set(f"{b:.8g}"); rc.set(f"{c_:.8g}")
                    self.show_result(f"a={a:.6g}  b={b:.6g}  c={c_:.6g}", label=f"θ={ang_v} {mv.get()}")
                except ValueError as ex:
                    ra.set(f"Error: {ex}"); rb.set("—"); rc.set("—")
                except Exception as ex:
                    ra.set(f"Error: {ex}"); rb.set("—"); rc.set("—")

            def clear_angle_side():
                t_ang.set(""); known_val.set("")
                ra.set("—"); rb.set("—"); rc.set("—")
            btn_row(p, "Calculate Sides from Angle", calc_angle_side, clear_angle_side)

        # ── Tab 3: Find Angle ──
        def panel_angle(p):
            inner = self._scrollable(p)
            p = self._full_frame(inner)
            tlabel(p, "c = hypotenuse   a = opposite   b = adjacent", size=9, muted=True).pack(anchor="w", pady=(0,6))
            mv = mode_row(p)

            def from_rad(v, mode):
                if mode=="DEG":  return math.degrees(v)
                if mode=="GRAD": return v * 200 / math.pi
                return v

            # ── Section 1: sin θ = a/c ──
            tlabel(p, "sin θ = a/c  →  enter opposite (a) and hypotenuse (c)", size=9, bold=True, fg_key="green").pack(anchor="w", pady=(8,2))
            a1, c1 = row2(p, "a (opposite)", "c (hypotenuse)")
            r1a, r1b = res2(p, "sin θ", "θ (angle)")

            def calc_sin():
                r1a.set("—"); r1b.set("—")
                try:
                    av, cv = float(a1.get()), float(c1.get())
                    if cv <= 0: raise ValueError("c must be > 0")
                    if av > cv: raise ValueError("a cannot be greater than c")
                    ratio = av/cv
                    angle = from_rad(math.asin(ratio), mv.get())
                    r1a.set(f"{ratio:.8g}")
                    r1b.set(f"{angle:.8g}°" if mv.get()=="DEG" else f"{angle:.8g}")
                    self.show_result(f"sin θ = {ratio:.8g}   θ = {angle:.8g}", label="Find Angle")
                except ValueError as ex:
                    r1a.set(f"Error: {ex}"); r1b.set("—")
                except:
                    r1a.set("—"); r1b.set("—")

            def clear_sin(): a1.set(""); c1.set(""); r1a.set("—"); r1b.set("—")
            btn_row(p, "Calculate sin θ", calc_sin, clear_sin)

            tk.Frame(p, bg=T["border"], height=1).pack(fill="x", pady=8)

            # ── Section 2: cos θ = b/c ──
            tlabel(p, "cos θ = b/c  →  enter adjacent (b) and hypotenuse (c)", size=9, bold=True, fg_key="green").pack(anchor="w", pady=(4,2))
            b2, c2 = row2(p, "b (adjacent)", "c (hypotenuse)")
            r2a, r2b = res2(p, "cos θ", "θ (angle)")

            def calc_cos():
                r2a.set("—"); r2b.set("—")
                try:
                    bv, cv = float(b2.get()), float(c2.get())
                    if cv <= 0: raise ValueError("c must be > 0")
                    if bv > cv: raise ValueError("b cannot be greater than c")
                    ratio = bv/cv
                    angle = from_rad(math.acos(ratio), mv.get())
                    r2a.set(f"{ratio:.8g}")
                    r2b.set(f"{angle:.8g}°" if mv.get()=="DEG" else f"{angle:.8g}")
                    self.show_result(f"cos θ = {ratio:.8g}   θ = {angle:.8g}", label="Find Angle")
                except ValueError as ex:
                    r2a.set(f"Error: {ex}"); r2b.set("—")
                except:
                    r2a.set("—"); r2b.set("—")

            def clear_cos(): b2.set(""); c2.set(""); r2a.set("—"); r2b.set("—")
            btn_row(p, "Calculate cos θ", calc_cos, clear_cos)

            tk.Frame(p, bg=T["border"], height=1).pack(fill="x", pady=8)

            # ── Section 3: tan θ = a/b ──
            tlabel(p, "tan θ = a/b  →  enter opposite (a) and adjacent (b)", size=9, bold=True, fg_key="green").pack(anchor="w", pady=(4,2))
            a3, b3 = row2(p, "a (opposite)", "b (adjacent)")
            r3a, r3b = res2(p, "tan θ", "θ (angle)")

            def calc_tan():
                r3a.set("—"); r3b.set("—")
                try:
                    av, bv = float(a3.get()), float(b3.get())
                    if bv == 0: raise ValueError("b cannot be zero")
                    ratio = av/bv
                    angle = from_rad(math.atan(ratio), mv.get())
                    r3a.set(f"{ratio:.8g}")
                    r3b.set(f"{angle:.8g}°" if mv.get()=="DEG" else f"{angle:.8g}")
                    self.show_result(f"tan θ = {ratio:.8g}   θ = {angle:.8g}", label="Find Angle")
                except ValueError as ex:
                    r3a.set(f"Error: {ex}"); r3b.set("—")
                except:
                    r3a.set("—"); r3b.set("—")

            def clear_tan(): a3.set(""); b3.set(""); r3a.set("—"); r3b.set("—")
            btn_row(p, "Calculate tan θ", calc_tan, clear_tan)

        panels = {"Trig Values": panel_trig, "Find Side": panel_side, "Find Angle": panel_angle}

        for i,name in enumerate(tabs):
            b = self._tab_btn(tab_bar, name, lambda n=name: switch(n))
            b.grid(row=0, column=i, sticky="ew", padx=3)
            tab_btns[name] = b

        switch("Trig Values")

    # ────────────────────────────────────────
    # PROGRAMMING  (isolated StringVars)
    # ────────────────────────────────────────
    def _render_programming(self, parent):
        frame = tk.Frame(parent, bg=T["bg"])
        frame.pack(fill="both", expand=True)

        cur=[0]; base=[10]; signed=[True]
        pending_op=[None]; pending_val=[None]; inputting=[False]
        MASK=0xFFFFFFFF
        ASCII_NAMES=['NUL','SOH','STX','ETX','EOT','ENQ','ACK','BEL','BS','TAB',
                    'LF','VT','FF','CR','SO','SI','DLE','DC1','DC2','DC3','DC4',
                    'NAK','SYN','ETB','CAN','EM','SUB','ESC','FS','GS','RS','US','SPC']

        def fmt_bin(n,bits=32):
            s=format(n&MASK,f'0{bits}b')
            return ' '.join(s[i:i+4] for i in range(0,bits,4))
        def fmt_hex(n):
            s=format(n&MASK,'08X')
            return s[:4]+' '+s[4:]

        def _bind_prog_keys(event):
            c = event.char.upper()
            if c in "0123456789":
                inp(c)
            elif c in "ABCDEF" and base[0] == 16:
                inp(c)
            elif c in "01" and base[0] == 2:
                inp(c)
            elif c in "01234567" and base[0] == 8:
                inp(c)
            elif event.keysym == "BackSpace":
                do_back()
            elif event.keysym == "Delete" or c == "C":
                do_ce()
            elif event.keysym == "Return":
                do_calc()

        self.root.bind("<Key>", _bind_prog_keys)
        def update():
            v=cur[0]&MASK
            if base[0]==10:
                disp=str(v-0x100000000) if signed[0] and (v&0x80000000) else str(v)
            elif base[0]==16: disp=format(v,'X')
            elif base[0]==2:  disp=fmt_bin(v)
            else:             disp=format(v,'o')
            self.display.set(disp or "0")
            byte=v&0xFF
            asc=ASCII_NAMES[byte] if byte<33 else chr(byte)
            dec_v=str(v-0x100000000) if signed[0] and (v&0x80000000) else str(v)
            self.show_result(
                f"HEX  {fmt_hex(v)}    DEC  {dec_v}\n"
                f"OCT  {format(v,'o')}    BIN  {fmt_bin(v,8)}\n"
                f"ASCII  {asc}",
                label=f"{'Signed' if signed[0] else 'Unsigned'} 32-bit"
            )
            build_bits(v)

        # ── Base selector + signed toggle ──
        top=tk.Frame(frame,bg=T["bg"]); top.pack(fill="x",pady=(0,4))
        for c in range(5): top.columnconfigure(c,weight=1,uniform="t")
        base_btns={}
        for ci,(bn,bv) in enumerate([("DEC",10),("HEX",16),("BIN",2),("OCT",8)]):
            def sw(bv=bv,bn=bn):
                base[0]=bv
                for n,b in base_btns.items():
                    b.set_colors("green" if n==bn else "surface2",
                                "green_hover" if n==bn else "sci_hover","text")
                inputting[0]=False; update()
            b=ProButton(top,bn,command=sw,
                        bg_color="green" if bv==10 else "surface2",
                        hover_color="green_hover" if bv==10 else "sci_hover",
                        fg_color="text",font_size=10,min_height=28,radius=14)
            b.grid(row=0,column=ci,padx=2,sticky="nsew")
            base_btns[bn]=b

        def toggle_signed():
            signed[0]=not signed[0]
            sign_btn.set_text("Signed" if signed[0] else "Unsigned")
            update()
        sign_btn=ProButton(top,"Signed",command=toggle_signed,
                        bg_color="surface2",hover_color="sci_hover",
                        fg_color="green",font_size=9,min_height=28,radius=14)
        sign_btn.grid(row=0,column=4,padx=2,sticky="nsew")

        # ── Bit grid ──
        bit_frame=tk.Frame(frame,bg=T["surface2"],
                        highlightbackground=T["border"],highlightthickness=1)
        bit_frame.pack(fill="x",pady=(0,5))
        tlabel(bit_frame,"32-bit — click to toggle",size=7,muted=True).pack(anchor="w",padx=6,pady=(2,1))
        bit_grid=tk.Frame(bit_frame,bg=T["surface2"]); bit_grid.pack(fill="x",padx=2,pady=(0,4))

        def build_bits(v):
            for w in bit_grid.winfo_children(): w.destroy()
            for grp in range(7,-1,-1):
                gf=tk.Frame(bit_grid,bg=T["surface2"]); gf.pack(side="left",padx=1)
                for i in range(grp*4+3,grp*4-1,-1):
                    on=(v>>i)&1; is_sign=(i==31)
                    fg=T["bg"] if on else (T["danger"] if is_sign else T["muted"])
                    bg=(T["danger"] if is_sign else T["green"]) if on else T["surface3"]
                    def make_toggle(bi):
                        def toggle():
                            cur[0]=(cur[0]^(1<<bi))&MASK
                            inputting[0]=False
                            update()
                        return toggle
                    b=tk.Label(gf,text=str(on),bg=bg,fg=fg,
                            font=(APP_FONT,10,"bold"),width=1,pady=1,
                            relief="flat",cursor="hand2",
                            highlightbackground=T["border"],highlightthickness=1)
                    b.pack(side="left",padx=1,pady=1)
                    b.bind("<Button-1>",lambda _,f=make_toggle(i):f())
                tk.Label(gf,text=str(grp*4+3),bg=T["surface2"],
                        fg=T["muted"],font=(APP_FONT,6)).pack()

        # ── Input helpers ──
        def inp(v):
            if not inputting[0]: cur[0]=0; inputting[0]=True
            if base[0]==10:
                if not v.isdigit(): return
                cur[0]=cur[0]*10+int(v)
            elif base[0]==16:
                try: cur[0]=(cur[0]*16+int(v,16))&MASK
                except: return
            elif base[0]==2:
                if v not in "01": return
                cur[0]=(cur[0]*2+int(v))&MASK
            else:
                if v not in "01234567": return
                cur[0]=(cur[0]*8+int(v))&MASK
            update()

        def do_ce(): cur[0]=0;pending_op[0]=None;pending_val[0]=None;inputting[0]=False;update()
        def do_back():
            if base[0]==10:  cur[0]=cur[0]//10
            elif base[0]==16: cur[0]=(cur[0]//16)&MASK
            elif base[0]==2:  cur[0]=(cur[0]//2)&MASK
            else:             cur[0]=(cur[0]//8)&MASK
            update()
        def do_bitop(op): pending_op[0]=op;pending_val[0]=cur[0];inputting[0]=False
        def do_calc():
            if pending_op[0] is None or pending_val[0] is None: return
            a=pending_val[0]&MASK; b=cur[0]&MASK
            ops={
                "AND":  a&b,
                "OR":   a|b,
                "XOR":  a^b,
                "NAND": (~(a&b))&MASK,
                "NOR":  (~(a|b))&MASK,
                "XNOR": (~(a^b))&MASK,
                "MOD":  a%b if b else a,
                "ADD":  (a+b)&MASK,
                "SUB":  (a-b)&MASK,
                "MUL":  (a*b)&MASK,
                "DIV":  a//b if b else a,
            }
            if pending_op[0] in ops: cur[0]=ops[pending_op[0]]
            pending_op[0]=None;pending_val[0]=None;inputting[0]=False;update()
        def do_not():
            cur[0] = (~(cur[0] & MASK)) & MASK
            inputting[0] = False
            update()
        def do_shl():  cur[0]=(cur[0]<<1)&MASK;update()
        def do_shr():  cur[0]=(cur[0]>>1)&MASK;update()
        def do_rol():  v=cur[0]&MASK;cur[0]=((v<<1)|(v>>31))&MASK;update()
        def do_ror():  v=cur[0]&MASK;cur[0]=((v>>1)|((v&1)<<31))&MASK;update()

        # ── HEX digit row ──
        hf=tk.Frame(frame,bg=T["bg"]); hf.pack(fill="x",pady=(0,3))
        for c in range(6): hf.columnconfigure(c,weight=1,uniform="h")
        for ci,h in enumerate(["A","B","C","D","E","F"]):
            ProButton(hf,h,command=lambda v=h:inp(v),
                    bg_color="sci",hover_color="sci_hover",fg_color="accent",
                    font_size=12,min_height=36,radius=18
                    ).grid(row=0,column=ci,padx=2,pady=1,sticky="nsew")

        # ── Main keypad ──
        kf=tk.Frame(frame,bg=T["bg"]); kf.pack(fill="both",expand=True)
        for c in range(4): kf.columnconfigure(c,weight=1,uniform="k")
        for r in range(5): kf.rowconfigure(r,weight=1,uniform="k")

        rows=[
            [("CE","danger","danger_hover"),("⌫","grey","grey_hover"),("MOD","green","green_hover"),("÷","green","green_hover")],
            [("7","surface3","num_hover"),("8","surface3","num_hover"),("9","surface3","num_hover"),("×","green","green_hover")],
            [("4","surface3","num_hover"),("5","surface3","num_hover"),("6","surface3","num_hover"),("−","green","green_hover")],
            [("1","surface3","num_hover"),("2","surface3","num_hover"),("3","surface3","num_hover"),("+","green","green_hover")],
            [("±","grey","grey_hover"),("0","surface3","num_hover"),(".","surface3","num_hover"),("=","green_dark","green_darkhover")],
        ]
        def key_cmd(lbl):
            if lbl=="CE":  return do_ce
            if lbl=="⌫":  return do_back
            if lbl=="=":   return do_calc
            if lbl=="MOD": return lambda: do_bitop("MOD")
            if lbl=="÷":   return lambda: do_bitop("DIV")
            if lbl=="×":   return lambda: do_bitop("MUL")
            if lbl=="−":   return lambda: do_bitop("SUB")
            if lbl=="+":   return lambda: do_bitop("ADD")
            if lbl=="±":   return lambda: (cur.__setitem__(0, (-cur[0]) & MASK), update())
            if lbl==".":   return lambda: None
            if lbl in "0123456789": return lambda v=lbl: inp(v)
            return lambda: None
        for ri,row in enumerate(rows):
            for ci,(lbl,bg,hov) in enumerate(row):
                ProButton(kf,lbl,command=key_cmd(lbl),
                        bg_color=bg,hover_color=hov,fg_color="text",
                        font_size=15,min_height=44,radius=22
                        ).grid(row=ri,column=ci,padx=3,pady=3,sticky="nsew")

        # ── Bitwise ops ──
        tlabel(frame,"Bitwise",size=8,muted=True).pack(anchor="w",pady=(4,2))
        bf=tk.Frame(frame,bg=T["bg"]); bf.pack(fill="x")
        for c in range(6): bf.columnconfigure(c,weight=1,uniform="b")
        bops=[("AND",lambda:do_bitop("AND")),("OR",lambda:do_bitop("OR")),
            ("XOR",lambda:do_bitop("XOR")),("NOT",do_not),
            ("NAND",lambda:do_bitop("NAND")),("NOR",lambda:do_bitop("NOR")),
            ("XNOR",lambda:do_bitop("XNOR")),("SHL",do_shl),
            ("SHR",do_shr),("RoL",do_rol),("RoR",do_ror),("=",do_calc)]
        for i,(lbl,cmd) in enumerate(bops):
            r,c=divmod(i,6)
            ProButton(bf,lbl,command=cmd,
                    bg_color="sci",hover_color="sci_hover",fg_color="green",
                    font_size=9,min_height=30,radius=15
                    ).grid(row=r,column=c,padx=2,pady=2,sticky="nsew")

        update()
        self.root.unbind("<Key>")
        self.root.bind("<Key>", _bind_prog_keys)

    # ────────────────────────────────────────
    # EQUATION SOLVER  (isolated StringVars)
    # ────────────────────────────────────────

    def _render_eq_solver(self, parent):
        from sympy import (symbols, solve, simplify, expand, factor, diff, integrate, # type: ignore
                        sympify, latex, pretty, S, sqrt, I, Rational, oo,
                        Symbol, Eq, linsolve, nonlinsolve, solveset, Reals, Complexes)
        from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication_application # type: ignore

        frame=tk.Frame(parent,bg=T["bg"]); frame.pack(fill="both",expand=True)
        tab_btns={}

        # ── 2-row tab bar at the TOP ──
        tab_bar2=tk.Frame(frame,bg=T["bg"]); tab_bar2.pack(fill="x",pady=(0,6))
        row1=tk.Frame(tab_bar2,bg=T["bg"]); row1.pack(fill="x",pady=(0,3))
        row2=tk.Frame(tab_bar2,bg=T["bg"]); row2.pack(fill="x")
        for c in range(3):
            row1.columnconfigure(c,weight=1,uniform="eq")
            row2.columnconfigure(c,weight=1,uniform="eq")

        cf=tk.Frame(frame,bg=T["bg"]); cf.pack(fill="both",expand=True)
        cf.pack_propagate(False)

        def switch(name):
            # Point 3: clear top output box when switching tabs
            self.display.set("0")
            self.expression.set("")
            self.preview.set("Ready")
            for n,b in tab_btns.items():
                b.set_colors("green" if n==name else "surface2",
                            "green_hover" if n==name else "sci_hover","text")
            for w in cf.winfo_children(): w.destroy()
            panels[name](cf)

        def pexpr(s):
            trans=(standard_transformations+(implicit_multiplication_application,))
            return parse_expr(s.strip(), transformations=trans)

        def show(result, label=""):
            self.show_result(result, label=label)

        def sf(p, lbl, hint=""):
            tlabel(p,lbl,size=9,muted=True).pack(anchor="w",pady=(6,1))
            v=tk.StringVar()
            tentry(p,v,12).pack(fill="x",ipady=5)
            if hint: tlabel(p,hint,size=8,muted=True).pack(anchor="w")
            return v

        def res_box(p):
            v=tk.StringVar(value="")
            outer=tk.Frame(p,bg=T["border"],padx=1,pady=1)
            tk.Label(outer,textvariable=v,bg=T["surface3"],fg=T["green"],
                    font=(APP_FONT,11,"bold"),padx=14,pady=10,
                    anchor="w",justify="left",wraplength=480).pack(fill="both",expand=True)
            def on_change(*_):
                if v.get(): outer.pack(fill="x",pady=(8,0))
                else: outer.pack_forget()
            v.trace_add("write",on_change)
            on_change()
            return v

        def full(p):
            inner=self._scrollable(p)
            f=tk.Frame(inner,bg=T["bg"]); f.pack(fill="x",padx=10,pady=4)
            return f

        def clear_btn(p, fields, res_var):
            """Point 2: Clear button — wipes all input fields and local res box and top display."""
            def do_clear():
                for fv in fields:
                    fv.set("")
                res_var.set("")
                self.display.set("0")
                self.expression.set("")
                self.preview.set("Ready")
            ProButton(p,"Clear",command=do_clear,
                bg_color="danger",hover_color="danger_hover",fg_color="text",
                font_size=12,min_height=40,radius=20).pack(fill="x",pady=(4,2))

        # ── Tab 1: Equation ──
        def panel_eq(p):
            p=full(p)
            tlabel(p,"Solve any equation for x  e.g.  x**2 - 4 = 0  or  sin(x) = 0.5",
                size=9,muted=True).pack(anchor="w",pady=(0,4))
            expr=sf(p,"Equation (use x as variable, write both sides with =)")
            domain_var=tk.StringVar(value="Real")
            dr=tk.Frame(p,bg=T["bg"]); dr.pack(fill="x",pady=(4,0))
            tlabel(dr,"Domain:",size=9,muted=True).pack(side="left",padx=(0,8))
            for d in ["Real","Complex"]:
                tk.Radiobutton(dr,text=d,variable=domain_var,value=d,
                    bg=T["bg"],fg=T["text"],selectcolor=T["surface2"],
                    activebackground=T["bg"],font=(APP_FONT,9)).pack(side="left",padx=4)
            res=res_box(p)
            def solve_eq():
                try:
                    raw=expr.get().strip()
                    if not raw:
                        msg="⚠ Please enter an equation."
                        res.set(msg); show(msg,label="Equation"); return
                    x=symbols('x')
                    if "=" in raw:
                        lhs,rhs=raw.split("=",1)
                        eq=Eq(pexpr(lhs),pexpr(rhs))
                    else:
                        eq=Eq(pexpr(raw),0)
                    dom=Reals if domain_var.get()=="Real" else Complexes
                    sol=solveset(eq,x,domain=dom)
                    lines=[f"Solving: {eq}",""]
                    if sol.is_empty:
                        lines.append("No solution")
                    elif sol.is_finite_set:
                        for i,s in enumerate(sol,1):
                            lines.append(f"x{i} = {s}  ≈  {float(s.evalf()):.8g}" if s.is_real else f"x{i} = {s}")
                    else:
                        lines.append(f"Solution set: {sol}")
                    result="\n".join(lines)
                    res.set(result); show(result,label="Equation")
                except Exception as ex:
                    msg=f"Error: {ex}"
                    res.set(msg); show(msg,label="Equation")
            calc_btn(p,"Solve Equation",solve_eq,app=self).pack(fill="x",pady=(8,2))
            clear_btn(p,[expr],res)

        # ── Tab 2: System of equations ──
        def panel_system(p):
            p=full(p)
            tlabel(p,"System of equations — 2 or 3 equations",size=9,muted=True).pack(anchor="w",pady=(0,4))
            e1=sf(p,"Equation 1  e.g.  2*x + y = 5")
            e2=sf(p,"Equation 2  e.g.  x - y = 1")
            e3=sf(p,"Equation 3  (optional, for 3 variables)")
            res=res_box(p)
            def solve_sys():
                try:
                    x,y,z=symbols('x y z')
                    def parse_eq(s):
                        s=s.strip()
                        if not s: return None
                        if "=" in s:
                            l,r=s.split("=",1)
                            return Eq(pexpr(l),pexpr(r))
                        return Eq(pexpr(s),0)
                    eqs=[parse_eq(e.get()) for e in [e1,e2,e3] if e.get().strip()]
                    if len(eqs)<2:
                        msg="⚠ Enter at least 2 equations."
                        res.set(msg); show(msg,label="System"); return
                    var_syms=[x,y] if len(eqs)==2 else [x,y,z]
                    sol=solve(eqs,var_syms)
                    if not sol:
                        try:
                            from sympy import linear_eq_to_matrix
                            A,b=linear_eq_to_matrix(eqs,var_syms)
                            rank_A=A.rank()
                            rank_aug=A.row_join(b).rank()
                            if rank_aug > rank_A:
                                msg="⚠ No solution — inconsistent equations (parallel lines that never meet)."
                            else:
                                msg="⚠ Infinite solutions — equations describe the same line.\nTry adding a different equation."
                        except Exception:
                            msg="⚠ No unique solution (parallel, coincident, or inconsistent)."
                        res.set(msg); show(msg,label="System"); return
                    from sympy import Symbol as Sym
                    if isinstance(sol,list) and any(
                        isinstance(v,Sym)
                        for s in sol
                        for v in (s.values() if isinstance(s,dict) else [s])
                    ):
                        msg="⚠ Infinite solutions — equations describe the same line.\nTry adding a different equation."
                        res.set(msg); show(msg,label="System"); return
                    lines=[]
                    if isinstance(sol,dict):
                        for k,v in sol.items():
                            lines.append(f"{k} = {v}  ≈  {float(v.evalf()):.8g}" if v.is_real else f"{k} = {v}")
                    elif isinstance(sol,list):
                        for i,s in enumerate(sol,1):
                            lines.append(f"Solution {i}: {s}")
                    result="\n".join(lines)
                    res.set(result); show(result,label="System")
                except Exception as ex:
                    msg=f"Error: {ex}"
                    res.set(msg); show(msg,label="System")
            calc_btn(p,"Solve System",solve_sys,app=self).pack(fill="x",pady=(8,2))
            clear_btn(p,[e1,e2,e3],res)

        # ── Tab 3: Polynomial ──
        def panel_poly(p):
            p=full(p)
            tlabel(p,"Find roots of any polynomial in x  e.g.  x**3 - 6*x**2 + 11*x - 6",
                size=9,muted=True).pack(anchor="w",pady=(0,4))
            expr=sf(p,"Polynomial expression")
            res=res_box(p)
            def solve_poly():
                try:
                    if not expr.get().strip():
                        msg="⚠ Please enter a polynomial."
                        res.set(msg); show(msg,label="Polynomial"); return
                    x=symbols('x')
                    poly=pexpr(expr.get())
                    roots=solve(poly,x)
                    factored=factor(poly)
                    lines=[f"Factored form: {factored}","","Roots:"]
                    for i,r in enumerate(roots,1):
                        try: approx=f"  ≈  {float(r.evalf()):.8g}"
                        except: approx=""
                        lines.append(f"x{i} = {r}{approx}")
                    result="\n".join(lines)
                    res.set(result); show(result,label="Polynomial")
                except Exception as ex:
                    msg=f"Error: {ex}"
                    res.set(msg); show(msg,label="Polynomial")
            calc_btn(p,"Find Roots",solve_poly,app=self).pack(fill="x",pady=(8,2))
            clear_btn(p,[expr],res)

        # ── Tab 4: Derivative ──
        def panel_deriv(p):
            p=full(p)
            tlabel(p,"Differentiate any expression  e.g.  x**3 + sin(x)",
                size=9,muted=True).pack(anchor="w",pady=(0,4))
            expr=sf(p,"Expression f(x)")
            order=sf(p,"Order (1=first, 2=second, etc.)","Leave blank for 1st derivative")
            res=res_box(p)
            def solve_deriv():
                try:
                    if not expr.get().strip():
                        msg="⚠ Please enter an expression."
                        res.set(msg); show(msg,label="Derivative"); return
                    x=symbols('x')
                    f=pexpr(expr.get())
                    n=int(order.get().strip()) if order.get().strip() else 1
                    d=diff(f,x,n)
                    simplified=simplify(d)
                    lines=[f"f(x) = {f}", f"f{'ʼ'*n}(x) = {d}"]
                    if simplified!=d:
                        lines.append(f"Simplified: {simplified}")
                    result="\n".join(lines)
                    res.set(result); show(result,label=f"d{n}/dx{n}")
                except Exception as ex:
                    msg=f"Error: {ex}"
                    res.set(msg); show(msg,label="Derivative")
            calc_btn(p,"Differentiate",solve_deriv,app=self).pack(fill="x",pady=(8,2))
            clear_btn(p,[expr,order],res)

        # ── Tab 5: Integral ──
        def panel_integ(p):
            p=full(p)
            tlabel(p,"Integrate any expression  e.g.  x**2 + sin(x)",
                size=9,muted=True).pack(anchor="w",pady=(0,4))
            expr=sf(p,"Expression f(x)")
            lo=sf(p,"Lower bound (leave blank for indefinite)")
            hi=sf(p,"Upper bound (leave blank for indefinite)")
            res=res_box(p)
            def solve_integ():
                try:
                    if not expr.get().strip():
                        msg="⚠ Please enter an expression."
                        res.set(msg); show(msg,label="Integral"); return
                    x=symbols('x')
                    f=pexpr(expr.get())
                    lv=lo.get().strip(); hv=hi.get().strip()
                    if lv and not hv:
                        msg="Error: Upper bound is missing"
                        res.set(msg); show(msg,label="Integral"); return
                    elif hv and not lv:
                        msg="Error: Lower bound is missing"
                        res.set(msg); show(msg,label="Integral"); return
                    elif lv and hv:
                        result=integrate(f,(x,pexpr(lv),pexpr(hv)))
                        lines=[f"∫ {f} dx  from {lv} to {hv}", f"= {result}",
                               f"≈ {float(result.evalf()):.10g}" if result.is_real else ""]
                    else:
                        result=integrate(f,x)
                        lines=[f"∫ {f} dx", f"= {result} + C"]
                    out="\n".join(l for l in lines if l)
                    res.set(out); show(out,label="Integral")
                except Exception as ex:
                    msg=f"Error: {ex}"
                    res.set(msg); show(msg,label="Integral")
            calc_btn(p,"Integrate",solve_integ,app=self).pack(fill="x",pady=(8,2))
            clear_btn(p,[expr,lo,hi],res)

        # ── Tab 6: Simplify / Factor / Expand ──
        def panel_simplify(p):
            p=full(p)
            tlabel(p,"Simplify, factor or expand any expression",
                size=9,muted=True).pack(anchor="w",pady=(0,4))
            expr=sf(p,"Expression  e.g.  (x**2 - 1)/(x - 1)  or  (x+1)**3")
            res=res_box(p)
            def do_simplify():
                try:
                    if not expr.get().strip():
                        msg="⚠ Please enter an expression."
                        res.set(msg); show(msg,label="Simplify"); return
                    from sympy import Symbol, cancel, together, fraction, solve as sym_solve
                    x=Symbol('x')
                    f=pexpr(expr.get())
                    numer,denom=fraction(f)
                    restrictions=[]
                    if denom!=1:
                        excluded=sym_solve(denom,x)
                        if excluded:
                            restrictions=[f"x ≠ {v}" for v in excluded]
                    lines=[
                        f"Original:   {f}",
                        f"Simplified: {simplify(f)}",
                        f"Expanded:   {expand(f)}",
                        f"Factored:   {factor(f)}",
                    ]
                    if restrictions:
                        lines.append(f"Domain:     {', '.join(restrictions)}")
                    result="\n".join(lines)
                    res.set(result); show(result,label="Simplify")
                except Exception as ex:
                    msg=f"Error: {ex}"
                    res.set(msg); show(msg,label="Simplify")
            calc_btn(p,"Simplify / Factor / Expand",do_simplify,app=self).pack(fill="x",pady=(8,2))
            clear_btn(p,[expr],res)

        panels={
            "Equation":panel_eq,
            "System":panel_system,
            "Polynomial":panel_poly,
            "Derivative":panel_deriv,
            "Integral":panel_integ,
            "Simplify/Factor":panel_simplify,
        }

        # build 2-row tab bar (3+3)
        tab_names=list(panels.keys())
        for i,name in enumerate(tab_names):
            row=row1 if i<3 else row2
            col=i if i<3 else i-3
            b=self._tab_btn(row,name,lambda n=name:switch(n))
            b.grid(row=0,column=col,sticky="ew",padx=3,pady=1)
            tab_btns[name]=b

        switch("Equation")

    # ────────────────────────────────────────
    # CONVERTER  (isolated StringVars)
    # ────────────────────────────────────────
    def _render_converter(self, parent):
        card=tk.Frame(parent,bg=T["surface2"],
                      highlightbackground=T["border"],highlightthickness=1)
        card.pack(fill="both",expand=True)

        cat_var=tk.StringVar(value="Length")
        val_var=tk.StringVar()
        from_var=tk.StringVar()
        to_var=tk.StringVar()
        res_var=tk.StringVar(value="")
        note_var=tk.StringVar()

        def refresh(*_):
            cat=CONVERTERS[cat_var.get()]
            units=list(cat.units.keys())
            # Set dropdown height — show all units without scrolling (max 12)
            h=min(len(units),12)
            from_cb.configure(values=units,height=h)
            to_cb.configure(values=units,height=h)
            from_var.set(units[0]); to_var.set(units[1] if len(units)>1 else units[0])
            note_var.set(cat.note)
            # Clear result and top display when switching category
            res_var.set("")
            self.display.set("0")
            self.expression.set("")
            self.preview.set("Ready")

        def do_clear():
            val_var.set("")
            res_var.set("")
            note_var.set(CONVERTERS[cat_var.get()].note)
            self.display.set("0")
            self.expression.set("")
            self.preview.set("Ready")
            val_e.focus_set()

        def convert(*_):
            raw=val_var.get().strip()
            if not raw:
                self.show_result("", label="Converter")
                res_var.set("")
                return
            cat=CONVERTERS[cat_var.get()]
            try:
                if cat.kind=="temperature":
                    v=float(raw)
                    in_celsius = v if from_var.get()=="Celsius" else (v-32)*5/9 if from_var.get()=="Fahrenheit" else v-273.15
                    if in_celsius < -273.15:
                        msg="Error: Temperature below absolute zero (−273.15°C) is not physically possible"
                        res_var.set(msg)
                        self.show_result(msg, label="Temperature")
                        return
                    r=conv_temp(v,from_var.get(),to_var.get())
                    result=f"{r:.8g} {to_var.get()}"
                    res_var.set(result)
                    self.show_result(result, label=f"Converter ({from_var.get()} → {to_var.get()})")
                elif cat.kind=="number":
                    result=f"{conv_num(raw,from_var.get(),to_var.get())}  ({to_var.get()})"
                    res_var.set(result)
                    self.show_result(result, label=f"Converter ({from_var.get()} → {to_var.get()})")
                else:
                    v=float(raw)
                    if v<0 and cat.name not in {"Temperature"}:
                        raise ValueError("Value cannot be negative")
                    if cat.name == "Currency":
                        import time
                        if not LIVE_RATES or (time.time() - LIVE_RATES_TIMESTAMP) > 3600:
                            success = fetch_live_rates()
                            if success:
                                note_var.set(f"✓ Live rates — updated {__import__('datetime').datetime.now().strftime('%H:%M')}")
                            else:
                                note_var.set("⚠ Could not fetch live rates — showing offline demo rates")
                        if LIVE_RATES:
                            fr = LIVE_RATES.get(from_var.get(), None)
                            to = LIVE_RATES.get(to_var.get(), None)
                            if fr and to:
                                r = v / fr * to
                                result=f"{r:.6g} {to_var.get()}"
                                res_var.set(result)
                                self.show_result(result, label=f"Converter ({from_var.get()} → {to_var.get()})")
                            else:
                                raise ValueError("Currency not found in live rates")
                        else:
                            b = v * cat.units[from_var.get()]
                            result=f"{b/cat.units[to_var.get()]:.8g} {to_var.get()} (offline)"
                            res_var.set(result)
                            self.show_result(result, label=f"Converter ({from_var.get()} → {to_var.get()})")
                    else:
                        b=v*cat.units[from_var.get()]
                        result=f"{b/cat.units[to_var.get()]:.8g} {to_var.get()}"
                        res_var.set(result)
                        self.show_result(result, label=f"Converter ({from_var.get()} → {to_var.get()})")
            except ValueError as ex:
                msg=f"Error: {ex}"
                res_var.set(msg)
                self.show_result(msg, label="Converter")
            except Exception as ex:
                msg=f"Error: {ex}"
                res_var.set(msg)
                self.show_result(msg, label="Converter")

        def slbl(text):
            tk.Label(card,text=text,bg=T["surface2"],fg=T["muted"],
                     font=(APP_FONT,10,"bold")).pack(anchor="w",padx=14,pady=(10,2))

        slbl("Category")
        cat_cb=ttk.Combobox(card,textvariable=cat_var,values=list(CONVERTERS.keys()),
                            state="readonly",font=(APP_FONT,11),style="C.TCombobox",
                            height=len(CONVERTERS))
        cat_cb.pack(fill="x",padx=14)

        slbl("Value to convert")
        val_e=tk.Entry(card,textvariable=val_var,bg=T["surface"],fg=T["text"],
                       insertbackground=T["text"],relief="flat",font=(APP_FONT,15),
                       highlightthickness=1,highlightcolor=T["green"],
                       highlightbackground=T["border"])
        val_e.pack(fill="x",padx=14,ipady=8)
        val_e.bind("<Button-1>", lambda _: val_e.focus_set())
        val_e.focus_set()

        ur=tk.Frame(card,bg=T["surface2"]); ur.pack(fill="x",padx=14,pady=8)
        ur.columnconfigure(0,weight=1); ur.columnconfigure(1,weight=1)
        tk.Label(ur,text="From",bg=T["surface2"],fg=T["muted"],
                 font=(APP_FONT,10,"bold")).grid(row=0,column=0,sticky="w")
        tk.Label(ur,text="To",  bg=T["surface2"],fg=T["muted"],
                 font=(APP_FONT,10,"bold")).grid(row=0,column=1,sticky="w",padx=(8,0))
        from_cb=ttk.Combobox(ur,textvariable=from_var,state="readonly",
                             font=(APP_FONT,11),style="C.TCombobox")
        to_cb  =ttk.Combobox(ur,textvariable=to_var,  state="readonly",
                             font=(APP_FONT,11),style="C.TCombobox")
        from_cb.grid(row=1,column=0,sticky="ew",pady=(3,0))
        to_cb  .grid(row=1,column=1,sticky="ew",padx=(8,0),pady=(3,0))

        res_lbl=tk.Label(card,textvariable=res_var,bg=T["surface"],fg=T["text"],
                 font=(APP_FONT,15,"bold"),padx=14,pady=12,
                 anchor="w",justify="left",wraplength=400)
        def _toggle_res_lbl(*_):
            if res_var.get(): res_lbl.pack(fill="x",padx=14,pady=(10,2))
            else: res_lbl.pack_forget()
        res_var.trace_add("write", _toggle_res_lbl)
        _toggle_res_lbl()
        tk.Label(card,textvariable=note_var,bg=T["surface2"],fg=T["danger"],
                 font=(APP_FONT,9),padx=14).pack(anchor="w")

        # Buttons row: Convert Now | ⇄ Swap  then Clear full width below
        br=tk.Frame(card,bg=T["surface2"]); br.pack(fill="x",padx=14,pady=(6,4))
        br.columnconfigure(0,weight=2); br.columnconfigure(1,weight=1)
        ProButton(br,"Convert Now",command=convert,bg_color="green",hover_color="green_hover",
                  fg_color="text",font_size=12,min_height=40,radius=20
                  ).grid(row=0,column=0,sticky="ew",padx=(0,6))
        def swap():
            a=from_var.get(); from_var.set(to_var.get()); to_var.set(a); convert()
        ProButton(br,"⇄ Swap",command=swap,bg_color="grey",hover_color="grey_hover",
                  fg_color="text",font_size=12,min_height=40,radius=20
                  ).grid(row=0,column=1,sticky="ew")
        ProButton(card,"Clear",command=do_clear,bg_color="danger",hover_color="danger_hover",
                  fg_color="text",font_size=12,min_height=40,radius=20
                  ).pack(fill="x",padx=14,pady=(4,14))

        cat_cb.bind("<<ComboboxSelected>>",refresh)
        from_cb.bind("<<ComboboxSelected>>",convert)
        to_cb.bind("<<ComboboxSelected>>",convert)
        val_e.bind("<KeyRelease>",convert)
        refresh()

    # ────────────────────────────────────────
    # Core calculator actions  (Basic & Scientific only)
    # ────────────────────────────────────────
    def handle(self, value):
        if value=="AC":   self.clear(); return
        if value=="⌫":   self.backspace(); return
        if value=="=":    self.calculate(); return
        if value=="±":   self.toggle_sign(); return
        if value in {"×","÷","−","+","%","."}: self.ins(value); return
        if value.isdigit(): self.ins(value); return

    def ins(self, token):
        curr = self.expression.get()
        if curr == "Error": curr = ""
        if curr.endswith(" ="):
            result = self.display.get()
            if token.endswith("("):
                curr = token + result + ")"
                self.expression.set(curr)
                self.display.set(curr)
                self._preview()
                return
            curr = result

        # ── Decimal guard ──
        if token == ".":
            # find the last number segment (split on operators)
            parts = re.split(r'[+\-×÷*/()^%]', curr)
            last = parts[-1] if parts else ""
            if "." in last:
                return  # already has a decimal, ignore

        new = curr + token
        self.expression.set(new)
        self.display.set(new if new else "0")
        self._preview()

    def wrap(self, tmpl):
        curr=self.expression.get()
        if not curr or curr=="Error": return
        e=tmpl.format(x=curr)
        self.expression.set(e); self.display.set(e); self._preview()

    def clear(self):
        self.expression.set(""); self.display.set("0"); self.preview.set("Ready")

    def backspace(self):
        curr=self.expression.get()[:-1]
        self.expression.set(curr); self.display.set(curr if curr else "0"); self._preview()

    def toggle_sign(self):
        curr=self.expression.get()
        if not curr: return
        e=curr[2:-1] if (curr.startswith("-(") and curr.endswith(")")) else f"-({curr})"
        self.expression.set(e); self.display.set(e); self._preview()

    def calculate(self):
         expr=self.expression.get()
         if not expr: return
         res=Engine.evaluate(expr, self.angle_mode)
         if "Error" not in res:
             self.history.insert(0,f"{expr} = {res}")
             self.history=self.history[:50]
         self.display.set(res)
         self.expression.set(f"{expr} =")
         self.preview.set("Calculated ✓")

    def _preview(self):
        expr=self.expression.get()
        if not expr or expr=="Error": return
        r=Engine.evaluate(expr, self.angle_mode)
        if "Error" not in r: self.preview.set(f"= {r}")
    
    def show_result(self, result: str, label: str = ""):
        self.expression.set(label)
        self.display.set(result)
        self.preview.set("Calculated ✓")
        if "Error" not in result:
            entry = f"[{label}]  {result}" if label else result
            entry_flat = entry.replace("\n", "  |  ")
            self.history.insert(0, entry_flat)
            self.history = self.history[:50]

    def mem(self, action):
        try:
            if action=="mc":
                # Clear memory — no need to evaluate expression
                self.memory=0.0
                self.lbl_mem.configure(text="")
                self.preview.set("Memory cleared")

            elif action in ("m+","m−"):
                # Evaluate current expression to get value to store
                curr_val=float(Engine.evaluate(self.expression.get(), self.angle_mode))
                if action=="m+": self.memory+=curr_val
                else:            self.memory-=curr_val
                self.lbl_mem.configure(text=f"M:{self.memory:.4g}")
                self.preview.set(f"Memory: {self.memory:.4g}")

            elif action=="mr":
                # Recall — replace display cleanly instead of appending
                val=f"{self.memory:.12g}"
                self.expression.set(val)
                self.display.set(val)
                self.preview.set(f"Recalled: {val}")
                self._preview()

        except:
            self.preview.set("Memory Error")

    def toggle_angle(self):
        self.angle_mode="DEG" if self.angle_mode=="RAD" else "RAD"
        self.rad_btn.set_text(self.angle_mode)
        self.lbl_angle.configure(text=f"  {self.angle_mode}")
        self.preview.set(f"Angle mode: {self.angle_mode}")

    def copy_result(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.display.get())
        self.preview.set("Copied ✓")

    # ────────────────────────────────────────
    # History popup
    # ────────────────────────────────────────
    def open_history(self):
        popup=tk.Toplevel(self.root)
        popup.title("Calculation History")
        popup.geometry("420x520")
        popup.configure(bg=T["bg"])
        popup.transient(self.root)
        popup.resizable(False,False)

        hdr=tk.Frame(popup,bg=T["bg"]); hdr.pack(fill="x",padx=18,pady=(16,8))
        tk.Label(hdr,text="◷  History",bg=T["bg"],fg=T["text"],
             font=(APP_FONT,17,"bold")).pack(side="left")
        ProButton(hdr,"Clear All",command=lambda:[self.history.clear(),popup.destroy()],
             bg_color="danger",hover_color="danger_hover",fg_color="text",
             font_size=10,min_height=30,radius=15,width=80).pack(side="right")
        ProButton(hdr,"Export CSV",command=lambda:self._export_history_csv(popup),
             bg_color="green",hover_color="green_hover",fg_color="text",
             font_size=10,min_height=30,radius=15,width=90).pack(side="right",padx=(0,6))

        if not self.history:
            tk.Label(popup,text="No calculations yet.",bg=T["bg"],
                     fg=T["muted"],font=(APP_FONT,12)).pack(pady=40)
            popup.update_idletasks()
            return

        cnv=tk.Canvas(popup,bg=T["bg"],highlightthickness=0)
        sb=ttk.Scrollbar(popup,orient="vertical",command=cnv.yview)
        sf=tk.Frame(cnv,bg=T["bg"])
        sf.bind("<Configure>",lambda _:cnv.configure(scrollregion=cnv.bbox("all")))
        cnv.create_window((0,0),window=sf,anchor="nw")
        cnv.configure(yscrollcommand=sb.set)
        cnv.pack(side="left",fill="both",expand=True,padx=(18,0),pady=(0,18))
        sb.pack(side="right",fill="y",pady=(0,18))
        def scroll_hist(ev):
            cnv.yview_scroll(-1 if ev.delta > 0 else 1, "units")

        def bind_hist(widget):
            widget.bind("<MouseWheel>", scroll_hist)
            for child in widget.winfo_children():
                bind_hist(child)

        cnv.bind("<MouseWheel>", scroll_hist)
        sf.bind("<Configure>", lambda e: bind_hist(sf))

        for item in self.history:
            row=tk.Label(sf,text=item,bg=T["surface2"],fg=T["text"],
                         font=(APP_FONT,10),padx=10,pady=7,
                         anchor="w",wraplength=360,justify="left",cursor="hand2")
            row.pack(fill="x",pady=2)
            row.bind("<Button-1>",lambda _,v=item:self._use_history(v,popup))
            row.bind("<Enter>",   lambda _,r=row:r.configure(bg=T["sci_hover"]))
            row.bind("<Leave>",   lambda _,r=row:r.configure(bg=T["surface2"]))

    def _use_history(self, item, popup):
        popup.destroy()
        if " = " in item:
            result=item.split(" = ",1)[1]
            self.expression.set(result)
            self.display.set(result)
            self.preview.set("From history")

    def _export_history_csv(self, popup=None):
         import csv, tkinter.filedialog as fd, tkinter.messagebox as mb
         if not self.history:
             mb.showinfo("Export", "No history to export.", parent=popup or self.root)
             return
         path = fd.asksaveasfilename(
             defaultextension=".csv",
             filetypes=[("CSV files","*.csv"),("All files","*.*")],
             title="Save History as CSV",
             initialfile="calc_history.csv"
        )
         if not path:
             return
         try:
             with open(path, "w", newline="", encoding="utf-8") as f:
                 w = csv.writer(f)
                 w.writerow(["#", "Calculation"])
                 for i, item in enumerate(self.history, 1):
                      w.writerow([i, item])
             mb.showinfo("Export", f"History saved to:\n{path}", parent=popup or self.root)
         except Exception as ex:
             mb.showerror("Export Failed", str(ex), parent=popup or self.root)

    # ────────────────────────────────────────
    # Theme toggle
    # ────────────────────────────────────────
    def toggle_theme(self):
        global T
        self.is_dark = not self.is_dark
        T = DARK if self.is_dark else LIGHT
        self.theme_btn.set_text("☀" if self.is_dark else "🌙")
        self._apply_combo_style()
        self._refresh_theme()
        self.switch_mode(self.current_mode)

    def _refresh_theme(self):
        self.root.configure(bg=T["bg"])
        self.sidebar.configure(bg=T["sidebar"])
        self.main_frame.configure(bg=T["bg"])
        self.content.configure(bg=T["bg"])

        # Labels
        for lbl in self._labels:
            try: lbl.configure(bg=T["bg"])
            except: pass
        for f in self._frames:
            try: f.configure(bg=T["bg"])
            except: pass

        # Specific labels
        self.lbl_expr.configure(fg=T["muted"])
        self.lbl_disp.configure(fg=T["text"])
        self.lbl_angle.configure(fg=T["green"])
        self.lbl_mem.configure(fg=T["success"])
        self.lbl_prev.configure(fg=T["muted"])
        self.lbl_mode_name.configure(fg=T["text"],bg=T["bg"])

        # Sidebar brand & nav
        self._sb_brand.configure(bg=T["sidebar"],fg=T["green"])
        self._sb_nav.configure(bg=T["sidebar"])
        self._sb_bot.configure(bg=T["sidebar"])
        for f in self._sb_nav.winfo_children():
            try: f.configure(bg=T["sidebar"])
            except: pass
            for child in f.winfo_children():
                try: child.configure(bg=T["sidebar"], fg=T["text"])
                except: pass
        self._highlight_sidebar(self.current_mode)

        # Sidebar bottom buttons
        for btn in [self.theme_btn, self.hist_btn]:
            btn.set_colors("surface2","sci_hover","text")
            btn.configure(bg=T["sidebar"])
        self.rad_btn.set_colors("surface2","sci_hover","green")
        self.rad_btn.configure(bg=T["bg"])
        self.copy_btn.set_colors("surface2","sci_hover","text")
        self.copy_btn.configure(bg=T["bg"])

    # ────────────────────────────────────────
    # Keyboard
    # ────────────────────────────────────────
    def _auto_resize_display(self, *_):
        text = self.display.get()
        lines = text.split("\n")
        longest = max(len(l) for l in lines)
        line_count = len(lines)

        if line_count > 2 or longest > 30:
            size = 13
        elif longest > 20:
            size = 18
        elif longest > 14:
            size = 26
        elif longest > 10:
            size = 34
        else:
            size = 42

        self.lbl_disp.configure(font=(APP_FONT, size, "bold"))

    def _bind_keys(self) -> None:
        self.root.bind("<Return>",    lambda _: self._smart_enter())
        self.root.bind("<Escape>",    lambda _: self.clear())
        self.root.bind("<BackSpace>", lambda _: self._key_backspace())
        self.root.bind("<Key>",       self._on_key)

    def _smart_enter(self):
        if self.current_mode in ("Basic", "Scientific"):
            self.calculate()
        elif self.current_calc_fn is not None:
            self.current_calc_fn()

    def _focused_is_entry(self) -> bool:
        focused = self.root.focus_get()
        return isinstance(focused, (tk.Entry, ttk.Entry, ttk.Combobox))

    def _key_backspace(self) -> None:
        if not self._focused_is_entry():
            self.backspace()

    def _on_key(self, event: tk.Event) -> None:
        if self._focused_is_entry():
            return
        c = event.char
        if not c:
            return
        remap = {"*": "×", "/": "÷", "-": "−"}
        if c in "0123456789.+-*/()%^":
            self.ins(remap.get(c, c))


# ─────────────────────────────────────────────
def main():
    root=tk.Tk()
    UltraCalc(root)
    root.mainloop()

if __name__=="__main__":
    main()
