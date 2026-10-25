"""A self-contained, printable coordinator brief with native evidence disclosure."""
from collections import defaultdict
from dataclasses import asdict
from html import escape
import base64
import io
import json
from .config import CHANNELS

LABELS={'temp_c':'Temp','rh_pct':'Humidity','pressure_hpa':'Pressure','wind_kmh':'Wind','wind_dir_deg':'Direction','rain_mm':'Rain','ghi_wm2':'Sunlight'}


def e(value): return escape(str(value),quote=True)


def figure(plot):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.figure import Figure
    from matplotlib.dates import DateFormatter
    import pandas as pd
    fig=Figure(figsize=(7.2,1.8),dpi=130,facecolor='white');ax=fig.subplots()
    ax.plot(pd.to_datetime(plot['times']),plot['values'],color='#24594e',linewidth=1.2)
    ax.axvspan(pd.Timestamp(plot['start']),min(pd.Timestamp(plot['end']),pd.Timestamp(plot['times'][-1])),color='#ab513b',alpha=.12)
    ax.set_ylabel(plot['channel'],fontsize=8);ax.xaxis.set_major_formatter(DateFormatter('%d %b'))
    ax.tick_params(labelsize=8);ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15)
    fig.tight_layout(pad=.6);stream=io.BytesIO();fig.savefig(stream,format='png',metadata={'Software':'Ridgeline checker'})
    return f'<figure><img alt="{e(plot["caption"])}" src="data:image/png;base64,{base64.b64encode(stream.getvalue()).decode()}"><figcaption>{e(plot["caption"])}</figcaption></figure>'


def render_report(result,context):
    summary=result.summary;stations=summary['stations'];groups=defaultdict(list)
    for flag in result.flags:groups[(flag.station_id,flag.channel,flag.issue,flag.action)].append(flag)
    rows=[]
    for index,s in enumerate(stations):
        cells=[]
        for channel in CHANNELS:
            count=s['channels'][channel]
            status=next((name for name in ('exclude','correct','review') if count[name]),'limited' if count['limited_comparison'] else 'screened')
            symbol={'exclude':'X','correct':'C','review':'R','limited':'L','screened':'S'}[status]
            title=', '.join(f'{key}: {count[key]}' for key in ('exclude','correct','review','screened'))
            cells.append(f'<td class="{status}" title="{e(title)}">{symbol}{" "+str(count[status]) if status in count else ""}</td>')
        metadata=' <span title="Verify installation coordinates">*</span>' if s['metadata_review'] else ''
        rows.append(f'<tr class="{"overflow-station" if index>=15 else ""}"><th scope="row"><strong>{e(s["station_id"])}</strong>{metadata}<small>{e(s["name"])}</small></th>'+''.join(cells)+'</tr>')
    findings=[]
    priority={'clock_error':0,'flatline':1,'sensor_bias':2,'out_of_range':3,'missing_data':4,'duplicate_data':5,'location_mismatch':6,'spike':7}
    for (station,channel,issue,action),flags in sorted(groups.items(),key=lambda item:(priority.get(item[0][2],9),item[0][0]))[:7]:
        start=min(f.start_utc for f in flags);end=max(f.end_utc for f in flags)
        findings.append(f'<li><strong>{e(station)} · {e(channel)}:</strong> {e(issue.replace("_"," "))} — {e(action)}; {e(start)} to {e(end)}'+(f' ({len(flags)} separate intervals)' if len(flags)>1 else '')+'.</li>')
    if not findings:findings=['<li>No supported faults were found by the available checks; review their coverage before use.</li>']
    if context:
        visit=f'<h3>Visit {e(context["station_id"])} first</h3><p><strong>First check:</strong> {e(context["first_check"])}</p><ol>'+''.join(f'<li>{e(t)}</li>' for t in context['tasks'])+f'</ol><p><strong>Why ahead of {e(context["runner_up"])}:</strong> {e(context["reason"])}</p>'
    else:
        visit='<h3>Visit recommendation pending review</h3><p>A matching, reviewed report_context.json is required before dispatch. A stale or invalid recommendation is never reused.</p>'
    panels=[]
    for entry in result.evidence['flags']:
        f=entry['flag'];facts={**entry['quantities'],**{k:v for k,v in entry['evidence'].items() if k not in ('weather_rows','scope_rows','gps_rows')}}
        facts={k:(f'{len(v)} entries; see evidence.json' if isinstance(v,list) and len(v)>12 else v) for k,v in facts.items()}
        panels.append(f'<details><summary>{entry["flag_row"]}. {e(f["station_id"])} / {e(f["channel"])} / {e(f["issue"])} / {e(f["action"])}</summary><p>{e(f["start_utc"])} — {e(f["end_utc"])}</p><p>{e(f["note"])}</p><pre>{e(json.dumps(facts,indent=2,default=str))}</pre></details>')
    reviews=''.join(f'<li><strong>{e(r["station_id"])} / {e(r["channel"])}:</strong> {e(r["reason"])}</li>' for r in result.reviews)
    diagnostics=''.join(f'<li>{e(d.get("station_id","Network"))} {e(d.get("channel",""))}: {e(d["reason"])}</li>' for d in result.evidence['diagnostics'])
    plots=''.join(figure(p) for p in result.evidence.get('plot_data',[])[:2] if p['times'])
    cautions=' '.join(e(c) for c in context.get('cautions',[])) if context else ''
    total=sum(s['channels']['temp_c']['total_observed'] for s in stations)
    missing=sum(s['missing_records'] for s in stations);duplicates=sum(s['duplicate_copies'] for s in stations)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ridgeline | Network health</title>
<style>
:root{{--ink:#202c29;--muted:#52635d;--line:#ccd4ce;--green:#24594e;--paper:#fafbf7}}*{{box-sizing:border-box}}body{{margin:0;background:#e9eee9;color:var(--ink);font:15px/1.45 "Segoe UI",Arial,sans-serif}}main{{max-width:1040px;margin:28px auto;background:var(--paper);padding:36px 42px;border-top:7px solid var(--green)}}.eyebrow{{font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--green);font-weight:700}}h1{{font:36px/1.1 Georgia,serif;margin:12px 0}}h2{{font-size:18px;margin:18px 0 8px}}h3{{font-size:17px;margin:0 0 8px}}p{{margin:8px 0}}.muted,small,figcaption{{color:var(--muted)}}.date{{font-size:13px}}.stats{{display:flex;gap:24px;border-block:1px solid var(--line);padding:10px 0;margin:16px 0;font-size:13px}}table{{border-collapse:collapse;width:100%;font-size:12px}}th,td{{padding:8px 6px;border-bottom:1px solid var(--line);text-align:center}}th:first-child{{text-align:left;width:24%}}thead{{background:#e8eee8}}th small{{display:block;font-weight:400;font-size:10px}}.exclude{{color:#8b321f;font-weight:700;background:#f5e7df}}.correct{{color:#665013;font-weight:700;background:#f4efda}}.review,.limited{{color:#605543;background:#efede6}}.screened{{color:var(--green)}}.legend{{font-size:11px;margin:8px 0}}.columns{{display:grid;grid-template-columns:1fr 1fr;gap:28px}}ul,ol{{margin:8px 0;padding-left:19px}}li{{margin:5px 0}}.visit{{border-left:3px solid var(--green);padding-left:16px}}figure{{margin:12px 0}}figure img{{width:100%;height:auto;display:block}}figcaption{{font-size:10px}}.foot{{border-top:1px solid var(--line);padding-top:10px;margin-top:14px;font-size:11px}}details{{border-top:1px solid var(--line);padding:10px 0}}summary{{cursor:pointer;font-weight:600}}summary:focus-visible,a:focus-visible{{outline:3px solid #9a6519;outline-offset:3px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}}a{{color:var(--green)}}.print-note{{display:none}}
@page{{size:A4;margin:12mm}}@media print{{body{{background:white;font-size:9pt;line-height:1.3}}main{{margin:0;max-width:none;padding:0;border-top-width:4px;background:white}}h1{{font-size:25pt}}h2{{font-size:12pt;margin:12px 0 6px}}h3{{font-size:11pt}}.stats{{margin:10px 0;padding:7px 0;font-size:9pt}}table{{font-size:8pt}}th,td{{padding:5px 4px}}th small{{font-size:7pt}}.columns{{gap:18px}}.screen-only,.overflow-station{{display:none!important}}.print-note{{display:block}}figure{{break-inside:avoid}}figure img{{max-height:38mm;object-fit:contain}}figcaption,.foot,.legend{{font-size:7.5pt}}a{{text-decoration:none}}.visit{{break-inside:avoid}}}}
@media(max-width:700px){{main{{margin:0;padding:20px 14px}}h1{{font-size:29px}}.columns{{grid-template-columns:1fr}}.stats{{gap:12px;flex-wrap:wrap}}.table-wrap{{overflow-x:auto}}table{{min-width:560px}}}}
</style></head><body><main>
<div class="eyebrow">Ridgeline schools weather network · evidence review</div><h1>Use the data selectively.</h1>
<p class="date">{e(summary['start_utc'])} — {e(summary['end_utc'])} UTC · {len(stations)} stations</p>
<p>Leave out intervals marked <strong>X</strong> for the affected channel. Apply <strong>C</strong> corrections first. Resolve <strong>R</strong> and limited comparisons before claiming a complete climate summary.</p>
<div class="stats"><span><strong>{total:,}</strong> observed records after verified deduplication</span><span><strong>{missing:,}</strong> missing records</span><span><strong>{duplicates:,}</strong> duplicate copies</span></div>
<h2>What can be used?</h2><div class="table-wrap"><table><thead><tr><th scope="col">Station</th>{''.join(f'<th scope="col">{e(LABELS[c])}</th>' for c in CHANNELS)}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="legend">S: screened · X: exclude · C: correct first · R: review · L: insufficient comparison evidence · * verify coordinates. Counts refer to affected observed values; a row can contain mixed intervals.</p>
{f'<p class="print-note">{len(stations)-15} further station rows appear in the screen version.</p>' if len(stations)>15 else ''}
<div class="columns"><section><h2>Decisions that matter</h2><ul>{''.join(findings)}</ul></section><section><h2>One technician · one hour</h2><div class="visit">{visit}</div></section></div>
{plots}<p class="foot">{e(summary['meaning'])}. {summary['review_events']} unresolved review intervals; full evidence and disabled checks are available on screen. {cautions} All timestamps are UTC; clock instructions refer to source rows and original logger labels.</p>
<section class="screen-only"><h2>Inspect the evidence</h2><p><a href="flags.csv" download>Download flags.csv</a> · <a href="review.csv">Review cases</a> · <a href="evidence.json">Audit evidence</a></p>
<details><summary>Final flags ({len(result.flags)})</summary>{''.join(panels) or '<p>No final flags.</p>'}</details><details><summary>Unresolved cases ({len(result.reviews)})</summary><ul>{reviews or '<li>None recorded.</li>'}</ul></details><details><summary>Coverage and disabled checks</summary><ul>{diagnostics or '<li>No disabled checks recorded.</li>'}</ul></details></section>
</main></body></html>'''
