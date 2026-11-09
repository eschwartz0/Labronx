"""Chart output checks using Matplotlib's noninteractive renderer."""
from pathlib import Path
import sys
import unittest

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgba

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from charts import INK, SELECTED, inning_chart, make_figure, stadium_chart
from models import Summary


class ChartTests(unittest.TestCase):
    def setUp(self):
        self.figure = make_figure()
        self.canvas = FigureCanvasAgg(self.figure)

    def test_stadium_rates_ranking_selection_and_seven_venue_limit(self):
        groups = {venue: Summary(venue * 10, venue) for venue in range(1, 10)}
        stadium_chart(self.figure, groups, {9: 'Selected park'}, selected=9)
        self.canvas.draw()
        axis = self.figure.axes[0]
        self.assertEqual(len(axis.patches), 7)
        self.assertEqual([label.get_text() for label in axis.get_yticklabels()],
                         ['Selected park', '8', '7', '6', '5', '4', '3'])
        self.assertTrue(all(bar.get_width() == 10 for bar in axis.patches))
        self.assertEqual(axis.patches[0].get_facecolor(), to_rgba(SELECTED))
        self.assertEqual(axis.patches[1].get_facecolor(), to_rgba(INK))
        self.assertIn('n=90', axis.texts[0].get_text())

    def test_tied_stadium_samples_have_deterministic_order(self):
        stadium_chart(self.figure, {3: Summary(10, 2), 1: Summary(10, 1)}, {})
        self.canvas.draw()
        axis = self.figure.axes[0]
        self.assertEqual([label.get_text() for label in axis.get_yticklabels()], ['1', '3'])
        self.assertEqual([bar.get_width() for bar in axis.patches], [10, 20])

    def test_extra_innings_are_sorted_and_rates_use_each_sample_size(self):
        inning_chart(self.figure, {12: Summary(5, 1), 1: Summary(20, 1), 10: Summary(4, 0)},
                     selected=12)
        self.canvas.draw()
        axis = self.figure.axes[0]
        self.assertEqual(list(axis.get_xticks()), [1, 10, 12])
        self.assertEqual([bar.get_height() for bar in axis.patches], [5, 0, 20])
        self.assertEqual(axis.patches[-1].get_facecolor(), to_rgba(SELECTED))
        self.assertEqual([text.get_text() for text in axis.texts], ['20', '4', '5'])

    def test_zero_home_runs_have_a_visible_positive_axis_range(self):
        inning_chart(self.figure, {1: Summary(12, 0)})
        self.canvas.draw()
        axis = self.figure.axes[0]
        self.assertEqual(axis.patches[0].get_height(), 0)
        self.assertGreater(axis.get_ylim()[1], 0)

    def test_empty_selection_clears_previous_bars_in_both_charts(self):
        for kind in ('stadium', 'inning'):
            with self.subTest(kind=kind):
                if kind == 'stadium':
                    stadium_chart(self.figure, {1: Summary(2, 1)}, {})
                    stadium_chart(self.figure, {}, {})
                else:
                    inning_chart(self.figure, {1: Summary(2, 1)})
                    inning_chart(self.figure, {})
                self.canvas.draw()
                self.assertEqual(len(self.figure.axes), 1)
                axis = self.figure.axes[0]
                self.assertEqual(len(axis.patches), 0)
                self.assertEqual(axis.texts[0].get_text(), 'No matching completed PAs')


if __name__ == '__main__':
    unittest.main()
