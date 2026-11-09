"""Native Tk check: removed buttons stay absent and filters refresh the app.

Run from the project root with a desktop-capable Python: python3 tests/gui_dynamic_smoke.py
"""
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gui import App


def main():
    data = ROOT / 'data/yankees_pa'
    if not (data / 'yankees_plate_appearances.csv').exists():
        data = Path('/Users/steven/PyCharmProjects/LaBronx/data/yankees_pa')
    app = App(data)

    def settle():
        deadline = time.monotonic() + 5
        while app._refresh_after_id is not None and time.monotonic() < deadline:
            app.update()
            time.sleep(.01)
        app.update()
        assert app._refresh_after_id is None, 'Automatic refresh did not finish'

    try:
        def widget_texts(widget):
            if 'text' in widget.keys():
                yield str(widget.cget('text'))
            for child in widget.winfo_children():
                yield from widget_texts(child)

        texts = set(widget_texts(app))
        assert 'Analyze' not in texts, 'Redundant Analyze control is still visible'
        assert 'View Stadium' not in texts, 'Redundant View Stadium control is still visible'
        assert '+' not in texts, 'Unused plus control is still visible'
        print('PASS: Analyze, View Stadium, and plus controls are absent', flush=True)
        deadline = time.monotonic() + 45
        while app.analyzer is None and time.monotonic() < deadline:
            app.update()
            time.sleep(.01)
        assert app.analyzer is not None, app.status.get()
        original_analyze = app.analyzer.analyze
        calls = []

        def counted(filters):
            calls.append(filters)
            return original_analyze(filters)

        app.analyzer.analyze = counted
        player = next(name for name, pk in app.player_ids.items() if pk == 592450)
        stadium = next(name for name, pk in app.stadium_ids.items() if pk == 3313)
        for key, value in [('season', '2025'), ('player', player), ('stadium', stadium),
                           ('inning', '1'), ('pitcher', 'Left'), ('batter', 'Left')]:
            before = len(calls)
            app.vars[key].set(value)  # No button press and no direct on_analyze().
            settle()
            assert len(calls) == before + 1, f'{key} did not trigger exactly one refresh'
            expected = original_analyze(app._filters())
            assert app.stat_vals['Matching sample size'].cget('text') == f"{expected['plate_appearances']:,} PA"
            assert len(app.stadium_chart.figure.axes[0].patches) == min(7, len(expected['stadium_groups']))
            assert len(app.inning_chart.figure.axes[0].patches) == len(expected['inning_groups'])
            assert 'Both structures agree' in app.status.get()
            filters = app._filters()
            dimensions = app.stadium_dimensions.resolve(filters.stadium_id or 3313, filters.season)
            assert (app.stadium.lf, app.stadium.cf, app.stadium.rf) == (
                dimensions['Left'], dimensions['Center'], dimensions['Right'])
            assert app._stadium_source_url == dimensions['dimensions_source_url']
            print(f'PASS: {key} automatically updates statistics and both chart canvases', flush=True)
        assert app.stat_vals['Home-run rate'].cget('text') == 'N/A'
        before = len(calls)
        for key, value in [('player', 'All Yankees'), ('batter', 'All'), ('inning', 'All innings'),
                           ('stadium', 'All stadiums'), ('season', '2024')]:
            app.vars[key].set(value)
        settle()
        assert len(calls) == before + 1, 'Rapid changes should coalesce into one refresh'
        assert app._filters().season == 2024
        print('PASS: rapid filter changes coalesce into one query using the final selection', flush=True)

        # Check real, mapped widget geometry; a withdrawn window cannot expose
        # the clipped record text and collapsed canvas seen on scaled displays.
        for size in ('1000x680', '1200x800'):
            app.geometry(size)
            app.update()
            app.update_idletasks()
            counts = app.record_label
            self_bottom = counts.winfo_rooty() + counts.winfo_height()
            panel_bottom = app.results_panel.winfo_rooty() + app.results_panel.winfo_height()
            assert counts.winfo_height() >= counts.winfo_reqheight(), f'Record counts clipped at {size}'
            assert self_bottom <= panel_bottom - 2, f'Record counts extend beyond panel at {size}'
            assert counts.winfo_width() >= counts.winfo_reqwidth(), f'Record counts too wide at {size}'
            for label in app.ds_vals.values():
                assert label.winfo_width() >= label.winfo_reqwidth(), f'Benchmark value clipped at {size}'
            assert app.stadium.winfo_height() >= 110, f'Stadium drawing collapsed at {size}'
            boxes = [app.stadium.bbox(item) for item in app.stadium.find_withtag('distance_label')]
            assert len(boxes) == 3, 'Missing field-distance labels'
            boxes.sort(key=lambda box: box[0])
            assert all(left[2] <= right[0] for left, right in zip(boxes, boxes[1:])), (
                f'Field-distance labels overlap at {size}')
            print(f'PASS: readable record counts, benchmark values, and stadium drawing at {size}', flush=True)
    finally:
        app.destroy()


if __name__ == '__main__':
    main()
