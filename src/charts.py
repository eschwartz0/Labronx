"""Matplotlib chart drawing shared by the desktop window and image checks."""
from matplotlib.figure import Figure

BG, FG, MUTED = '#ece3d2', '#1c1c1c', '#6b6559'
INK, SELECTED = '#29475d', '#9c6f37'


def make_figure():
    return Figure(figsize=(3.1, 2.7), dpi=100, facecolor=BG, layout='constrained')


def prepare(figure):
    figure.clear()
    axis = figure.add_subplot(111)
    axis.set_facecolor(BG)
    axis.tick_params(labelsize=7, colors=FG)
    for side in ('top', 'right'):
        axis.spines[side].set_visible(False)
    for side in ('left', 'bottom'):
        axis.spines[side].set_color('#b8ae9a')
    axis.set_axisbelow(True)
    return axis


def empty_chart(figure, message='No matching completed PAs'):
    axis = prepare(figure)
    axis.set_axis_off()
    axis.text(.5, .5, message, transform=axis.transAxes, ha='center', va='center',
              color=MUTED, fontsize=9, wrap=True)


def stadium_chart(figure, groups, names, selected=None):
    if not groups:
        empty_chart(figure)
        return
    axis = prepare(figure)
    # Keep labels legible in the original narrow panel; disclose the sample ranking.
    rows = sorted(groups.items(), key=lambda pair: (-pair[1][0], pair[0]))[:7]
    labels, rates = [], []
    for stadium, (pa, hr) in rows:
        name = names.get(stadium, str(stadium))
        labels.append(name if len(name) <= 19 else name[:17] + '…')
        rates.append(100 * hr / pa)
    positions = list(range(len(rows)))
    axis.barh(positions, rates, color=[SELECTED if key == selected else INK for key, _ in rows],
              height=.63)
    axis.set_yticks(positions, labels, fontsize=6.5)
    axis.invert_yaxis()
    limit = max(max(rates) * 1.5, 5)
    axis.set_xlim(0, limit)
    for y, (_, (pa, _)), rate in zip(positions, rows, rates):
        axis.text(rate + limit * .025, y, f'{rate:.1f}%\nn={pa:,}', va='center',
                  fontsize=6, color=FG)
    axis.set_xlabel('Historical HR / completed PA (%)', fontsize=7, color=FG)
    axis.xaxis.grid(True, alpha=.2)


def inning_chart(figure, groups, selected=None):
    if not groups:
        empty_chart(figure)
        return
    axis = prepare(figure)
    rows = sorted(groups.items())
    innings = [key for key, _ in rows]
    rates = [100 * hr / pa for _, (pa, hr) in rows]
    axis.bar(innings, rates, width=.7,
             color=[SELECTED if key == selected else INK for key in innings])
    axis.set_xticks(innings)
    axis.set_ylim(0, max(max(rates) * 1.4, 5))
    for inning, (_, (pa, _)), rate in zip(innings, rows, rates):
        axis.text(inning, rate + axis.get_ylim()[1] * .025, f'{pa:,}',
                  ha='center', va='bottom', fontsize=5.5, rotation=90 if len(rows) > 10 else 0,
                  color=MUTED)
    axis.set_xlabel('Inning · labels show completed PA count', fontsize=7, color=FG)
    axis.set_ylabel('Historical HR / PA (%)', fontsize=7, color=FG)
    axis.yaxis.grid(True, alpha=.2)
