#!/usr/bin/env python3
"""Render the README comparison from preserved benchmark summaries.

Authoring dependency: matplotlib. Core builds/tests do not require it.
"""
import json
import math
from pathlib import Path
import statistics
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'results/2026-11-04-qa'
OUTPUT = Path(__file__).resolve().parent
BASELINE = 'push/fifo'
CANDIDATE = 'push/priority'
COLORS = {'baseline': '#7A8492', 'candidate': '#2459A6', 'text': '#182536', 'grid': '#E5E9EF'}


def reviewed_rows():
    aggregate = json.loads((EVIDENCE / 'aggregate.json').read_text())
    summary = json.loads((EVIDENCE / 'summary.json').read_text())
    rows = []
    for scenario, label in [('burst', 'Burst'), ('slow', 'Slow sink')]:
        values = {}
        for mode in (BASELINE, CANDIDATE):
            runs = [r for r in summary if r['scenario'] == scenario
                    and f"{r['admission']}/{r['policy']}" == mode]
            if len(runs) != 9 or sorted({r['seed'] for r in runs}) != [7, 42, 2026]:
                raise ValueError('expected nine runs over three seeds')
            published = next(r for r in aggregate if (r['scenario'], r['mode']) == (scenario, mode))
            mean = statistics.mean(r['classes']['critical']['mean_ms'] for r in runs)
            if not math.isclose(mean, published['classes']['critical']['mean_ms'], abs_tol=1e-9):
                raise ValueError('aggregate does not match equally weighted run means')
            values[mode] = mean
        seed_reductions = []
        for seed in (7, 42, 2026):
            means = {}
            for mode in (BASELINE, CANDIDATE):
                runs = [r for r in summary if r['scenario'] == scenario and r['seed'] == seed
                        and f"{r['admission']}/{r['policy']}" == mode]
                if len(runs) != 3:
                    raise ValueError('expected three timing repeats per seed')
                means[mode] = statistics.mean(r['classes']['critical']['mean_ms'] for r in runs)
            seed_reductions.append(100 * (1 - means[CANDIDATE] / means[BASELINE]))
        rows.append(dict(scenario=scenario, label=label, baseline=values[BASELINE], candidate=values[CANDIDATE],
                         reduction=100 * (1 - values[CANDIDATE] / values[BASELINE]),
                         seed_min=min(seed_reductions), seed_max=max(seed_reductions)))
    return rows


def main():
    rows = reviewed_rows()
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'svg.fonttype': 'none',
                         'svg.hashsalt': 'prento-readme-results', 'axes.unicode_minus': False})
    fig = plt.figure(figsize=(9.2, 6.0), facecolor='white')
    ax = fig.add_axes([.205, .255, .575, .51])
    labels, positions = [], []
    for row, center in zip(rows, [2.65, .65]):
        for value, y, label, color in [(row['baseline'], center+.30, 'FIFO push', COLORS['baseline']),
                                        (row['candidate'], center-.30, 'Priority push', COLORS['candidate'])]:
            ax.barh(y, value, height=.38, color=color, zorder=3)
            ax.text(value+14, y, f'{value:.2f}', va='center', fontsize=12.5, color=COLORS['text'])
            labels.append(f"{row['label']}\n{label}")
            positions.append(y)
        ax.text(1.10, center+.10, f"{row['reduction']:.1f}%", transform=ax.get_yaxis_transform(),
                va='center', ha='center', fontsize=24, fontweight='bold', color=COLORS['candidate'])
        ax.text(1.10, center-.33, 'lower mean\nlatency', transform=ax.get_yaxis_transform(),
                va='center', ha='center', fontsize=10.5, color=COLORS['text'])
    ax.set_yticks(positions, labels)
    ax.tick_params(axis='y', length=0, pad=12, labelsize=11.5, colors=COLORS['text'])
    ax.set_xlim(0, 1050)
    ax.set_ylim(-.05, 3.4)
    ax.set_xticks([0, 250, 500, 750, 1000])
    ax.tick_params(axis='x', length=3, labelsize=10, colors=COLORS['text'])
    ax.set_xlabel('Milliseconds · lower is better', fontsize=11, color=COLORS['text'], labelpad=10)
    ax.xaxis.grid(True, color=COLORS['grid'], linewidth=.8)
    ax.set_axisbelow(True)
    for side in ['top', 'right']:
        ax.spines[side].set_visible(False)
    for side in ['bottom', 'left']:
        ax.spines[side].set_color('#A9B1BC')
        ax.spines[side].set_linewidth(.8)
    fig.text(.055, .935, 'Mean critical end-to-end latency', fontsize=20, fontweight='bold', color=COLORS['text'])
    fig.text(.055, .883, 'Intended generation → sink processing acknowledgment', fontsize=11.5, color='#4E5B6B')
    fig.text(.055, .135, '9 runs per bar · 3 workload seeds × 3 timing repeats · push admission in both modes',
             fontsize=9.4, color='#4E5B6B')
    ranges='; '.join(f"{r['label'].lower()} {r['seed_min']:.1f}–{r['seed_max']:.1f}%" for r in rows)
    fig.text(.055, .095, 'Reduction by seed: '+ranges+' (descriptive ranges).', fontsize=9.4, color='#4E5B6B')
    fig.text(.055, .055, 'Selected stressed workloads. Full scenario matrix, sample sizes and bulk costs are linked in the README.',
             fontsize=9.0, color='#4E5B6B')
    title='Mean critical end-to-end latency: FIFO push versus priority push'
    fig.savefig(OUTPUT / 'results.svg', metadata={'Date': None, 'Title': title})
    fig.savefig(OUTPUT / 'results.png', dpi=180, metadata={'Title': title})
    plt.close(fig)
    namespace = 'http://www.w3.org/2000/svg'
    ET.register_namespace('', namespace)
    document = ET.parse(OUTPUT / 'results.svg')
    svg = document.getroot()
    svg.set('role', 'img')
    svg.set('aria-labelledby', 'results-title results-description')
    title_element = ET.Element(f'{{{namespace}}}title', id='results-title')
    title_element.text = title
    description = ET.Element(f'{{{namespace}}}desc', id='results-description')
    description.text = '; '.join(f"{r['label']}: {r['baseline']:.2f} to {r['candidate']:.2f} milliseconds, "
                                f"{r['reduction']:.1f}% lower mean critical end-to-end latency" for r in rows)
    svg.insert(0, title_element)
    svg.insert(1, description)
    document.write(OUTPUT / 'results.svg', encoding='utf-8', xml_declaration=True)
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
