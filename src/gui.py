import tkinter as tk
from tkinter import ttk
import csv
from pathlib import Path

BG = "#ece3d2"
FG = "#1c1c1c"
MUTED = "#6b6559"
LINE = "#2b2b2b"
FONT = "Courier New"


def font(size=10, weight="normal"):
    return (FONT, size, weight)


class Panel(tk.Frame):
    def __init__(self, master, title):
        super().__init__(master, bg=BG, highlightbackground=LINE,
                         highlightcolor=LINE, highlightthickness=2)
        tk.Label(self, text=title, bg=BG, fg=FG, font=font(11, "bold"),
                 anchor="w").pack(fill="x", padx=10, pady=(10, 4))
class PlaceholderChart(tk.Canvas):
    """Big X on a chart as a placeholder"""

    def __init__(self, master, caption):
        super().__init__(master, bg=BG, highlightthickness=0)
        self.caption = caption
        self.bind("<Configure>", self.redraw)

    def redraw(self, _event=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        m = 4
        self.create_line(m, m, w - m, h - m, fill=LINE, width=1)
        self.create_line(w - m, m, m, h - m, fill=LINE, width=1)
        self.create_text(w / 2, h / 2, text=self.caption, fill=MUTED,
                         font=font(9), tags="cap")
        # background patch so the caption stays readable over the X
        bbox = self.bbox("cap")
        if bbox:
            pad = 6
            r = self.create_rectangle(bbox[0] - pad, bbox[1] - 2,
                                      bbox[2] + pad, bbox[3] + 2,
                                      fill=BG, outline=BG)
            self.tag_lower(r, "cap")


class StadiumCanvas(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, bg=BG, highlightthickness=0, height=130)
        self.lf = self.cf = self.rf = "--"
        self.bind("<Configure>", self.redraw)

    def set_dims(self, lf="--", cf="--", rf="--"):
        self.lf, self.cf, self.rf = lf, cf, rf
        self.redraw()

    def redraw(self, _event=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        cx = w / 2
        home_y = h - 8
        r = min(w * 0.38, h - 40)
        left = (cx - r * 0.95, home_y - r * 0.62)
        right = (cx + r * 0.95, home_y - r * 0.62)
        top_y = home_y - r

        # foul lines
        self.create_line(cx, home_y, *left, fill=LINE, width=1)
        self.create_line(cx, home_y, *right, fill=LINE, width=1)
        # outfield wall (arc)
        self.create_arc(cx - r * 1.15, home_y - r * 1.5, cx + r * 1.15,
                        home_y + r * 0.8, start=38, extent=104,
                        style="arc", outline=LINE, width=1)
        # infield diamond
        d = r * 0.38
        self.create_polygon(cx, home_y, cx - d, home_y - d, cx,
                            home_y - 2 * d, cx + d, home_y - d,
                            outline=LINE, fill="", width=1)
        # labels
        self.create_text(left[0] - 4, left[1] - 14, text=f"LF: {self.lf} ft",
                         font=font(8), fill=FG, anchor="e")
        self.create_text(right[0] + 4, right[1] - 14, text=f"RF: {self.rf} ft",
                         font=font(8), fill=FG, anchor="w")
        self.create_text(cx, max(top_y - 12, 8), text=f"CF: {self.cf} ft",
                         font=font(8), fill=FG)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LaBronx Bombers - Yankees Matchup Analyzer")
        self.configure(bg=BG)
        self.geometry("1000x680")
        self.minsize(900, 620)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=BG, background=BG,
                        foreground=MUTED, bordercolor="#b8ae9a",
                        lightcolor=BG, darkcolor=BG, arrowcolor=FG,
                        padding=3)
        style.map("TCombobox", fieldbackground=[("readonly", BG)],
                  foreground=[("readonly", MUTED)])
        self.option_add("*TCombobox*Listbox.background", BG)
        self.option_add("*TCombobox*Listbox.foreground", FG)

        self.stadium_dimensions = self._load_stadium_dimensions()
        self._build_topbar()
        self._build_header()
        self._build_body()

    def _load_stadium_dimensions(self):
        dimensions_file = Path(__file__).resolve().parents[1] / "data" / "Stadium_dimensions.csv"
        dimensions = {}
        with dimensions_file.open(newline="", encoding="utf-8") as stream:
            for row in csv.DictReader(stream):
                dimensions[row["Ballpark"]] = {
                    "left": row["Left"].removesuffix(" ft"),
                    "center": row["Center"].removesuffix(" ft"),
                    "right": row["Right"].removesuffix(" ft"),
                }
        return dimensions

    # ---------------------------------------------------------- top bar
    def _build_topbar(self):
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x")
        tk.Label(bar, text="LaBronx", bg=BG, fg=FG, font=font(9, "bold")
                 ).pack(side="left", padx=12, pady=6)
        tk.Label(bar, text="Anthony Kanige / Steven Baez-Fabre / Evan Schwartz",
                 bg=BG, fg=MUTED, font=font(9)).pack(side="right", padx=12)
        tk.Frame(self, bg=LINE, height=1).pack(fill="x")

    def _build_header(self):
        head = tk.Frame(self, bg=BG)
        head.pack(fill="x", padx=14, pady=(14, 0))
        head.columnconfigure(1, weight=1)

        box = tk.Label(head, text="+", bg=BG, fg=FG, font=font(16),
                       highlightbackground=LINE, highlightthickness=2,
                       width=2)
        box.grid(row=0, column=0, sticky="w")
        tk.Label(head, text="Yankees Matchup Analyzer", bg=BG, fg=FG,
                 font=font(13, "bold")).grid(row=0, column=1)
        tk.Label(head, text="2021-2025 regular seasons", bg=BG, fg=MUTED,
                 font=font(9)).grid(row=0, column=2, sticky="e")

    # ------------------------------------------------------------- body
    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=34, pady=(26, 24))
        body.columnconfigure(0, weight=1, uniform="c")
        body.columnconfigure(1, weight=1, uniform="c")
        body.columnconfigure(2, weight=0, minsize=270)
        body.rowconfigure(0, weight=3, uniform="r")
        body.rowconfigure(1, weight=2, uniform="r")

        # chart panels
        p = Panel(body, "Performance by Stadium")
        p.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        PlaceholderChart(p, "Player or team comparison").pack(
            fill="both", expand=True, padx=8, pady=(0, 8))

        p = Panel(body, "Performance by Inning")
        p.grid(row=0, column=1, sticky="nsew", padx=(8, 8), pady=(0, 8))
        PlaceholderChart(p, "Player or team comparison").pack(
            fill="both", expand=True, padx=8, pady=(0, 8))

        self._build_ds_panel(body)
        self._build_stadium_panel(body)
        self._build_controls(body)

    def _build_ds_panel(self, body):
        p = Panel(body, "Data-Structure Results")
        p.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(8, 0))

        table = tk.Frame(p, bg=BG)
        table.pack(fill="x", padx=10)
        table.columnconfigure(0, weight=1)
        for c, t in enumerate(["Metric", "Hash table", "Red-black\ntree"]):
            tk.Label(table, text=t, bg=BG, fg=FG, font=font(8, "bold"),
                     anchor="w" if c == 0 else "center", justify="center"
                     ).grid(row=0, column=c, sticky="ew", padx=4)
        tk.Frame(table, bg="#b8ae9a", height=1).grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=4)

        self.ds_vals = {}
        for i, m in enumerate(["Construction time", "Lookup time",
                               "Memory usage"]):
            r = 2 + i
            tk.Label(table, text=m, bg=BG, fg=FG, font=font(8), anchor="w"
                     ).grid(row=r, column=0, sticky="w", padx=4, pady=5)
            for c in (1, 2):
                lbl = tk.Label(table, text="--", bg=BG, fg=MUTED,
                               font=font(8), width=9)
                lbl.grid(row=r, column=c)
                self.ds_vals[(m, c)] = lbl

        tk.Label(p, text="Same summaries; 100,000+ records", bg=BG, fg=MUTED,
                 font=font(7), anchor="w").pack(side="bottom", fill="x",
                                                padx=10, pady=8)
        tk.Frame(p, bg="#b8ae9a", height=1).pack(side="bottom", fill="x",
                                                 padx=10)

    def _build_stadium_panel(self, body):
        p = Panel(body, "Stadium Window")
        p.grid(row=1, column=1, sticky="nsew", padx=(8, 8), pady=(8, 0))

        self.stadium_lbl = tk.Label(
            p, text="[Selected stadium]   Year: [year]", bg=BG, fg=MUTED,
            font=font(8), anchor="w")
        self.stadium_lbl.pack(fill="x", padx=10)

        self.stadium = StadiumCanvas(p)

        self.wall_lbl = tk.Label(
            p, text="Wall heights: LF -- / CF -- / RF -- ft", bg=BG, fg=MUTED,
            font=font(8))
        tk.Label(p, text="Dimensions for the selected year", bg=BG, fg=MUTED,
                 font=font(8)).pack(side="bottom", pady=(0, 8))
        self.wall_lbl.pack(side="bottom")
        self.stadium.pack(fill="both", expand=True, padx=8)

    def _build_controls(self, body):
        side = tk.Frame(body, bg=BG)
        side.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=(30, 0))

        tk.Label(side, text="Bronx Breakdown", bg=BG, fg=FG,
                 font=font(16, "bold"), anchor="w").pack(fill="x")
        tk.Label(side, text="Explore Yankees matchup scenarios", bg=BG,
                 fg=FG, font=font(9), anchor="w").pack(fill="x", pady=(6, 14))

        grid = tk.Frame(side, bg=BG)
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1, uniform="g")
        grid.columnconfigure(1, weight=1, uniform="g")

        specs = [
            ("Player", ["All Yankees"], 0, 0, "player"),
            ("Stadium", ["All stadiums"] + list(self.stadium_dimensions), 0, 1,
             "stadium"),
            ("Season", ["2026", "2025", "2024", "2023", "2022", "2021","2020"],
             2, 0, "season"),
            ("Inning", ["All innings"] + [str(i) for i in range(1, 10)],
             2, 1, "inning"),
            ("Pitcher handedness", ["All", "Left", "Right"], 4, 0, "pitcher"),
            ("Batter handedness", ["All", "Left", "Right", "Switch"], 4, 1,
             "batter"),
        ]
        self.vars = {}
        for label, values, row, col, key in specs:
            tk.Label(grid, text=label, bg=BG, fg=FG, font=font(9, "bold"),
                     anchor="w").grid(row=row, column=col, sticky="w",
                                      padx=(0 if col == 0 else 6, 6),
                                      pady=(8, 2))
            var = tk.StringVar(value=values[0])
            cb = ttk.Combobox(grid, textvariable=var, values=values,
                              state="readonly", font=font(9), width=11)
            cb.grid(row=row + 1, column=col, sticky="ew",
                    padx=(0 if col == 0 else 6, 6))
            self.vars[key] = var
            if key in ("stadium", "season"):
                cb.bind("<<ComboboxSelected>>",
                        lambda event: self.on_view_stadium())

        # buttons
        btns = tk.Frame(side, bg=BG)
        btns.pack(fill="x", pady=(22, 20))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)

        analyze = tk.Label(btns, text="Analyze", bg=FG, fg="white",
                           font=font(10, "bold"), pady=11, cursor="hand2")
        analyze.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        analyze.bind("<Button-1>", lambda e: self.on_analyze())

        view = tk.Label(btns, text="View Stadium", bg=BG, fg=FG,
                        font=font(9, "bold"), pady=10, cursor="hand2",
                        highlightbackground=LINE, highlightthickness=2)
        view.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        view.bind("<Button-1>", lambda e: self.on_view_stadium())

        # statistics
        tk.Label(side, text="Statistics", bg=BG, fg=FG,
                 font=font(11, "bold"), anchor="w").pack(fill="x")
        stats = tk.Frame(side, bg=BG)
        stats.pack(fill="x", pady=(6, 0))
        stats.columnconfigure(0, weight=1)
        self.stat_vals = {}
        rows = ["Home-run rate", "Matching sample size",
                "Average runs per inning",
                "Team innings with at least\none home run (%)"]
        for i, name in enumerate(rows):
            tk.Frame(stats, bg="#b8ae9a", height=1).grid(
                row=i * 2, column=0, columnspan=2, sticky="ew")
            tk.Label(stats, text=name, bg=BG, fg=FG, font=font(9),
                     anchor="w", justify="left").grid(
                row=i * 2 + 1, column=0, sticky="w", pady=6)
            v = tk.Label(stats, text="--", bg=BG, fg=MUTED, font=font(9))
            v.grid(row=i * 2 + 1, column=1, sticky="e")
            self.stat_vals[name] = v
        tk.Frame(stats, bg="#b8ae9a", height=1).grid(
            row=len(rows) * 2, column=0, columnspan=2, sticky="ew")

        tk.Label(side, text="Results reflect the selected filters.", bg=BG,
                 fg=MUTED, font=font(8), anchor="w").pack(fill="x", pady=10)

    # --------------------------------------------------------- handlers
    def on_analyze(self):
        """Hook: run the analysis using self.vars and fill in the results."""
        filters = {k: v.get() for k, v in self.vars.items()}
        print("Analyze:", filters)

    def on_view_stadium(self):
        """Hook: update the Stadium Window for the selected stadium/year."""
        stadium = self.vars["stadium"].get()
        season = self.vars["season"].get()
        self.stadium_lbl.config(
            text=f"[{stadium}]   Year: [{season}]")
        selected_dimensions = self.stadium_dimensions.get(stadium)
        if selected_dimensions is None:
            self.stadium.set_dims()
            #placeholder text if no stadium is selected
            self.wall_lbl.config(text="Wall heights: LF -- / CF -- / RF -- ft")
            return

        left = selected_dimensions["left"]
        center = selected_dimensions["center"]
        right = selected_dimensions["right"]
        self.stadium.set_dims(left, center, right)
        self.wall_lbl.config(
            text=f"Wall heights: LF {left} / CF {center} / RF {right} ft")


if __name__ == "__main__":
    App().mainloop()
