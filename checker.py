"""Usage: python checker.py PACK_FOLDER. Outputs are written in the working directory."""
import argparse
from pathlib import Path
import sys
from ridgeline.io import load_pack, load_report_context, write_outputs
from ridgeline.gps import audit_gps, apply_supported_time_map
from ridgeline.checks import check_basic
from ridgeline.relationships import check_relationships
from ridgeline.decisions import decide
from ridgeline.report import render_report


def investigate(pack_folder):
    pack=load_pack(pack_folder)
    gps=audit_gps(pack)
    analysis=apply_supported_time_map(pack,gps)
    basic=check_basic(analysis)
    relational=check_relationships(analysis,basic)
    return decide(analysis,gps+basic+relational)


def main():
    parser = argparse.ArgumentParser(description='Offline deterministic weather-network checker')
    parser.add_argument('pack_folder', type=Path)
    args = parser.parse_args()
    try:
        result=investigate(args.pack_folder)
        context=load_report_context(Path.cwd(),result.evidence['input_hashes'],{s['station_id'] for s in result.summary['stations']})
        if context is None:
            result.evidence['diagnostics'].append({'check':'report_context','reason':'Visit recommendation pending: no valid context matching this pack'})
        write_outputs(result,render_report(result,context),Path.cwd())
        print(f'{len(result.summary["stations"])} stations; {len(result.flags)} flags; {len(result.reviews)} review cases. Wrote flags.csv, report.html, review.csv, evidence.json.')
        return 0
    except (ValueError, OSError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
