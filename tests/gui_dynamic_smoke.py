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
    app.withdraw()

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
        print('PASS: Analyze and View Stadium controls are absent', flush=True)
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
    finally:
        app.destroy()


if __name__ == '__main__':
    main()
