#!/usr/bin/env python3
"""Summarize measured outcomes. No predicted improvements are inserted."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from collections import defaultdict
from html import escape

STATUSES = ("completed", "failed_unknown", "producer_drop")

def percentile(values, p):
    if not values:
        return None
    return sorted(values)[max(0, math.ceil(p * len(values)) - 1)]

def latency_parts(row):
    intended, sent, end = (int(row[k]) for k in ("intended_ns", "send_ns", "end_ns"))
    if sent <= 0 or not 0 <= intended <= sent <= end:
        raise ValueError("completed message has impossible/missing timestamps")
    return (sent-intended)/1e6, (end-sent)/1e6, (end-intended)/1e6

def signature(rows):
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("duplicate logical IDs in outcome ledger")
    if not rows:
        return []
    origin = min(int(r["intended_ns"]) for r in rows)
    return sorted((int(r["id"]), r.get("producer", "0"), r["class"], int(r["bytes"]),
                   int(r["intended_ns"])-origin) for r in rows)

def summarize(rows, duration_ms):
    if duration_ms <= 0:
        raise ValueError("duration must be positive")
    fingerprint = signature(rows)
    if any(r["status"] not in STATUSES or r["class"] not in ("critical", "bulk") or int(r["bytes"]) <= 0 for r in rows):
        raise ValueError("invalid outcome, class or payload size")
    result = {"generated": len(rows), "generated_bytes": sum(int(r["bytes"]) for r in rows),
              "workload_sha256": hashlib.sha256(json.dumps(fingerprint).encode()).hexdigest()}
    for status in STATUSES:
        subset = [r for r in rows if r["status"] == status]
        result[status] = len(subset)
        result[status + "_bytes"] = sum(int(r["bytes"]) for r in subset)
    result["classes"] = {}
    for kind in ("critical", "bulk"):
        subset = [r for r in rows if r["class"] == kind]
        done = [r for r in subset if r["status"] == "completed"]
        parts = [latency_parts(r) for r in done]
        pre, post, total = ([p[i] for p in parts] for i in range(3))
        for row, (_, _, elapsed) in zip(done, parts):
            if "latency_ms" in row and abs(float(row["latency_ms"])-elapsed) > .000002:
                raise ValueError("CSV latency disagrees with timestamps")
        result["classes"][kind] = {
            "generated": len(subset), "completed": len(done),
            "completion_fraction": len(done)/len(subset) if subset else None,
            "mean_ms": statistics.mean(total) if total else None,
            "mean_pre_send_ms": statistics.mean(pre) if pre else None,
            "mean_post_send_ms": statistics.mean(post) if post else None,
            "p50_ms": percentile(total, .5), "p99_ms": percentile(total, .99),
            "p999_ms": percentile(total, .999), "max_ms": max(total) if total else None,
            "p99_equals_max": bool(total) and math.ceil(.99*len(total)) == len(total),
            "producer_wait_p99_ms": percentile(pre, .99),
        }
    if rows:
        start = min(int(r["intended_ns"]) for r in rows)
        offer_end = start + duration_ms * 1000000
        end = max(int(r["end_ns"]) for r in rows)
        completed_in_window = [r for r in rows if r["status"] == "completed" and int(r["end_ns"]) <= offer_end]
        result["offered_bytes_per_sec"] = result["generated_bytes"] / (duration_ms / 1000)
        result["completion_bytes_per_sec_during_offer"] = sum(int(r["bytes"]) for r in completed_in_window) / (duration_ms / 1000)
        result["drain_ms"] = max(0, (end - offer_end) / 1000000)
    return result

def compare_pair(reference, candidate):
    if signature(reference) != signature(candidate):
        raise ValueError("paired modes have different logical inputs or intended schedules")
    ref, cand = ({r["id"]: r for r in rows} for rows in (reference, candidate))
    result = {"classes": {}, "messages": []}
    for kind in ("critical", "bulk"):
        stats = dict(both_completed=0, reference_only_completed=0, candidate_only_completed=0,
                     neither_completed=0, faster=0, slower=0, tied=0)
        before, after = [], []
        for identity in sorted(ref, key=int):
            a, b = ref[identity], cand[identity]
            if a["class"] != kind:
                continue
            ac, bc = a["status"] == "completed", b["status"] == "completed"
            key = "both_completed" if ac and bc else "reference_only_completed" if ac else "candidate_only_completed" if bc else "neither_completed"
            stats[key] += 1
            row = {"id": identity, "class": kind, "reference_status": a["status"], "candidate_status": b["status"]}
            for name, item, ok in (("reference", a, ac), ("candidate", b, bc)):
                if ok:
                    pre, post, total = latency_parts(item)
                    row.update({name+"_pre_send_ms": pre, name+"_post_send_ms": post, name+"_ms": total})
            if ac and bc:
                old, new = row["reference_ms"], row["candidate_ms"]
                before.append(old); after.append(new)
                delta = old-new
                row["reduction_ms"] = delta
                stats["faster" if delta > .000001 else "slower" if delta < -.000001 else "tied"] += 1
            result["messages"].append(row)
        stats["mean_reference_ms"] = statistics.mean(before) if before else None
        stats["mean_candidate_ms"] = statistics.mean(after) if after else None
        stats["mean_reduction_pct"] = round((1-statistics.mean(after)/statistics.mean(before))*100, 12) if before and statistics.mean(before)>0 else None
        result["classes"][kind] = stats
    return result

def aggregate(runs):
    groups = defaultdict(list)
    for run in runs:
        groups[(run["scenario"], run["admission"]+"/"+run["policy"])].append(run)
    output = []
    for (scenario, mode), group in sorted(groups.items()):
        item = {"scenario": scenario, "mode": mode, "runs": len(group), "seeds": sorted({r["seed"] for r in group}), "classes": {}}
        for kind in ("critical", "bulk"):
            classes = [r["classes"][kind] for r in group]
            valid = [c for c in classes if c["mean_ms"] is not None]
            stats = {"generated": sum(c["generated"] for c in classes), "completed": sum(c["completed"] for c in classes)}
            for key in ("mean_ms", "mean_pre_send_ms", "mean_post_send_ms"):
                stats[key] = statistics.mean(c[key] for c in valid) if valid else None
            stats["max_ms"] = max((c["max_ms"] for c in valid), default=None)
            per_seed = []
            for seed in item["seeds"]:
                values = [r["classes"][kind]["mean_ms"] for r in group if r["seed"] == seed and r["classes"][kind]["mean_ms"] is not None]
                if values:
                    per_seed.append(statistics.mean(values))
            stats["seed_mean_min_ms"] = min(per_seed, default=None)
            stats["seed_mean_max_ms"] = max(per_seed, default=None)
            item["classes"][kind] = stats
        output.append(item)
    return output

def validate_group(configs, environment_digest=None):
    common=('duration_ms','rate','sink_rate','producers','queue_items','buffer_bytes',
            'bulk_bytes','critical_bytes','critical_fraction','timeout_ms','seed','scenario')
    for key in common:
        if any(key not in config for config in configs):
            raise ValueError('missing matched experimental setting: '+key)
        if any(config[key]!=configs[0][key] for config in configs[1:]):
            raise ValueError('matched modes differ in experimental setting: '+key)
    identities=[config.get('binary_sha256',environment_digest) for config in configs]
    if len(set(identities))!=1:
        raise ValueError('matched modes use different executable identities')
    if environment_digest and any(identity!=environment_digest for identity in identities):
        raise ValueError('run executable identity disagrees with environment')
    source='per-run' if all('binary_sha256' in config for config in configs) else 'global-environment' if environment_digest else 'unavailable'
    return dict(configuration_verified=True,binary_sha256=identities[0],binary_identity_source=source)

def stacked_chart(directory, aggregates):
    rows=[r for r in aggregates if r['classes']['critical']['mean_ms'] is not None]
    maximum=max((r['classes']['critical']['mean_ms'] for r in rows),default=1) or 1
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="{140+len(rows)*30}" role="img" aria-labelledby="title desc">',
         '<title id="title">Critical message mean latency breakdown</title>',
         '<desc id="desc">Blue is pre-send; orange is post-send including transfer, admission, sink and ACK. Each run is weighted equally.</desc>',
         '<rect width="100%" height="100%" fill="white"/>','<g font-family="sans-serif" font-size="12" fill="#172033">',
         '<text x="16" y="24" font-size="18">Mean critical latency: where time accumulates</text>',
         '<rect x="16" y="39" width="14" height="14" fill="#2563eb"/><text x="36" y="51">Pre-send</text>',
         '<rect x="150" y="39" width="14" height="14" fill="#ea580c"/><text x="170" y="51">Post-send (not isolated collector queueing)</text>']
    for tick in range(6):
        svg.append(f'<text x="{330+tick*120}" y="82">{maximum*tick/5:.0f} ms</text>')
    for i,row in enumerate(rows):
        y=95+i*30
        c=row['classes']['critical']
        pre,post=c['mean_pre_send_ms']/maximum*600,c['mean_post_send_ms']/maximum*600
        label=f"{row['scenario']} {row['mode']} ({len(row['seeds'])} seeds)"
        svg.extend([f'<text x="16" y="{y+14}">{escape(label)}</text>',
                    f'<rect x="330" y="{y}" width="{pre:.3f}" height="20" fill="#2563eb"/>',
                    f'<rect x="{330+pre:.3f}" y="{y}" width="{post:.3f}" height="20" fill="#ea580c"/>',
                    f'<text x="950" y="{y+14}">{c["mean_pre_send_ms"]:.2f} + {c["mean_post_send_ms"]:.2f} = {c["mean_ms"]:.2f} ms</text>'])
    svg.extend(['</g></svg>'])
    (directory/'latency-breakdown.svg').write_text('\n'.join(svg))

def render(directory):
    directory=Path(directory)
    runs=[]
    matched=defaultdict(dict)
    matched_configs=defaultdict(dict)
    environment_path=directory/'environment.json'
    environment=json.loads(environment_path.read_text()) if environment_path.exists() else {}
    modes=('push/fifo','push/priority','credit/fifo','credit/priority')
    comparisons=((modes[0],modes[1]),(modes[2],modes[3]),(modes[0],modes[2]),(modes[1],modes[3]))
    for path in sorted(directory.glob('*/run.json')):
        config=json.loads(path.read_text())
        with (path.parent/'outcomes.csv').open() as f: rows=list(csv.DictReader(f))
        result=summarize(rows,config['duration_ms'])
        result.update({k:config[k] for k in ('scenario','admission','policy','repeat')})
        result['seed']=config.get('seed',42)
        result['measurements']=config.get('measurements',{})
        result['producer_summary']=config.get('producer_summary',{})
        for key in ('generated',*STATUSES):
            if key in result['producer_summary'] and result[key]!=result['producer_summary'][key]:
                raise ValueError('CSV does not match producer summary: '+key)
        group=(result['scenario'],result['seed'],result['repeat'])
        mode=result['admission']+'/'+result['policy']
        if mode in matched[group]: raise ValueError('duplicate scenario/seed/repeat/mode')
        matched[group][mode]=rows
        matched_configs[group][mode]=config
        (path.parent/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
        runs.append(result)
    if not runs: raise ValueError('no measured runs found')
    pairs=[];messages=[]
    for (scenario,seed,repeat),inputs in sorted(matched.items()):
        if set(inputs)!=set(modes): raise ValueError('incomplete four-mode group')
        validation=validate_group([matched_configs[(scenario,seed,repeat)][mode] for mode in modes],environment.get('binary_sha256'))
        for before,after in comparisons:
            pair=compare_pair(inputs[before],inputs[after])
            meta=dict(scenario=scenario,seed=seed,repeat=repeat,reference_mode=before,candidate_mode=after)
            messages.extend(dict(meta,**row) for row in pair.pop('messages'))
            pairs.append(dict(meta,validation=validation,**pair))
    columns=['scenario','seed','repeat','reference_mode','candidate_mode','id','class','reference_status','candidate_status',
             'reference_pre_send_ms','reference_post_send_ms','reference_ms','candidate_pre_send_ms','candidate_post_send_ms','candidate_ms','reduction_ms']
    with (directory/'paired-messages.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns)
        writer.writeheader();writer.writerows(messages)
    aggregates=aggregate(runs)
    for name,value in (('summary.json',runs),('aggregate.json',aggregates),('paired-comparisons.json',pairs)):
        (directory/name).write_text(json.dumps(value,indent=2)+'\n')
    fmt=lambda x:'—' if x is None else f'{x:.2f}'
    seeds=sorted({r['seed'] for r in runs})
    total=sum(r['generated'] for r in runs)
    completed=sum(r['completed'] for r in runs)
    dropped=sum(r['producer_drop'] for r in runs)
    unknown=sum(r['failed_unknown'] for r in runs)
    lines=['# Measured fan-in results','',f'{len(runs)} trials; workload seeds {seeds}. Each run is weighted equally in mean breakdowns. Repeats of a seed are timing repeats, not new workloads.','',
           f'Outcomes: {total} generated; {completed} completed; {dropped} producer drops; {unknown} delivery-unknown outcomes.','',
           'Pre-send includes scheduled-generation lateness, producer queueing, payload preparation and connection setup. Post-send includes transfer, admission/ready-work waiting, sink processing and ACK. It is not an isolated collector-queue measurement.','',
           'Latency statistics describe completed messages. Read completion counts and per-seed variation alongside them. These finite laptop runs do not establish a production capacity or tail SLO.','',
           '## Mean critical-message latency breakdown','',
           '| Scenario | Mode | Critical completed / generated | Pre-send ms | Post-send ms | Total ms | Per-seed mean range ms |',
           '|---|---|---:|---:|---:|---:|---:|']
    for row in aggregates:
        c=row['classes']['critical']
        lines.append(f"| {row['scenario']} | {row['mode']} | {c['completed']}/{c['generated']} | {fmt(c['mean_pre_send_ms'])} | {fmt(c['mean_post_send_ms'])} | {fmt(c['mean_ms'])} | {fmt(c['seed_mean_min_ms'])}–{fmt(c['seed_mean_max_ms'])} |")
    lines.extend(['','![Latency decomposition](latency-breakdown.svg)','','## Matched end-to-end comparisons','',
                  'Inputs match by logical ID, producer, class, bytes and intended relative schedule within each scenario/seed/repeat. All completed pairs are retained; no post-hoc overload filter is used. Completion-status changes are recorded separately. Positive reduction favors the candidate. Percentages compare mean latencies, not mean per-message percentages. Per-seed ranges are descriptive, not confidence intervals.','',
                  '| Scenario | Reference → candidate | Mean critical reduction % | Per-seed reduction range % | Faster critical / completed pairs |',
                  '|---|---|---:|---:|---:|'])
    for scenario in sorted({r['scenario'] for r in runs}):
        for before,after in comparisons:
            group=[p for p in pairs if p['scenario']==scenario and p['reference_mode']==before and p['candidate_mode']==after]
            valid=[p['classes']['critical'] for p in group if p['classes']['critical']['both_completed']]
            if not valid: continue
            old=statistics.mean(c['mean_reference_ms'] for c in valid)
            new=statistics.mean(c['mean_candidate_ms'] for c in valid)
            reduction=(1-new/old)*100 if old else None
            per_seed=[]
            for seed in seeds:
                sample=[p['classes']['critical'] for p in group if p['seed']==seed and p['classes']['critical']['both_completed']]
                if sample:
                    a=statistics.mean(c['mean_reference_ms'] for c in sample)
                    b=statistics.mean(c['mean_candidate_ms'] for c in sample)
                    if a: per_seed.append((1-b/a)*100)
            lines.append(f"| {scenario} | {before} → {after} | {fmt(reduction)} | {fmt(min(per_seed,default=None))}–{fmt(max(per_seed,default=None))} | {sum(c['faster'] for c in valid)}/{sum(c['both_completed'] for c in valid)} |")
    lines.extend(['','Every matched message and interval appears in paired-messages.csv; paired-comparisons.json preserves per-run counts and statistics.','','## Bulk-traffic cost','',
                  '| Scenario | Mode | Bulk completed / generated | Bulk mean ms | Bulk observed maximum ms |', '|---|---|---:|---:|---:|'])
    for row in aggregates:
        c=row['classes']['bulk']
        lines.append(f"| {row['scenario']} | {row['mode']} | {c['completed']}/{c['generated']} | {fmt(c['mean_ms'])} | {fmt(c['max_ms'])} |")
    findings=list(lines)
    lines.extend(['','## Per-run outcomes and observed maxima','',
                  '| Scenario | Seed | Mode | Repeat | Critical n | Critical mean ms | Critical max ms | Drops | Unknown |', '|---|---:|---|---:|---:|---:|---:|---:|---:|'])
    for row in runs:
        c=row['classes']['critical']
        lines.append(f"| {row['scenario']} | {row['seed']} | {row['admission']}/{row['policy']} | {row['repeat']} | {c['completed']}/{c['generated']} | {fmt(c['mean_ms'])} | {fmt(c['max_ms'])} | {row['producer_drop']} | {row['failed_unknown']} |")
    limits=['','## Interpretation and limits','',
            'A large post-send improvement may yield a smaller end-to-end improvement when producer-local head-of-line blocking dominates. Show means, observed maxima, completion counts and bulk cost together.','',
            'Empirical p99/p99.9 remain in JSON. p99_equals_max marks runs where nearest-rank p99 selects the observed maximum; the tables call that observation max. Short samples cannot establish stable tails.','',
            'Sink processing is serialized and non-preemptive. Slowdown and pause settings apply at batch entry; pauses do not model network partitions or durable-backend crashes. OS wake-up delays can extend requested sleeps. Compare datasets only after checking sink-timing behavior, load-window duration and backend settings against the recorded source and executable provenance; CSV format alone does not establish comparability.','',
            'Payload reservations do not cap process RSS or kernel socket buffering. Producer queues hold metadata; payloads are synthesized at send time. failed_unknown may include processing without an observed ACK; it is not known loss or exactly-once delivery.','']
    (directory/'REPORT.md').write_text('\n'.join(lines+limits))
    (directory/'FINDINGS.md').write_text('\n'.join(findings+limits))
    stacked_chart(directory,aggregates)
    return runs

if __name__ == "__main__":
    try:
        result = render(sys.argv[1] if len(sys.argv) > 1 else "results/latest")
        print(f"wrote {len(result)} measured runs and REPORT.md")
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(str(error))
