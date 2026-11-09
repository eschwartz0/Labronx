import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import argparse
import queue
import threading
import webbrowser

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from analyzer import Analyzer, Dataset, DEFAULT_DATA
from models import Filters
from charts import make_figure, empty_chart, stadium_chart, inning_chart
from stadium_metadata import StadiumMetadata, fence_points

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
class PerformanceChart(tk.Frame):
    def __init__(self, master, caption):
        super().__init__(master, bg=BG)
        tk.Label(self, text=caption, bg=BG, fg=MUTED, font=font(7),
                 wraplength=270, justify='left').pack(fill='x', padx=5)
        self.figure = make_figure()
        empty_chart(self.figure, 'Loading historical data…')
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        canvas_widget = self.canvas.get_tk_widget()
        # The grid allocates chart space; a fixed Figure size must not squeeze
        # the lower information panels on smaller or scaled Windows displays.
        canvas_widget.configure(width=1, height=1)
        canvas_widget.pack(fill='both', expand=True)

    def refresh(self):
        self.canvas.draw_idle()


class StadiumCanvas(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, bg=BG, highlightthickness=0, width=1, height=130)
        self.lf = self.cf = self.rf = "--"
        self.left_gap = self.right_gap = None
        self.bind("<Configure>", self.redraw)

    def set_dims(self, lf="--", cf="--", rf="--", left_gap=None, right_gap=None):
        self.lf, self.cf, self.rf = lf, cf, rf
        self.left_gap, self.right_gap = left_gap, right_gap
        self.redraw()

    def redraw(self, _event=None):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        cx = w / 2
        home_y = h - 10
        known = self.lf != '--' and self.cf != '--' and self.rf != '--'
        profile = fence_points(self.lf if known else 330, self.cf if known else 400,
                               self.rf if known else 330,
                               self.left_gap if known else None, self.right_gap if known else None)
        # A shared feet-to-pixels scale makes changes in distances visible. The five
        # rays are an illustrative profile, not the source's surveyed fence geometry.
        scale = max(.01, min((w - 40) / 650, (h - 40) / 460))
        points = [(cx + x * scale, home_y - y * scale) for x, y in profile]
        wall = [coordinate for point in points for coordinate in point]
        self.create_polygon(cx, home_y, *wall, fill='#e1ddca', outline=LINE, width=1)
        self.create_line(*wall, fill=LINE, width=2, tags='fence')
        d = 90 * scale / 2 ** .5
        self.create_polygon(cx, home_y, cx - d, home_y - d, cx,
                            home_y - 2 * d, cx + d, home_y - d,
                            outline=LINE, fill="", width=1)
        # Fixed label columns remain separate when the field profile is small.
        self.create_text(8, 6, text=f"LF {self.lf} ft", anchor='nw',
                         font=font(7), fill=FG, tags='distance_label')
        self.create_text(cx, 6, text=f"CF {self.cf} ft", anchor='n',
                         font=font(7), fill=FG, tags='distance_label')
        self.create_text(w - 8, 6, text=f"RF {self.rf} ft", anchor='ne',
                         font=font(7), fill=FG, tags='distance_label')


class App(tk.Tk):
    def __init__(self, data_dir=DEFAULT_DATA):
        super().__init__()
        self.title("LaBronx Bombers - Yankees Matchup Analyzer")
        self.configure(bg=BG)
        self.geometry("1000x680")
        self.minsize(900, 620)
        self.analyzer = None
        self._refresh_after_id = None
        self.data_dir = Path(data_dir)
        self._load_queue = queue.Queue()

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
        # Reserve the footer before allocating the expanding body.
        footer = tk.Frame(self, bg=BG)
        footer.pack(side='bottom', fill='x', padx=14, pady=(0, 8))
        self.status = tk.StringVar(value='Loading CSVs and comparing both data structures…')
        status_label = tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED,
                               font=font(8), anchor='w', justify='left', wraplength=950)
        status_label.pack(fill='x', pady=(0, 5))
        notice = tk.Label(
            footer,
            text="Historical results, not predictions. Stadium distances and park factors include source years.",
            bg=BG, fg=MUTED, font=font(8), anchor='w', justify='left', wraplength=950)
        notice.pack(fill='x')
        footer.bind('<Configure>', lambda event: (
            status_label.configure(wraplength=max(1, event.width)),
            notice.configure(wraplength=max(1, event.width))))
        self._build_body()
        threading.Thread(target=self._load_backend, daemon=True).start()
        self.after(100, self._poll_backend)

    def _load_stadium_dimensions(self):
        return StadiumMetadata()

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
        head.columnconfigure(0, weight=1)
        tk.Label(head, text="Yankees Matchup Analyzer", bg=BG, fg=FG,
                 font=font(13, "bold")).grid(row=0, column=0, sticky='w')
        tk.Label(head, text="2021-2025 regular seasons", bg=BG, fg=MUTED,
                 font=font(9)).grid(row=0, column=1, sticky="e")

    # ------------------------------------------------------------- body
    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=(18, 14))
        body.columnconfigure(0, weight=1, uniform="c")
        body.columnconfigure(1, weight=1, uniform="c")
        body.columnconfigure(2, weight=0, minsize=270)
        body.rowconfigure(0, weight=1, minsize=180)
        # Keep the lower panels at their requested content height. The charts
        # take the remaining space instead of forcing a fixed 3:2 row ratio.
        body.rowconfigure(1, weight=0)

        # chart panels
        p = Panel(body, "Performance by Stadium")
        p.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        self.stadium_chart = PerformanceChart(p, "Selected filters · top 7 matching venues by PA")
        self.stadium_chart.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        p = Panel(body, "Performance by Inning")
        p.grid(row=0, column=1, sticky="nsew", padx=(8, 8), pady=(0, 8))
        self.inning_chart = PerformanceChart(p, "Selected filters · matching innings and PA counts")
        self.inning_chart.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        self._build_ds_panel(body)
        self._build_stadium_panel(body)
        self._build_controls(body)

    def _build_ds_panel(self, body):
        p = Panel(body, "Data-Structure Results")
        self.results_panel = p
        p.grid(row=1, column=0, sticky="nsew", padx=(0, 8), pady=(8, 0))

        table = tk.Frame(p, bg=BG)
        table.pack(fill="x", padx=10)
        for column in range(3):
            table.columnconfigure(column, weight=1)
        for c, t in enumerate(["Metric", "Hash table", "Red-black\ntree"]):
            tk.Label(table, text=t, bg=BG, fg=FG, font=font(8, "bold"),
                     anchor="w" if c == 0 else "center", justify="center"
                     ).grid(row=0, column=c, sticky="ew", padx=4)
        tk.Frame(table, bg="#b8ae9a", height=1).grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=4)

        self.ds_vals = {}
        for i, (m, caption) in enumerate([("Construction time", "Build time"),
                                           ("Lookup time", "Lookup time"),
                                           ("Memory usage", "Memory")]):
            r = 2 + i
            tk.Label(table, text=caption, bg=BG, fg=FG, font=font(8), anchor="w"
                     ).grid(row=r, column=0, sticky="w", padx=4, pady=5)
            for c in (1, 2):
                lbl = tk.Label(table, text="--", bg=BG, fg=MUTED,
                               font=font(8))
                lbl.grid(row=r, column=c, sticky='ew', padx=4)
                self.ds_vals[(m, c)] = lbl

        tk.Frame(p, bg="#b8ae9a", height=1).pack(fill='x', padx=10, pady=(8, 0))
        self.record_label = tk.Label(p, text="Loading record counts…", bg=BG, fg=MUTED,
                                    font=font(8), anchor='nw', justify='left', wraplength=270)
        self.record_label.pack(fill='x', padx=10, pady=(8, 10))
        p.bind('<Configure>', lambda event: self.record_label.configure(
            wraplength=max(1, event.width - 24)))

    def _build_stadium_panel(self, body):
        p = Panel(body, "Stadium Window")
        p.grid(row=1, column=1, sticky="nsew", padx=(8, 8), pady=(8, 0))

        self.stadium_lbl = tk.Label(
            p, text="[Selected stadium]   Year: [year]", bg=BG, fg=MUTED,
            font=font(8), anchor="w", justify='left', wraplength=270)
        self.stadium_lbl.pack(fill="x", padx=10)

        self.stadium = StadiumCanvas(p)

        self.park_factor_lbl = tk.Label(
            p, text="Park factor*: --", bg=BG, fg=MUTED,
            font=font(8))
        self.park_factor_lbl.configure(wraplength=270)
        self.park_factor_lbl.pack(side="bottom")
        self.stadium_source_lbl = tk.Label(p, text='', bg=BG, fg=MUTED, font=font(7),
                                           cursor='hand2', wraplength=270)
        self.stadium_source_lbl.pack(side='bottom', fill='x')
        p.bind('<Configure>', lambda event: [label.configure(wraplength=max(1, event.width - 24))
                                             for label in (self.stadium_lbl, self.park_factor_lbl,
                                                           self.stadium_source_lbl)])
        self._stadium_source_url = self._factor_source_url = None
        self.stadium_source_lbl.bind('<Button-1>', lambda event: self._open_source(self._stadium_source_url))
        self.park_factor_lbl.bind('<Button-1>', lambda event: self._open_source(self._factor_source_url))
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
            ("Stadium", ["All stadiums"], 0, 1,
             "stadium"),
            ("Season", ["All seasons"],
             2, 0, "season"),
            ("Inning", ["All innings"],
             2, 1, "inning"),
            ("Pitcher handedness", ["All", "Left", "Right"], 4, 0, "pitcher"),
            ("Batter side", ["All", "Left", "Right"], 4, 1,
             "batter"),
        ]
        self.vars = {}
        self.comboboxes = {}
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
            self.comboboxes[key] = cb

        # Observe the values, so mouse/keyboard selections and programmatic filter
        # changes all use the same refresh path. Coalesce quick changes into one query.
        for var in self.vars.values():
            var.trace_add('write', self._on_filter_change)

        # statistics
        tk.Label(side, text="Statistics", bg=BG, fg=FG,
                 font=font(11, "bold"), anchor="w").pack(fill="x", pady=(22, 0))
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

        tk.Label(side, text="HR rate uses all filters. Team innings use\nstadium, season and inning only.", bg=BG,
                 fg=MUTED, font=font(8), anchor="w", justify='left').pack(fill="x", pady=10)

    # --------------------------------------------------------- handlers
    def _on_filter_change(self, *_args):
        if self.analyzer is None:
            return
        if self._refresh_after_id is not None:
            self.after_cancel(self._refresh_after_id)
        self._refresh_after_id = self.after(100, self.on_analyze)

    def on_analyze(self):
        if self._refresh_after_id is not None:
            self.after_cancel(self._refresh_after_id)
            self._refresh_after_id = None
        if self.analyzer is None:
            return
        try:
            filters = self._filters()
            result = self.analyzer.analyze(filters)
            percentage = lambda value: 'N/A' if value is None else f'{100 * value:.2f}%'
            self.stat_vals['Home-run rate'].config(text=percentage(result['hr_rate']))
            self.stat_vals['Matching sample size'].config(text=f"{result['plate_appearances']:,} PA")
            average = result['average_runs']
            self.stat_vals['Average runs per inning'].config(text='N/A' if average is None else f'{average:.3f}')
            self.stat_vals['Team innings with at least\none home run (%)'].config(
                text=percentage(result['hr_inning_rate']))
            stadium_chart(self.stadium_chart.figure, result['stadium_groups'],
                          self.analyzer.dataset.venues, filters.stadium_id)
            inning_chart(self.inning_chart.figure, result['inning_groups'], filters.inning)
            self.stadium_chart.refresh()
            self.inning_chart.refresh()
            self.status.set(f"Both structures agree: {result['home_runs']:,} HR / "
                            f"{result['plate_appearances']:,} PA. Team context: {result['team_innings']:,} innings. "
                            f"Filtered query: hash {result['query_ms']['hash']:.1f} ms, "
                            f"tree {result['query_ms']['tree']:.1f} ms.")
            self.on_view_stadium()
        except Exception as exc:
            self.status.set(f'Analysis failed: {exc}')
            messagebox.showerror('Analysis failed', str(exc), parent=self)

    def _filters(self):
        hand = {'All': None, 'Left': 'L', 'Right': 'R'}
        season, inning = self.vars['season'].get(), self.vars['inning'].get()
        return Filters(self.player_ids.get(self.vars['player'].get()),
                       self.stadium_ids.get(self.vars['stadium'].get()),
                       None if season == 'All seasons' else int(season),
                       None if inning == 'All innings' else int(inning),
                       hand[self.vars['pitcher'].get()], hand[self.vars['batter'].get()])

    def _load_backend(self):
        try:
            dataset = Dataset.load(self.data_dir)
            self._load_queue.put(Analyzer(dataset, benchmark_dir=self.data_dir.parent / 'benchmark'))
        except Exception as exc:
            self._load_queue.put(exc)

    def _poll_backend(self):
        try:
            result = self._load_queue.get_nowait()
        except queue.Empty:
            self.after(100, self._poll_backend)
            return
        if isinstance(result, Exception):
            self.status.set(f'Unable to load data: {result}')
            for chart in (self.stadium_chart, self.inning_chart):
                empty_chart(chart.figure, 'Data unavailable\nSee the status message below')
                chart.refresh()
            return
        self.analyzer = result
        dataset = result.dataset
        self.player_ids = {f'{name} ({player})': player for player, name in dataset.players.items()}
        self.stadium_ids = {f'{name} [{stadium}]': stadium for stadium, name in dataset.venues.items()}
        choices = {'player': ['All Yankees'] + sorted(self.player_ids),
                   'stadium': ['All stadiums'] + sorted(self.stadium_ids),
                   'season': ['All seasons'] + [str(year) for year in reversed(dataset.seasons)],
                   'inning': ['All innings'] + list(map(str, dataset.inning_numbers))}
        for key, values in choices.items():
            self.comboboxes[key].config(values=values)
        for column, name in [(1, 'hash'), (2, 'tree')]:
            metrics = result.metrics[name]
            self.ds_vals[('Construction time', column)].config(text=f"{metrics['construction_ms']:.1f} ms")
            self.ds_vals[('Lookup time', column)].config(text=f"{metrics['lookup_us']:.2f} µs")
            self.ds_vals[('Memory usage', column)].config(text=f"{metrics['memory_bytes'] / 1048576:.2f} MiB")
        metrics = result.metrics
        if metrics.get('meets_100000_stored_entries'):
            counts = (f"MLB 2021: {metrics['input_records']:,} PA records\n"
                      f"Yankees 2021–25: {len(dataset.entries):,} PAs\n"
                      f"Yankees index: {len(result.hash_table):,} summaries")
        else:
            counts = (f"Input: {metrics['input_records']:,} PAs\n"
                      f"Index: {metrics['unique_keys']:,} summaries")
        self.record_label.config(text=counts)
        self.on_analyze()

    def _open_source(self, url):
        if url and url.startswith('https://'):
            webbrowser.open(url)

    def on_view_stadium(self):
        """Hook: update the Stadium Window for the selected stadium/year."""
        stadium = self.vars["stadium"].get()
        season = self.vars["season"].get()
        stadium_id = getattr(self, 'stadium_ids', {}).get(stadium)
        preview = stadium_id is None
        if preview:
            stadium_id = 3313  # Explicit default preview while analysis covers all parks.
        selected = self.stadium_dimensions.resolve(stadium_id, int(season) if season.isdigit() else None)
        self._stadium_source_url = self._factor_source_url = None
        if selected is None:
            self.stadium_lbl.config(text=f'{stadium}\nYear: {season}')
            self.stadium.set_dims()
            self.park_factor_lbl.config(text='No source for this venue/year')
            self.stadium_source_lbl.config(text='Select a season when this park was used')
            return
        year = selected['valid_from_year']
        label = selected['Ballpark'] + (' (preview)' if preview else '')
        self.stadium_lbl.config(text=f"{label}\nDimensions: {year}"
                               + (' (latest; analysis uses all seasons)' if season == 'All seasons' else ''))
        self.stadium.set_dims(selected['Left'], selected['Center'], selected['Right'],
                              selected['Left_Center'], selected['Right_Center'])
        self._stadium_source_url = selected['dimensions_source_url']
        self._factor_source_url = selected['park_factor_source_url']
        self.stadium_source_lbl.config(text=f"{selected['dimensions_basis']} · schematic\nSource ↗")
        factor = selected['Park Factor']
        self.park_factor_lbl.config(text=f'Runs park factor: {factor} ({year}; 100 = avg) ↗'
                                   if factor else f'Runs park factor: unavailable for {year}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='LaBronx desktop Yankees Matchup Analyzer')
    parser.add_argument('--data-dir', type=Path, default=DEFAULT_DATA)
    App(parser.parse_args().data_dir).mainloop()
