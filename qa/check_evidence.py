#!/usr/bin/env python3
"""Audit the shipped QA matrix without changing its raw files."""
import csv
import itertools
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import report


def check(directory):
    directory = Path(directory)
    expected = set(itertools.product(('steady', 'burst', 'slow', 'outage'),
                                    (7, 42, 2026), (1, 2, 3),
                                    ('push', 'credit'), ('fifo', 'priority')))
    groups = {}
    generated = completed = 0
    environment = json.loads((directory / 'environment.json').read_text())
    seen = set()
    for path in sorted(directory.glob('*/run.json')):
        config = json.loads(path.read_text())
        identity = tuple(config[k] for k in ('scenario', 'seed', 'repeat', 'admission', 'policy'))
        if identity in seen:
            raise ValueError('duplicate trial: ' + str(identity))
        seen.add(identity)
        with (path.parent / 'outcomes.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        summary = report.summarize(rows, config['duration_ms'])
        if summary['generated'] != config['producer_summary']['generated']:
            raise ValueError('generated count disagrees with producer: ' + str(path))
        for status in report.STATUSES:
            if summary[status] != config['producer_summary'][status]:
                raise ValueError('terminal outcome mismatch: ' + str(path))
        counters = config['measurements']['collector_final_counters']
        # Archived trials retain their measured metric names; new runs use Prento.
        prefix = 'prento_' if 'prento_reserved_peak_bytes' in counters else 'fanin_'
        if not (0 <= counters[prefix + 'reserved_peak_bytes'] <= config['buffer_bytes']
                and counters[prefix + 'reserved_bytes'] == 0
                and counters[prefix + 'waiting_announcements'] == 0
                and counters[prefix + 'ready_batches'] == 0):
            raise ValueError('reservation or final queue invariant: ' + str(path))
        if counters[prefix + 'completed_total'] != summary['completed']:
            raise ValueError('collector completion mismatch: ' + str(path))
        for stats in summary['classes'].values():
            if stats['completed'] and abs(stats['mean_pre_send_ms'] + stats['mean_post_send_ms'] - stats['mean_ms']) > 1e-8:
                raise ValueError('latency decomposition mismatch')
        groups.setdefault(identity[:3], []).append((config, rows))
        generated += summary['generated']
        completed += summary['completed']
    if seen != expected:
        raise ValueError(f'incomplete/unexpected matrix: missing={expected-seen}, extra={seen-expected}')
    for group in groups.values():
        report.validate_group([config for config, _ in group], environment.get('binary_sha256'))
        for _, rows in group[1:]:
            report.compare_pair(group[0][1], rows)
    result = dict(trials=len(seen), matched_groups=len(groups), generated=generated,
                  completed=completed, not_completed=generated-completed,
                  reservation_and_final_queue_invariants='passed',
                  matched_workloads_and_configuration='passed',
                  latency_decomposition='passed')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    check(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'results/2026-11-04-qa')
