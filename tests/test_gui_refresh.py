"""Exercise the real GUI handlers with Tcl variables/timers, without a display.

Only the visible widgets are replaced with small state holders. Dataset queries,
filter traces, debounce timers, charts, metadata, and the App handlers are real.
The separate gui_dynamic_smoke.py checks the native Tk widgets on a desktop.
"""
from pathlib import Path
import queue
import sys
import time
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from analyzer import Analyzer, Dataset
from charts import make_figure
from gui import App
from models import Filters, Summary
from stadium_metadata import StadiumMetadata


class WidgetState:
    def __init__(self):
        self.options = {}

    def config(self, **options):
        self.options.update(options)

    def cget(self, option):
        return self.options.get(option)


class GuiRefreshTests(unittest.TestCase):
    def setUp(self):
        self.tcl = tk.Tcl()  # No tk.Tk() and no graphical display required.
        self.view = SimpleNamespace()
        view = self.view
        for method in ('_filters', '_on_filter_change', 'on_analyze',
                       'on_view_stadium', '_poll_backend'):
            setattr(view, method, getattr(App, method).__get__(view))
        view.after, view.after_cancel = self.tcl.after, self.tcl.after_cancel
        view._refresh_after_id = None
        view.analyzer = None
        view._load_queue = queue.Queue()
        defaults = dict(player='All Yankees', stadium='All stadiums', season='All seasons',
                        inning='All innings', pitcher='All', batter='All')
        view.vars = {key: tk.StringVar(master=self.tcl, value=value)
                     for key, value in defaults.items()}
        for var in view.vars.values():
            var.trace_add('write', view._on_filter_change)
        view.status = tk.StringVar(master=self.tcl)
        view.comboboxes = {key: WidgetState() for key in defaults}
        view.stat_vals = {key: WidgetState() for key in (
            'Home-run rate', 'Matching sample size', 'Average runs per inning',
            'Team innings with at least\none home run (%)')}
        view.ds_vals = {(metric, column): WidgetState()
                        for metric in ('Construction time', 'Lookup time', 'Memory usage')
                        for column in (1, 2)}
        view.record_label = WidgetState()
        view.stadium_chart = SimpleNamespace(figure=make_figure(), refresh=Mock())
        view.inning_chart = SimpleNamespace(figure=make_figure(), refresh=Mock())
        view.stadium_dimensions = StadiumMetadata()
        view.stadium = Mock()
        view.stadium_lbl, view.park_factor_lbl, view.stadium_source_lbl = (
            WidgetState(), WidgetState(), WidgetState())
        dataset = Dataset(
            entries=[
                ((10, 3313, 2025, 1, 'R', 'R'), Summary(1, 1)),
                ((10, 3313, 2025, 1, 'R', 'R'), Summary(1, 0)),
                ((11, 3313, 2025, 1, 'L', 'L'), Summary(1, 0)),
                ((10, 3, 2024, 10, 'L', 'R'), Summary(1, 0)),
                ((11, 3, 2024, 2, 'R', 'L'), Summary(1, 1)),
                ((12, 3313, 2024, 2, 'R', 'R'), Summary(1, 0)),
            ],
            innings=[(3313, 2025, 1, 2, True), (3313, 2025, 2, 0, False),
                     (3, 2024, 10, 0, False), (3, 2024, 2, 1, True),
                     (3313, 2024, 2, 0, False)],
            players={10: 'Player A', 11: 'Player B', 12: 'Player C'},
            venues={3313: 'Yankee Stadium', 3: 'Fenway Park'},
            seasons=[2024, 2025], inning_numbers=[1, 2, 10], report={})
        self.analyzer = Analyzer(dataset, repeats=1)
        self.analyzer.analyze = Mock(wraps=self.analyzer.analyze)
        view._load_queue.put(self.analyzer)
        view._poll_backend()  # Exercises the automatic initial analysis too.
        self.analyzer.analyze.reset_mock()
        error_dialog = patch('gui.messagebox.showerror')
        self.errors = error_dialog.start()
        self.addCleanup(error_dialog.stop)

    def tearDown(self):
        for timer in self.tcl.splitlist(self.tcl.eval('after info')):
            self.tcl.after_cancel(timer)

    def settle(self):
        deadline = time.monotonic() + 3
        while self.view._refresh_after_id is not None and time.monotonic() < deadline:
            self.tcl.eval('update')
            time.sleep(.005)
        self.assertIsNone(self.view._refresh_after_id, 'Automatic refresh timed out')
        self.errors.assert_not_called()

    def test_initial_data_load_populates_menus_and_statistics(self):
        self.assertEqual(self.view.stat_vals['Matching sample size'].cget('text'), '6 PA')
        self.assertEqual(self.view.stat_vals['Home-run rate'].cget('text'), '33.33%')
        self.assertEqual(self.view.comboboxes['season'].cget('values'),
                         ['All seasons', '2025', '2024'])
        self.assertEqual(self.view.comboboxes['inning'].cget('values'),
                         ['All innings', '1', '2', '10'])
        self.assertIn('(preview)', self.view.stadium_lbl.cget('text'))

    def test_each_filter_automatically_refreshes_stats_and_both_charts(self):
        selections = [('season', '2025', 3), ('player', 'Player A (10)', 2),
                      ('stadium', 'Yankee Stadium [3313]', 2), ('inning', '1', 2),
                      ('pitcher', 'Right', 2), ('batter', 'Left', 0)]
        for key, value, expected_pa in selections:
            with self.subTest(filter=key):
                self.analyzer.analyze.reset_mock()
                self.view.stadium_chart.refresh.reset_mock()
                self.view.inning_chart.refresh.reset_mock()
                self.view.vars[key].set(value)
                self.settle()
                self.analyzer.analyze.assert_called_once_with(self.view._filters())
                self.assertEqual(self.view.stat_vals['Matching sample size'].cget('text'),
                                 f'{expected_pa} PA')
                self.view.stadium_chart.refresh.assert_called_once()
                self.view.inning_chart.refresh.assert_called_once()
                self.assertIn('Both structures agree', self.view.status.get())

    def test_rapid_filter_changes_make_one_query_with_final_values(self):
        self.view.vars['season'].set('2025')
        self.view.vars['season'].set('2024')
        self.view.vars['inning'].set('10')
        self.view.vars['pitcher'].set('Left')
        self.settle()
        self.analyzer.analyze.assert_called_once_with(Filters(season=2024, inning=10, pitcher_hand='L'))
        self.assertEqual(self.view.stat_vals['Matching sample size'].cget('text'), '1 PA')

    def test_empty_selection_clears_stale_statistics_and_charts(self):
        self.view.vars['player'].set('Player C (12)')
        self.view.vars['batter'].set('Left')
        self.settle()
        self.assertEqual(self.view.stat_vals['Matching sample size'].cget('text'), '0 PA')
        self.assertEqual(self.view.stat_vals['Home-run rate'].cget('text'), 'N/A')
        # The team-innings statistic intentionally ignores player/hand filters.
        self.assertEqual(self.view.stat_vals['Average runs per inning'].cget('text'), '0.600')
        for chart in (self.view.stadium_chart, self.view.inning_chart):
            self.assertEqual(len(chart.figure.axes[0].patches), 0)
            self.assertEqual(chart.figure.axes[0].texts[0].get_text(), 'No matching completed PAs')

    def test_stadium_and_season_automatically_update_dimensions_and_sources(self):
        self.view.vars['stadium'].set('Fenway Park [3]')
        self.view.vars['season'].set('2024')
        self.settle()
        expected = self.view.stadium_dimensions.resolve(3, 2024)
        self.view.stadium.set_dims.assert_called_with(
            expected['Left'], expected['Center'], expected['Right'],
            expected['Left_Center'], expected['Right_Center'])
        self.assertIn('2024', self.view.stadium_lbl.cget('text'))
        self.assertNotIn('(preview)', self.view.stadium_lbl.cget('text'))
        self.assertEqual(self.view._stadium_source_url, expected['dimensions_source_url'])
        self.assertEqual(self.view._factor_source_url, expected['park_factor_source_url'])
        self.assertIn(expected['Park Factor'], self.view.park_factor_lbl.cget('text'))

    def test_unavailable_stadium_year_clears_old_dimensions_and_source_links(self):
        self.view.vars['stadium'].set('Fenway Park [3]')
        self.view.vars['season'].set('1900')
        self.settle()
        self.view.stadium.set_dims.assert_called_with()
        self.assertIsNone(self.view._stadium_source_url)
        self.assertIsNone(self.view._factor_source_url)
        self.assertEqual(self.view.park_factor_lbl.cget('text'), 'No source for this venue/year')
        self.assertEqual(self.view.stat_vals['Average runs per inning'].cget('text'), 'N/A')

    def test_filter_changes_before_backend_is_ready_are_safe(self):
        self.view.analyzer = None
        self.view.vars['season'].set('2025')
        self.assertIsNone(self.view._refresh_after_id)
        self.analyzer.analyze.assert_not_called()

    def test_backend_failure_displays_status_and_empty_charts(self):
        self.view.analyzer = None
        self.view._load_queue.put(ValueError('Missing data file'))
        self.view._poll_backend()
        self.assertIn('Unable to load data: Missing data file', self.view.status.get())
        for chart in (self.view.stadium_chart, self.view.inning_chart):
            self.assertEqual(len(chart.figure.axes[0].patches), 0)
            self.assertIn('Data unavailable', chart.figure.axes[0].texts[0].get_text())

    def test_query_failure_reports_error_instead_of_claiming_success(self):
        self.analyzer.analyze.side_effect = ValueError('Data structures disagree')
        self.view.on_analyze()
        self.assertEqual(self.view.status.get(), 'Analysis failed: Data structures disagree')
        self.errors.assert_called_once_with('Analysis failed', 'Data structures disagree',
                                            parent=self.view)


if __name__ == '__main__':
    unittest.main()
