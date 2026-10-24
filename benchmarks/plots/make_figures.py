"""Render README figures as dependency-free SVG from committed result data; no model calls.

Inputs: benchmarks/fault-injection/results.json, qualification/argon-offline-repeatability.json,
and the live JSON receipts of the two offline test suites. Outputs go to docs/figures/.

Usage: make_figures.py [--check] [OUTPUT_DIR]
  --check  regenerate in memory and fail if any committed figure differs (no files written)
"""
import json
from pathlib import Path
import subprocess
import sys
from xml.sax.saxutils import escape

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT = ROOT / "docs/figures"
FONT = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

# Roles for the reference palette: blue = slot 1, amber = fixed warning status colour.
STYLE = f"""
svg {{ --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --grid:#dcdbd6; --accent:#2a78d6;
  --on-accent:#ffffff; --warn:#fab219; --on-warn:#0b0b0b; --neutral:#ecebe7; --tile:#f3f2ee; }}
@media (prefers-color-scheme: dark) {{
  svg {{ --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --grid:#3a3a37; --accent:#3987e5;
    --on-accent:#0b0b0b; --warn:#fab219; --on-warn:#0b0b0b; --neutral:#2a2a28; --tile:#232321; }}
}}
text {{ font-family:{FONT}; fill:var(--ink); }}
.mono {{ font-family:{MONO}; }}
.muted {{ fill:var(--ink2); }}
.title {{ font-size:20px; font-weight:600; }}
.sub {{ font-size:13px; }}
.lab {{ font-size:13px; }}
.small {{ font-size:11.5px; }}
.big {{ font-size:30px; font-weight:650; }}
.head {{ font-size:12px; font-weight:600; }}
"""


def t(x, y, text, cls="lab", anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}"{extra}>'
            f'{escape(str(text))}</text>')


def fits(text, size, width, label):
    """Fail loudly instead of drawing clipped or overlapping labels."""
    if len(str(text)) * size * 0.58 > width:
        raise ValueError(f"LABEL_TOO_WIDE:{label}:{text}")


def wrap(text, limit):
    lines, line = [], ""
    for word in str(text).split():
        if line and len(line) + 1 + len(word) > limit:
            lines.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    return lines + ([line] if line else [])


def document(width, height, title, description, body, extra=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" role="img" aria-labelledby="t d">\n'
            f'<title id="t">{escape(title)}</title><desc id="d">{escape(description)}</desc>\n'
            f'<style>{STYLE}{extra}</style>\n'
            f'<rect width="{width}" height="{height}" rx="10" fill="var(--surface)"/>\n'
            + "\n".join(body) + "\n</svg>\n")


def check_mark(cx, cy):
    return (f'<polyline points="{cx-7},{cy} {cx-2},{cy+5} {cx+8},{cy-6}" fill="none" '
            f'stroke="var(--on-accent)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>')


def bang_mark(cx, cy):
    return (f'<line x1="{cx}" y1="{cy-7}" x2="{cx}" y2="{cy+1}" stroke="var(--on-warn)" '
            f'stroke-width="2.8" stroke-linecap="round"/>'
            f'<circle cx="{cx}" cy="{cy+6}" r="1.8" fill="var(--on-warn)"/>')


def dash_mark(cx, cy):
    return (f'<line x1="{cx-6}" y1="{cy}" x2="{cx+6}" y2="{cy}" stroke="var(--ink2)" '
            f'stroke-width="2.2" stroke-linecap="round"/>')


GATES = [("PIN_AND_PATH", "Pin &", "path"), ("STRICT_PARSING", "Strict", "parsing"),
         ("LEDGER_SCHEMA", "Ledger", "schema"), ("LINE_AND_QUOTE", "Line &", "quote")]


def fault_matrix(results):
    faults = results["faults"]
    summary = results["summary"]
    width, left, row_h, label_w, col_w = 900, 24, 38, 420, 64
    escape_x = left + label_w + col_w * len(GATES)
    manual_x = escape_x + 88
    top = 118
    height = top + 56 + row_h * len(faults) + 66
    body = [t(left, 36, "Fault injection: what the citation checker catches, and what it cannot", "title"),
            t(left, 58, f"{summary['mechanicalStopped']} of {summary['mechanicalFaults']} mechanical faults stopped with the expected reason · "
                        f"{summary['semanticPassedThroughToManualCheck']} of {summary['semanticFaults']} semantic faults pass through · "
                        f"{summary['notExercised']} checks not exercised", "sub muted"),
            t(left, 78, "Each row is a single fault applied to a valid baseline, run through the real manual_citations.py. "
                        "No model or provider is called.", "sub muted")]
    head_y = top + 8
    for i, (_, a, b) in enumerate(GATES):
        cx = left + label_w + col_w * i + col_w / 2
        body += [t(cx, head_y, a, "head", "middle"), t(cx, head_y + 15, b, "head", "middle")]
    body += [t(escape_x + 44, head_y, "Passes", "head", "middle"), t(escape_x + 44, head_y + 15, "script", "head", "middle"),
             t(manual_x + 44, head_y, "Not", "head", "middle"), t(manual_x + 44, head_y + 15, "exercised", "head", "middle")]
    y = top + 30
    body.append(f'<line x1="{left}" y1="{y}" x2="{width-left}" y2="{y}" stroke="var(--grid)"/>')
    for fault in faults:
        y0 = y
        fits(fault["description"], 13, label_w - 12, fault["id"])
        second = (fault["observedReason"] or
                  ("CITATIONS_MATCHED, so the script accepts it" if fault["kind"] == "SEMANTIC" else fault["owner"]))
        fits(second, 11.5, label_w - 12, fault["id"] + ":second")
        body.append(t(left, y0 + 17, fault["description"], "lab"))
        body.append(t(left, y0 + 32, second, "small muted mono" if fault["observedReason"] else "small muted"))
        cy = y0 + row_h / 2
        if fault["kind"] == "MECHANICAL":
            for i, (layer, _, _) in enumerate(GATES):
                if fault["layer"] == layer:
                    cx = left + label_w + col_w * i + col_w / 2
                    body.append(f'<rect x="{cx-20}" y="{cy-12}" width="40" height="24" rx="4" fill="var(--accent)"/>')
                    body.append(check_mark(cx, cy))
        elif fault["kind"] == "SEMANTIC":
            cx = escape_x + 44
            body.append(f'<rect x="{cx-20}" y="{cy-12}" width="40" height="24" rx="4" fill="var(--warn)" '
                        f'stroke="var(--ink2)" stroke-width="1.2"/>')
            body.append(bang_mark(cx, cy))
        else:
            cx = manual_x + 44
            body.append(f'<rect x="{cx-20}" y="{cy-12}" width="40" height="24" rx="4" fill="var(--neutral)" '
                        f'stroke="var(--ink2)" stroke-width="1" stroke-dasharray="3 3"/>')
            body.append(dash_mark(cx, cy))
        y += row_h
        body.append(f'<line x1="{left}" y1="{y}" x2="{width-left}" y2="{y}" stroke="var(--grid)" stroke-opacity="0.6"/>')
    ly = y + 30
    body += [f'<rect x="{left}" y="{ly-13}" width="30" height="20" rx="4" fill="var(--accent)"/>', check_mark(left + 15, ly - 3),
             t(left + 40, ly + 2, "Stopped by this gate", "small"),
             f'<rect x="{left+190}" y="{ly-13}" width="30" height="20" rx="4" fill="var(--warn)" stroke="var(--ink2)" stroke-width="1.2"/>',
             bang_mark(left + 205, ly - 3),
             t(left + 230, ly + 2, "Script accepts it; Codex must check the premise", "small"),
             f'<rect x="{left+535}" y="{ly-13}" width="30" height="20" rx="4" fill="var(--neutral)" stroke="var(--ink2)" stroke-dasharray="3 3"/>',
             dash_mark(left + 550, ly - 3),
             t(left + 575, ly + 2, "Not scored: no script in the manual route", "small"),
             t(left, ly + 26, "A matching quotation proves text placement, not that a claim is true. Rows marked ! are documented limits, not failures.", "small muted")]
    return document(width, height, "Fault injection against the citation checker",
                    f"{summary['mechanicalStopped']} of {summary['mechanicalFaults']} mechanical faults stopped; "
                    f"{summary['semanticPassedThroughToManualCheck']} semantic faults pass through to manual review; "
                    f"{summary['notExercised']} checks not exercised.", body)


def evidence_overview(inputs):
    width, left = 900, 24
    tiles = [
        (str(inputs["utilityChecks"]), f"checks across {inputs['utilityCases']} failure modes"),
        (str(inputs["citationScenarios"]), "citation scenarios, LF and Unicode CRLF"),
        (f"{inputs['mechanicalStopped']}/{inputs['mechanicalFaults']}", "injected faults stopped by the checker"),
        (f"{inputs['argonTotal']:,}", f"Argon controls: {inputs['argonRuns']} fresh runs of {inputs['argonPerRun']}"),
        ("0", "provider calls, 0 qualification credit"),
    ]
    gap = 12
    tile_w = (width - 2 * left - gap * (len(tiles) - 1)) / len(tiles)
    body = [t(left, 36, "Offline evidence: deterministic checks, zero model calls", "title"),
            t(left, 58, "Synthetic fixtures and process doubles. This is repeatability evidence for the gates, "
                        "not native containment or model-quality evidence.", "sub muted")]
    for i, (value, label) in enumerate(tiles):
        x = left + i * (tile_w + gap)
        body.append(f'<rect x="{x:.1f}" y="82" width="{tile_w:.1f}" height="92" rx="8" fill="var(--tile)" stroke="var(--grid)"/>')
        body.append(t(f"{x + 14:.1f}", 122, value, "big"))
        for j, line in enumerate(wrap(label, 22)[:2]):
            body.append(t(f"{x + 14:.1f}", 143 + 15 * j, line, "small muted"))
    suites = sorted(inputs["argonSuites"], key=lambda s: (-s[1], s[0]))
    top, bar_h, pitch, label_w = 228, 18, 30, 180
    body.append(t(left, 208, f"Argon offline controls by suite ({inputs['argonPerRun']} per run, 2 fresh runs)", "lab", extra=' font-weight="600"'))
    scale = (width - 2 * left - label_w - 70) / max(c for _, c in suites)
    for i, (name, count) in enumerate(suites):
        y = top + i * pitch
        body.append(t(left, y + 13, name, "small mono"))
        w = max(count * scale, 3)
        body.append(f'<path d="M{left+label_w},{y} h{w-4:.1f} a4,4 0 0 1 4,4 v{bar_h-8} a4,4 0 0 1 -4,4 h-{w-4:.1f} z" fill="var(--accent)"/>')
        body.append(t(f"{left + label_w + w + 8:.1f}", y + 13, count, "small"))
    height = top + len(suites) * pitch + 24
    return document(width, height, "Offline evidence overview",
                    f"{inputs['utilityChecks']} utility checks, {inputs['citationScenarios']} citation scenarios, "
                    f"{inputs['mechanicalStopped']} of {inputs['mechanicalFaults']} injected faults stopped, "
                    f"{inputs['argonTotal']} Argon controls, 0 provider calls.", body)


VERDICT = {"NO_BLOCKERS_FOUND": ("Clean", "#cde2fb", "#0b0b0b"),
           "CHANGES_RECOMMENDED": ("Changes", "#6da7ec", "#0b0b0b"),
           "BLOCKERS_FOUND": ("Blockers", "#184f95", "#ffffff")}
SEVERITY = {"NO_BLOCKERS_FOUND": 0, "CHANGES_RECOMMENDED": 1, "BLOCKERS_FOUND": 2}
FAMILY_LABEL = {"absent_vs_null": "Absent vs null", "caller_callee": "Caller / callee",
                "output_bytes": "Output byte limit", "ownership_authorization": "Ownership / authorization",
                "required_coverage": "Required coverage", "runtime_budget": "Runtime budget evidence"}


def pair_matrix(pilot):
    """Reviewer verdict per case: sound plan beside its changed twin, for every family, wording and trial.

    Optional pilot keys (defaults reproduce the pilot 1 figure): families, subLabels, flagNote, pairs, title,
    subtitle3, footer (list of (text, css class)), desc.
    """
    rows = pilot["rows"]
    invalid = set(pilot.get("invalidFamilies", []))
    families = list(pilot.get("families", FAMILY_LABEL))
    labels = pilot.get("families", FAMILY_LABEL)
    sub_labels = pilot.get("subLabels", {})
    flag_note = pilot.get("flagNote", "corpus defect: see adjudication")
    cells = {}
    for family in families:
        for wording in ("A", "B"):
            for role in ("sound", "changed"):
                for trial in (1, 2):
                    cells[(family, wording, role, trial)] = rows[(family, wording, role, trial)]
    width, left, row_h, label_w, cell_w, gap = 900, 24, 32, 230, 76, 8
    cols = [("sound", 1), ("sound", 2), ("changed", 1), ("changed", 2)]
    col_x = [left + label_w + i * (cell_w + gap) + (24 if i >= 2 else 0) for i in range(4)]
    note_x = col_x[3] + cell_w + 22
    top = 132
    ordinal_ok = sum(SEVERITY[cells[(f, w, "changed", t)]] > SEVERITY[cells[(f, w, "sound", t)]]
                     for f in families if f not in invalid for w in ("A", "B") for t in (1, 2))
    ordinal_n = sum(1 for f in families if f not in invalid for _ in range(4))
    footer = pilot.get("footer") or [
        (f"Ordinal reading, five valid families: the changed twin was judged strictly more severely than its sound twin in {ordinal_ok} of {ordinal_n} pair-observations.", "small"),
        ("The runtime-budget twin has no measured throughput, so Changes (uncertainty) is the correct verdict there, not Blockers.", "small muted"),
        ("Dashed cells: the Output byte limit family is excluded because its sound plan and its twin were both flawed in ways the reviewer correctly described.", "small muted")]
    height = top + len(families) * (row_h * 2 + 14) + 64 + 18 * len(footer)
    pairs = pilot.get("pairs", 12)
    body = [t(left, 36, pilot.get("title", "Sound plans and their changed twins: reviewer verdicts"), "title"),
            t(left, 58, pilot.get("subtitle2") or f"Route claude-cli, model {pilot['model']}, effort {pilot['effort']}; {len(families) * 4} cases, 2 trials, 0 technical stops, 0 unsupported VERIFIED findings.", "sub muted"),
            t(left, 78, pilot.get("subtitle3") or f"Pre-registered strict score, pairs discriminated: {pilot['strict'][0]}/{pairs} and {pilot['strict'][1]}/{pairs}. Post-hoc adjudication in the write-up.", "sub muted")]
    for group, first in (("Sound plan", 0), ("Changed twin", 2)):
        centre = (col_x[first] + col_x[first + 1] + cell_w) / 2
        fits(group, 12, 2 * cell_w + gap, group)
        body.append(t(centre, top - 26, group, "head", "middle"))
    for (role, trial), x in zip(cols, col_x):
        body.append(t(x + cell_w / 2, top - 10, f"trial {trial}", "small muted", "middle"))
    y = top
    for family in families:
        flagged = family in invalid
        fits(labels[family], 13, label_w - 40, family)
        body.append(t(left, y + 20, labels[family], "lab", extra=' font-weight="600"'))
        if flagged:
            fits(flag_note, 11.5, label_w - 20, family + ":flag")
            body.append(t(left, y + 38, flag_note, "small muted"))
        elif family in sub_labels:
            body.append(t(left, y + 38, sub_labels[family], "small muted"))
        for w_index, wording in enumerate(("A", "B")):
            yy = y + w_index * row_h
            body.append(t(left + label_w - 18, yy + 20, wording, "small muted", "end"))
            for (role, trial), x in zip(cols, col_x):
                verdict = cells[(family, wording, role, trial)]
                label, fill, ink = VERDICT[verdict]
                label += "*" if (family, wording, role, trial) in pilot.get("marks", ()) else ""
                body.append(f'<rect x="{x}" y="{yy + 3}" width="{cell_w}" height="{row_h - 6}" rx="4" fill="{fill}"'
                            f'{" stroke=\"var(--ink2)\" stroke-dasharray=\"3 3\"" if flagged else ""}/>')
                body.append(f'<text x="{x + cell_w / 2}" y="{yy + 21}" class="small" text-anchor="middle" fill="{ink}" style="fill:{ink}">{label}</text>')
        ok = sum(SEVERITY[cells[(family, w, "changed", t_)]] > SEVERITY[cells[(family, w, "sound", t_)]] for w in ("A", "B") for t_ in (1, 2))
        body.append(t(note_x, y + 20, f"{ok}/4 judged stricter", "small muted"))
        y += row_h * 2 + 14
        body.append(f'<line x1="{left}" y1="{y - 7}" x2="{width - left}" y2="{y - 7}" stroke="var(--grid)" stroke-opacity="0.6"/>')
    ly = y + 16
    for i, verdict in enumerate(("NO_BLOCKERS_FOUND", "CHANGES_RECOMMENDED", "BLOCKERS_FOUND")):
        label, fill, ink = VERDICT[verdict]
        x = left + i * 250
        text = {"NO_BLOCKERS_FOUND": "Clean: no blockers found", "CHANGES_RECOMMENDED": "Changes recommended",
                "BLOCKERS_FOUND": "Blockers found"}[verdict]
        fits(text, 11.5, 200, text)
        body.append(f'<rect x="{x}" y="{ly}" width="26" height="16" rx="3" fill="{fill}"/>')
        body.append(t(x + 34, ly + 12, text, "small"))
    for i, (text, css) in enumerate(footer):
        body.append(t(left, ly + 40 + 18 * i, text, css))
    return document(width, height, "Reviewer verdicts on sound plans and their changed twins",
                    pilot.get("desc") or (f"Per-case verdicts from {pilot['model']} through the Claude CLI across 6 families, 2 wordings and 2 trials; "
                                          f"five valid families judged the changed twin more severely in {ordinal_ok} of {ordinal_n} pair-observations."), body)


def run_receipt(script):
    done = subprocess.run([sys.executable, "-B", "-I", str(ROOT / script)], capture_output=True, text=True,
                          timeout=300, check=False)
    lines = [ln for ln in done.stdout.splitlines() if ln.strip()]
    if done.returncode != 0 or not lines:
        raise SystemExit("TEST_FAILED:" + script)
    return json.loads(lines[-1])


def collect_inputs():
    results = json.loads((ROOT / "benchmarks/fault-injection/results.json").read_bytes())
    argon = json.loads((ROOT / "qualification/argon-offline-repeatability.json").read_bytes())
    utility = run_receipt("tools/test_demonstrated_utility.py")
    citations = run_receipt("skills/antigravity-preflight/scripts/test_manual_citations.py")
    if utility.get("status") != "PASS" or utility.get("providerCalls") != 0 or citations.get("providerCalls") != 0:
        raise SystemExit("UNEXPECTED_RECEIPT")
    if argon["status"] != "PASS" or argon["providerCalls"] != 0:
        raise SystemExit("UNEXPECTED_QUALIFICATION")
    summary = results["summary"]
    return {
        "results": results,
        "utilityChecks": utility["checks"], "utilityCases": utility["cases"],
        "citationScenarios": citations["scenarios"],
        "mechanicalStopped": summary["mechanicalStopped"], "mechanicalFaults": summary["mechanicalFaults"],
        "argonTotal": argon["totalCases"], "argonRuns": len(argon["runs"]), "argonPerRun": argon["casesPerRun"],
        "argonSuites": [(s["suite"], s["cases"]) for s in argon["runs"][0]["suites"]],
        "pilot": load_pilot(),
        "pilot2": load_pilot2(),
        "ablation": load_ablation(),
        "threeArms": load_three_arms(),
        "fourArms": load_four_arms(),
        "flash": load_flash(),
        "routes": load_routes(),
        "v3Gemini": load_v3_gemini(),
        "v3Arms": load_v3_arms(),
    }


def load_pilot():
    """Verdicts from the committed pilot ledgers, mapped to family/wording/role through the oracle."""
    base = ROOT / "benchmarks/counterfactual-pairs"
    results = base / "results/pilot1-claude-opus-5-5-high"
    if not results.is_dir():
        return None
    oracle = {c["case"]: c for c in json.loads((base / "oracle/oracle.json").read_bytes())["cases"]}
    rows, model, effort = {}, set(), set()
    for trial in (1, 2):
        for line in (results / f"trial{trial}/responses.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            truth = oracle[row["case"]]
            if row.get("technicalStop"):
                raise SystemExit("PILOT_HAS_STOPS")
            rows[(truth["family"], truth["wording"], truth["role"], trial)] = row["assessment"]
            model.add(row["requestedModel"])
            effort.add(row["effort"])
    if len(rows) != 48 or len(model) != 1 or len(effort) != 1:
        raise SystemExit("PILOT_INCOMPLETE_OR_MIXED")
    score = json.loads((results / "score.json").read_bytes())["trials"]
    strict = [score[str(t_)]["pairDiscrimination"]["count"] for t_ in (1, 2)]
    if any(score[str(t_)]["pairDiscrimination"]["of"] != 12 for t_ in (1, 2)):
        raise SystemExit("PILOT_SCORE_MISMATCH")
    return {"rows": rows, "model": model.pop(), "effort": effort.pop(), "strict": strict,
            "invalidFamilies": ["output_bytes"]}


GEMINI_RESULTS = ROOT / "benchmarks/counterfactual-pairs/results/pilot-flash-high"


def _flash_rows(ledger):
    return {t: [json.loads(line) for line in (GEMINI_RESULTS / f"trial{t}/{ledger}").read_text(encoding="utf-8").splitlines() if line.strip()] for t in (1, 2)}


def load_flash():
    """The Gemini 3.8 Flash High pilot on corpus v1, in the documented-rule view (four format stops re-read), from committed ledgers."""
    if not GEMINI_RESULTS.is_dir():
        return None
    base = ROOT / "benchmarks/counterfactual-pairs"
    oracle = {c["case"]: c for c in json.loads((base / "oracle/oracle.json").read_bytes())["cases"]}
    as_run, doc = _flash_rows("responses.jsonl"), _flash_rows("responses-documented-rule.jsonl")
    identity = json.loads((GEMINI_RESULTS / "orchestrator-reported-identity.json").read_bytes())
    rows, marks = {}, set()
    for trial in (1, 2):
        for row in doc[trial]:
            truth = oracle[row["case"]]
            if row.get("technicalStop"):
                raise SystemExit("FLASH_DOCUMENTED_RULE_HAS_STOPS")
            key = (truth["family"], truth["wording"], truth["role"], trial)
            rows[key] = row["assessment"]
            if row.get("reparsedFrom"):
                marks.add(key)
    stops = sum(1 for t in (1, 2) for r in as_run[t] if r.get("technicalStop"))
    score = json.loads((GEMINI_RESULTS / "score-documented-rule.json").read_bytes())["trials"]
    as_run_score = json.loads((GEMINI_RESULTS / "score-as-run.json").read_bytes())["trials"]
    strict = [score[str(t_)]["pairDiscrimination"]["count"] for t_ in (1, 2)]
    if len(rows) != 48 or len(marks) != stops or any(score[str(t_)]["pairDiscrimination"]["of"] != 12 for t_ in (1, 2)):
        raise SystemExit("FLASH_SCORE_MISMATCH")
    ordinal = sum(SEVERITY[rows[(f, w, "changed", t_)]] > SEVERITY[rows[(f, w, "sound", t_)]]
                  for f in FAMILY_LABEL if f != "output_bytes" for w in ("A", "B") for t_ in (1, 2))
    as_run_strict = [(as_run_score[str(t_)]["pairDiscrimination"]["count"], as_run_score[str(t_)]["pairDiscrimination"]["of"]) for t_ in (1, 2)]
    return {"rows": rows, "model": identity["requestedModel"], "effort": identity["effort"], "strict": strict, "invalidFamilies": ["output_bytes"],
            "marks": marks, "stops": stops, "ordinal": ordinal, "asRunStrict": as_run_strict}


V2_LABEL = {"absent_vs_null": "Absent vs null", "required_coverage": "Required coverage", "caller_callee": "Caller / callee",
            "deadline_arithmetic": "Deadline arithmetic", "migration_order": "Migration order", "output_bytes": "Output byte limit",
            "ownership_authorization": "Ownership / authorization", "permission_chain": "Permission chain",
            "unit_mismatch": "Unit mismatch", "runtime_budget": "Runtime budget evidence"}
V2_DIFFICULTY = {"direct": 0, "inference": 1, "evidence_gap": 2}
V2_DIFFICULTY_TEXT = {"direct": "direct contradiction", "inference": "needs inference across lines",
                      "evidence_gap": "uncertainty, not a defect"}


def load_pilot2():
    """Verdicts, scores and the adjudication for pilot 2, all read from committed files."""
    base = ROOT / "benchmarks/counterfactual-pairs"
    results = base / "results/pilot2-v2-claude-opus-5-5-high"
    if not results.is_dir():
        return None
    oracle = {c["case"]: c for c in json.loads((base / "v2/oracle/oracle.json").read_bytes())["cases"]}
    rows, model, effort = {}, set(), set()
    for trial in (1, 2):
        for line in (results / f"trial{trial}/responses.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("technicalStop"):
                raise SystemExit("PILOT2_HAS_STOPS")
            truth = oracle[row["case"]]
            rows[(truth["family"], truth["wording"], truth["role"], trial)] = row["assessment"]
            model.add(row["requestedModel"])
            effort.add(row["effort"])
    if len(rows) != 80 or len(model) != 1 or len(effort) != 1:
        raise SystemExit("PILOT2_INCOMPLETE_OR_MIXED")
    model_name, effort_name = model.pop(), effort.pop()
    result = json.loads((results / "score.json").read_bytes())
    adjudication = json.loads((results / "adjudication.json").read_bytes())
    invalid = sorted({entry["family"] for entry in adjudication["invalidPairs"]})
    trials = [result["trials"][str(t_)] for t_ in (1, 2)]
    adjusted = [result["adjusted"]["trials"][str(t_)] for t_ in (1, 2)]
    if any(t_["pairOrderedCalibrated"]["of"] != 20 for t_ in trials):
        raise SystemExit("PILOT2_SCORE_MISMATCH")
    family_difficulty = {c["family"]: c["difficulty"] for c in oracle.values()}
    families = {f: V2_LABEL[f] for f in sorted(V2_LABEL, key=lambda f: (V2_DIFFICULTY[family_difficulty[f]], V2_LABEL[f]))}
    inference_n = sum(1 for d in family_difficulty.values() if d == "inference")
    o = [t_["pairOrderedCalibrated"]["count"] for t_ in trials]
    a = [t_["pairOrderedCalibrated"]["count"] for t_ in adjusted]
    an = adjusted[0]["pairOrderedCalibrated"]["of"]
    st = [t_["pairDiscrimination"]["count"] for t_ in trials]
    h = [t_["hedgedOnSoundPlans"]["count"] for t_ in trials]
    blocked = sum(t_["falseBlockersOnSoundPlans"]["count"] for t_ in trials)
    blocked_text = "none was blocked" if blocked == 0 else f"{blocked} were blocked"
    flagged_family = ", ".join(V2_LABEL[f] for f in invalid)
    return {
        "rows": rows, "model": model_name, "effort": effort_name, "invalidFamilies": invalid, "families": families,
        "subLabels": {f: V2_DIFFICULTY_TEXT[family_difficulty[f]] for f in families},
        "flagNote": "adjudicated gap in sound plan",
        "title": "Corpus v2: reviewer verdicts on sound plans and their changed twins",
        "subtitle3": f"Preregistered before the run: ten families, {inference_n} needing inference across lines.",
        "desc": (f"Per-case verdicts from {model_name} through the Claude CLI on corpus v2 across 10 families, 2 wordings and 2 trials; "
                 f"preregistered ordinal pair discrimination {o[0]} of 20 and {o[1]} of 20."),
        "footer": [
            (f"Primary (preregistered ordinal): {o[0]}/20 and {o[1]}/20 pairs; {a[0]}/{an} and {a[1]}/{an} excluding the adjudicated pair.", "small"),
            (f"Strict (sound plan fully clean): {st[0]}/20 and {st[1]}/20, because {h[0]}/20 and {h[1]}/20 sound plans were hedged; {blocked_text}.", "small"),
            ("The runtime-budget twin has no measured throughput, so Changes (uncertainty) is the correct verdict there, not Blockers.", "small muted"),
            (f"Dashed cells ({flagged_family}): the sound plan's tests omit main(), so its hedging is warranted by the text; adjudicated after the run.", "small muted")],
    }


ABLATION_CSS = """
svg { --skill:#2a78d6; --bare:#eb6834; }
@media (prefers-color-scheme: dark) { svg { --skill:#3987e5; --bare:#d95926; } }
"""
VERDICT_ORDER = ("NO_BLOCKERS_FOUND", "CHANGES_RECOMMENDED", "BLOCKERS_FOUND")


def load_ablation():
    """Both arms' verdicts, recomputed from committed ledgers and checked against the committed analysis."""
    base = ROOT / "benchmarks/counterfactual-pairs"
    results = base / "results/ablation-bare-opus-5-5-high"
    if not results.is_dir():
        return None
    oracle = {c["case"]: c for c in json.loads((base / "v2/oracle/oracle.json").read_bytes())["cases"]}
    analysis = json.loads((results / "analysis.json").read_bytes())
    human = json.loads((results / "human-reading.json").read_bytes())
    arms = {"skill": base / "results/pilot2-v2-claude-opus-5-5-high", "bare": results}
    mix, units = {}, {}
    for arm, directory in arms.items():
        severity, mix[arm] = {}, {"sound": dict.fromkeys(VERDICT_ORDER, 0), "defect": dict.fromkeys(VERDICT_ORDER, 0), "stops": 0}
        for trial in (1, 2):
            for line in (directory / f"trial{trial}/responses.jsonl").read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                if row.get("technicalStop"):
                    mix[arm]["stops"] += 1
                    continue
                truth = oracle[row["case"]]
                severity[(truth["family"], truth["wording"], trial, truth["role"])] = (VERDICT_ORDER.index(row["assessment"]), truth["expectedClass"])
                group = "sound" if truth["role"] == "sound" else "defect" if truth["expectedClass"] == "DEFECT" else None
                if group:
                    mix[arm][group][row["assessment"]] += 1
        counted = {}
        for (family, wording, trial, role), (value, klass) in severity.items():
            if role == "sound" and (family, wording, trial, "changed") in severity:
                twin, twin_class = severity[(family, wording, trial, "changed")]
                counted[(family, wording, trial)] = twin > value and not (twin_class == "UNCERTAIN" and twin == 2)
        units[arm] = counted
    for arm in arms:
        expected = analysis["allPairs"]["primaryOrdinalPairDiscrimination"][arm]
        if (sum(units[arm].values()), len(units[arm])) != (expected["count"], expected["of"]):
            raise SystemExit("ABLATION_ANALYSIS_STALE:" + arm)
    families = sorted({f for f, _, _ in units["skill"]})
    per_family = {f: {arm: sum(v for (fam, _, _), v in units[arm].items() if fam == f) for arm in arms} for f in families}
    for f in families:  # pairs a stop removed: four are expected per family (2 wordings x 2 trials)
        for arm in arms:
            per_family[f][arm + "Lost"] = 4 - sum(1 for (fam, _, _) in units[arm] if fam == f)
    rows = human["missedDefectTwins"]["classification"]
    paired = analysis["allPairs"]["primaryPaired"]
    return {"mix": mix, "perFamily": per_family, "primary": analysis["allPairs"]["primaryOrdinalPairDiscrimination"],
            "paired": paired, "named": sum(r["namesPlantedMechanism"] for r in rows), "missed": len(rows),
            "blockingWording": sum(r["blockingOrCriticalWording"] for r in rows),
            "model": analysis["arms"]["bare"]["stamps"][0][0], "cost": analysis["arms"]["bare"]["costUsd"]}


def ablation_figure(data):
    width, left = 900, 24
    mix, per_family, paired = data["mix"], data["perFamily"], data["paired"]
    p_text = "p < 0.0001" if paired["exactTwoSidedSignTestP"] < 0.0001 else f"p = {paired['exactTwoSidedSignTestP']}"
    sound_bare, defect_bare = mix["bare"]["sound"], mix["bare"]["defect"]
    n_sound, n_defect = sum(sound_bare.values()), sum(defect_bare.values())
    body = [t(left, 36, "Bare prompt against skill-style prompt: same model, same 40 plans", "title"),
            t(left, 58, f"{data['model']} through the Claude CLI, 2 trials per arm. The skill-style arm is pilot 2, run earlier, not concurrently.", "sub muted"),
            t(left, 78, "Preregistered ablation: a bundle of prompt and packet changes, not any single component.", "sub muted"),
            t(left, 116, "A. Verdicts given", "lab", extra=' font-weight="600"')]
    bar_x, bar_w, row_y = 210, 520, 134
    for group, label in (("sound", "Sound plans"), ("defect", "Defect twins")):
        body.append(t(left, row_y + 15, label, "head"))
        row_y += 22
        for arm, name in (("skill", "Skill-style"), ("bare", "Bare")):
            counts = mix[arm][group]
            n = sum(counts.values())
            body.append(t(left + 12, row_y + 17, f"{name} (n={n})", "small"))
            x = bar_x
            for verdict in VERDICT_ORDER:
                value = counts[verdict]
                if not value:
                    continue
                seg = bar_w * value / n
                label, fill, ink = VERDICT[verdict]
                body.append(f'<rect x="{x:.1f}" y="{row_y}" width="{seg:.1f}" height="24" fill="{fill}" stroke="var(--surface)" stroke-width="2"/>')
                if seg >= 46:
                    body.append(f'<text x="{x + seg / 2:.1f}" y="{row_y + 16}" class="small" text-anchor="middle" fill="{ink}" style="fill:{ink}">{label} {value}</text>')
                x += seg
            row_y += 32
        row_y += 6
    lx = bar_x
    for i, verdict in enumerate(VERDICT_ORDER):
        label, fill, ink = VERDICT[verdict]
        text = {"NO_BLOCKERS_FOUND": "Clean (GO)", "CHANGES_RECOMMENDED": "Changes (GO_WITH_CHANGES)", "BLOCKERS_FOUND": "Blockers (NO_GO)"}[verdict]
        body.append(f'<rect x="{lx}" y="{row_y}" width="22" height="14" rx="3" fill="{fill}"/>')
        body.append(t(lx + 30, row_y + 11, text, "small"))
        lx += 30 + len(text) * 6.6 + 24
    row_y += 44
    body.append(t(left, row_y, "B. Pairs where the changed twin was judged more severely than its sound twin", "lab", extra=' font-weight="600"'))
    body.append(t(left, row_y + 18, "Out of 4 per family (2 wordings x 2 trials). A dashed line spans pairs that a stop removed. Sorted by the best-case gap.", "small muted"))
    track_x, unit = 250, 84
    order = sorted(per_family, key=lambda f: (per_family[f]["bare"] + per_family[f]["bareLost"] - per_family[f]["skill"], V2_LABEL.get(f, f)))
    top = row_y + 56
    for k in range(5):
        x = track_x + k * unit
        body.append(f'<line x1="{x}" y1="{top - 10}" x2="{x}" y2="{top + 24 * len(order) - 6}" stroke="var(--grid)" stroke-opacity="0.7"/>')
        body.append(t(x, top - 16, str(k), "small muted", "middle"))
    notes = {"runtime_budget": "hedged sound plan: nothing to order",
             "caller_callee": "sound plan's tests omit main()"}
    for i, family in enumerate(order):
        y = top + 24 * i + 6
        fits(V2_LABEL[family], 13, track_x - left - 24, family)
        body.append(t(left, y + 4, V2_LABEL[family], "lab"))
        a, b, lost = per_family[family]["skill"], per_family[family]["bare"], per_family[family]["bareLost"]
        if a != b:
            body.append(f'<line x1="{track_x + b * unit}" y1="{y}" x2="{track_x + a * unit}" y2="{y}" stroke="var(--ink2)" stroke-width="2"' + (' stroke-dasharray="4 4"' if lost else "") + '/>')
        body.append(f'<polygon points="{track_x + b * unit},{y - 7} {track_x + b * unit + 7},{y} {track_x + b * unit},{y + 7} {track_x + b * unit - 7},{y}" fill="var(--bare)" stroke="var(--surface)" stroke-width="1.5"/>')
        body.append(f'<circle cx="{track_x + a * unit}" cy="{y}" r="6.5" fill="var(--skill)" stroke="var(--surface)" stroke-width="1.5"/>')
        if lost:
            body.append(t(track_x + 4 * unit + 20, y + 4, f"{lost} bare pair{'s' if lost > 1 else ''} lost to platform interruptions", "small muted"))
        elif family in notes and a != b:
            body.append(t(track_x + 4 * unit + 20, y + 4, notes[family], "small muted"))
    ly = top + 24 * len(order) + 14
    body.append(f'<circle cx="{left + 8}" cy="{ly}" r="6.5" fill="var(--skill)"/>')
    body.append(t(left + 22, ly + 4, "Skill-style", "small"))
    body.append(f'<polygon points="{left + 130},{ly - 7} {left + 137},{ly} {left + 130},{ly + 7} {left + 123},{ly}" fill="var(--bare)"/>')
    body.append(t(left + 146, ly + 4, "Bare", "small"))
    footer = [
        (f"Primary (preregistered): skill {data['primary']['skill']['count']}/{data['primary']['skill']['of']} pairs, bare {data['primary']['bare']['count']}/{data['primary']['bare']['of']}; "
         f"{paired['onlyFirst']} units favour skill, {paired['onlySecond']} favour bare ({p_text}).", "small"),
        (f"Sound plans blocked: {sound_bare['BLOCKERS_FOUND']} of {n_sound} (bare), {mix['skill']['sound']['BLOCKERS_FOUND']} of {sum(mix['skill']['sound'].values())} (skill-style).", "small"),
        (f"Bare reviewer said GO_WITH_CHANGES for {sound_bare['CHANGES_RECOMMENDED']} of {n_sound} sound plans and {defect_bare['CHANGES_RECOMMENDED']} of {n_defect} defect twins.", "small"),
        (f"Human reading: all {data['named']} of {data['missed']} missed bare twins named the planted mechanism; {data['blockingWording']} called it blocking or critical.", "small"),
        ("The verdict line did not separate them; the findings did. Skill-style verdicts follow from labelled findings; bare ones do not.", "small muted"),
        (f"{mix['bare']['stops']} bare observations were interrupted by the platform: stops, not verdicts (see the write-up).", "small muted")]
    y0 = ly + 34
    for i, (text, css) in enumerate(footer):
        body.append(t(left, y0 + 18 * i, text, css))
    height = y0 + 18 * len(footer) + 18
    return document(width, height, "Bare prompt against skill-style prompt on corpus v2",
                    f"Verdict mix and per-family pair discrimination for the skill-style and bare arms: "
                    f"{data['primary']['skill']['count']} of {data['primary']['skill']['of']} against {data['primary']['bare']['count']} of {data['primary']['bare']['of']} pairs ordered.",
                    body, ABLATION_CSS)


THREE_ARM_CSS = """
svg { --skill:#2a78d6; --bare:#eb6834; --defined:#1baf7a; }
@media (prefers-color-scheme: dark) { svg { --skill:#3987e5; --bare:#d95926; --defined:#199e70; } }
"""
FOUR_ARM_CSS = """
svg { --skill:#2a78d6; --bare:#eb6834; --defined:#1baf7a; --defined-go:#8a5fd6; }
@media (prefers-color-scheme: dark) { svg { --skill:#3987e5; --bare:#d95926; --defined:#199e70; --defined-go:#a07ae6; } }
"""
ARM_STYLE = (("skill", "Skill-style", "circle"), ("bare", "Bare", "diamond"), ("defined", "Bare + defined verdicts", "square"))
FOUR_ARM_STYLE = (("skill", "Skill-style", "circle"), ("bare", "Bare", "diamond"), ("defined", "Defined verdicts", "square"),
                  ("defined-go", "Defined + optional sentence", "triangle"))
_RIGHT = {"DEFECT": "BLOCKERS_FOUND", "UNCERTAIN": "CHANGES_RECOMMENDED"}  # the verdict-only correct verdict for a changed twin
RESULTS_V2 = ROOT / "benchmarks/counterfactual-pairs/results"
ARM_DIRS = {"skill": "pilot2-v2-claude-opus-5-5-high", "bare": "ablation-bare-opus-5-5-high",
            "defined": "ablation-defined-opus-5-5-high", "defined-go": "ablation-defined-go-opus-5-5-high"}


def _arm_data(directory, oracle, ledger="responses.jsonl"):
    """One arm's verdict mix (sound plans, defect twins, uncertainty twins) and per-unit ordinal and strict outcomes, from its ledgers."""
    severity, verdicts, mix = {}, {}, {"sound": dict.fromkeys(VERDICT_ORDER, 0), "defect": dict.fromkeys(VERDICT_ORDER, 0),
                         "uncertain": dict.fromkeys(VERDICT_ORDER, 0), "stops": 0}
    for trial in (1, 2):
        for line in (directory / f"trial{trial}/{ledger}").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("technicalStop"):
                mix["stops"] += 1
                continue
            truth = oracle[row["case"]]
            verdicts[(trial, row["case"])] = row["assessment"]
            severity[(truth["family"], truth["wording"], trial, truth["role"])] = (VERDICT_ORDER.index(row["assessment"]), truth["expectedClass"])
            group = "sound" if truth["role"] == "sound" else "defect" if truth["expectedClass"] == "DEFECT" else "uncertain"
            mix[group][row["assessment"]] += 1
    ordinal, strict = {}, {}
    for (family, wording, trial, role), (value, klass) in severity.items():
        if role == "sound" and (family, wording, trial, "changed") in severity:
            twin, twin_class = severity[(family, wording, trial, "changed")]
            ordinal[(family, wording, trial)] = twin > value and not (twin_class == "UNCERTAIN" and twin == 2)
            strict[(family, wording, trial)] = value == 0 and twin == (2 if twin_class == "DEFECT" else 1)
    return mix, ordinal, strict, verdicts


def _load_arms(names):
    """Verdicts recomputed from the committed ledgers, checked against the committed analyses; None until the last arm exists."""
    base = ROOT / "benchmarks/counterfactual-pairs"
    if not (RESULTS_V2 / ARM_DIRS[names[-1]]).is_dir():
        return None
    oracle = {c["case"]: c for c in json.loads((base / "v2/oracle/oracle.json").read_bytes())["cases"]}
    mix, units, strict, verdicts = {}, {}, {}, {}
    for arm in names:
        mix[arm], units[arm], strict[arm], verdicts[arm] = _arm_data(RESULTS_V2 / ARM_DIRS[arm], oracle)
    return oracle, mix, units, strict, verdicts


def _per_family(units, names):
    families = sorted({f for f, _, _ in units[names[0]]})
    per_family = {f: {arm: sum(v for (fam, _, _), v in units[arm].items() if fam == f) for arm in names} for f in families}
    for f in families:
        for arm in names:
            per_family[f][arm + "Lost"] = 4 - sum(1 for (fam, _, _) in units[arm] if fam == f)
    return per_family


def load_three_arms():
    """All three arms' verdicts recomputed from committed ledgers and checked against the committed analyses."""
    names = ["skill", "bare", "defined"]
    loaded = _load_arms(names)
    if loaded is None:
        return None
    oracle, mix, units, _, _ = loaded
    defined_dir = RESULTS_V2 / ARM_DIRS["defined"]
    vs_bare = json.loads((defined_dir / "analysis-vs-bare.json").read_bytes())
    vs_skill = json.loads((defined_dir / "analysis-vs-skill.json").read_bytes())
    expected = {"skill": vs_skill["allPairs"]["primaryOrdinalPairDiscrimination"]["skill"], "bare": vs_bare["allPairs"]["primaryOrdinalPairDiscrimination"]["bare"],
                "defined": vs_bare["allPairs"]["primaryOrdinalPairDiscrimination"]["defined"]}
    for arm in names:
        if (sum(units[arm].values()), len(units[arm])) != (expected[arm]["count"], expected[arm]["of"]):
            raise SystemExit("THREE_ARM_ANALYSIS_STALE:" + arm)
    only_skill = sorted({k[0] for k in set(units["skill"]) & set(units["defined"]) if units["skill"][k] and not units["defined"][k]})
    return {"mix": mix, "perFamily": _per_family(units, names), "primary": expected, "model": vs_bare["arms"]["defined"]["stamps"][0][0],
            "pairedDefinedBare": vs_bare["allPairs"]["primaryPaired"], "pairedSkillDefined": vs_skill["allPairs"]["primaryPaired"],
            "follows": {"skill": vs_skill["arms"]["skill"]["verdictFollowsFinding"], "bare": vs_bare["arms"]["bare"]["verdictFollowsFinding"],
                        "defined": vs_bare["arms"]["defined"]["verdictFollowsFinding"]},
            "onlySkillFamilies": only_skill}


def load_four_arms():
    """The fourth arm beside the other three, recomputed from committed ledgers and checked against the committed analyses."""
    names = ["skill", "bare", "defined", "defined-go"]
    loaded = _load_arms(names)
    if loaded is None:
        return None
    oracle, mix, units, strict, verdicts = loaded
    go_dir = RESULTS_V2 / ARM_DIRS["defined-go"]
    vs_defined = json.loads((go_dir / "analysis-vs-defined.json").read_bytes())
    vs_skill = json.loads((go_dir / "analysis-vs-skill.json").read_bytes())
    block = {"defined": vs_defined["allPairs"], "skill": vs_skill["allPairs"]}
    for arm, source in (("defined", "defined"), ("defined-go", "defined"), ("skill", "skill")):
        counted = block[source]["primaryOrdinalPairDiscrimination"][arm]
        strict_counted = block[source]["strictPairDiscrimination"][arm]
        if ((sum(units[arm].values()), len(units[arm])) != (counted["count"], counted["of"])
                or (sum(strict[arm].values()), len(strict[arm])) != (strict_counted["count"], strict_counted["of"])):
            raise SystemExit("FOUR_ARM_ANALYSIS_STALE:" + arm)
    only_skill = sorted({k[0] for k in set(units["skill"]) & set(units["defined-go"]) if units["skill"][k] and not units["defined-go"][k]})
    return {"mix": mix, "perFamily": _per_family(units, names), "model": vs_defined["arms"]["defined-go"]["stamps"][0][0],
            "primary": {arm: {"count": sum(units[arm].values()), "of": len(units[arm])} for arm in names},
            "strict": {arm: {"count": sum(strict[arm].values()), "of": len(strict[arm])} for arm in names},
            "primaryDefinedGoVsDefined": vs_defined["allPairs"]["primaryPaired"], "soundCleanDefinedVsGo": vs_defined["allPairs"]["soundCleanPaired"],
            "twinCorrectDefinedVsGo": vs_defined["allPairs"]["changedTwinCorrectPaired"], "soundCleanSkillVsGo": vs_skill["allPairs"]["soundCleanPaired"],
            "strictSkillVsGo": vs_skill["allPairs"]["strictPaired"],
            "defectBlocked": {"defined": vs_defined["allPairs"]["defectTwinsBlocked"]["defined"], "defined-go": vs_defined["allPairs"]["defectTwinsBlocked"]["defined-go"]},
            "lostFamilies": sorted({oracle[case]["family"] for (trial, case), verdict in verdicts["defined"].items()
                                    if oracle[case]["role"] == "changed" and verdict == _RIGHT[oracle[case]["expectedClass"]]
                                    and (trial, case) in verdicts["defined-go"] and verdicts["defined-go"][(trial, case)] != verdict}),
            "onlySkillFamilies": only_skill}


def _marker(shape, cx, cy, var, scale=1.0, stroke=True):
    ring = f' stroke="var(--surface)" stroke-width="1.5"' if stroke else ""
    if shape == "circle":
        return f'<circle cx="{cx}" cy="{cy}" r="{6.5 * scale:.1f}" fill="var({var})"{ring}/>' if scale != 1.0 else f'<circle cx="{cx}" cy="{cy}" r="6.5" fill="var({var})"{ring}/>'
    if shape == "diamond":
        d = 7.5 * scale
        return f'<polygon points="{cx},{cy - d:g} {cx + d:g},{cy} {cx},{cy + d:g} {cx - d:g},{cy}" fill="var({var})"{ring}/>'
    if shape == "triangle":
        d = 7.5 * scale
        return f'<polygon points="{cx},{cy - d:g} {cx + d:g},{cy + d * 0.8:g} {cx - d:g},{cy + d * 0.8:g}" fill="var({var})"{ring}/>'
    h = 5.5 * scale
    return f'<rect x="{cx - h:g}" y="{cy - h:g}" width="{2 * h:g}" height="{2 * h:g}" fill="var({var})"{ring}/>'


def _arms_figure(data, style, css, groups, header, footer, title, description, lanes=False):
    """Panel A (verdict mix per arm and group) and panel B (pairs ordered per family and arm), shared by the three- and four-arm figures."""
    width, left = 900, 24
    mix, per_family = data["mix"], data["perFamily"]
    body = [t(left, 36, header[0], "title"), t(left, 58, header[1], "sub muted"), t(left, 78, header[2], "sub muted"),
            t(left, 116, "A. Verdicts given", "lab", extra=' font-weight="600"')]
    bar_x, bar_w, row_y = 250, 480, 134
    for group, label in groups:
        body.append(t(left, row_y + 15, label, "head"))
        row_y += 22
        for arm, name, _ in style:
            counts = mix[arm][group]
            n = sum(counts.values())
            fits(name, 11.5, bar_x - left - 24, name)
            body.append(t(left + 12, row_y + 17, f"{name} (n={n})", "small"))
            x = bar_x
            for verdict in VERDICT_ORDER:
                value = counts[verdict]
                if not value:
                    continue
                seg = bar_w * value / n
                label, fill, ink = VERDICT[verdict]
                body.append(f'<rect x="{x:.1f}" y="{row_y}" width="{seg:.1f}" height="22" fill="{fill}" stroke="var(--surface)" stroke-width="2"/>')
                if seg >= 46:
                    body.append(f'<text x="{x + seg / 2:.1f}" y="{row_y + 15}" class="small" text-anchor="middle" fill="{ink}" style="fill:{ink}">{label} {value}</text>')
                x += seg
            row_y += 28
        row_y += 6
    lx = bar_x
    for verdict in VERDICT_ORDER:
        label, fill, ink = VERDICT[verdict]
        text = {"NO_BLOCKERS_FOUND": "Clean (GO)", "CHANGES_RECOMMENDED": "Changes (GO_WITH_CHANGES)", "BLOCKERS_FOUND": "Blockers (NO_GO)"}[verdict]
        body.append(f'<rect x="{lx}" y="{row_y}" width="22" height="14" rx="3" fill="{fill}"/>')
        body.append(t(lx + 30, row_y + 11, text, "small"))
        lx += 30 + len(text) * 6.6 + 20
    row_y += 44
    body.append(t(left, row_y, "B. Pairs where the changed twin was judged more severely than its sound twin", "lab", extra=' font-weight="600"'))
    body.append(t(left, row_y + 18, "Out of 4 per family (2 wordings x 2 trials); a line joins the lowest and highest arm. Stops can remove pairs.", "small muted"))
    track_x, unit = 250, 84
    pitch = 40 if lanes else 24
    order = sorted(per_family, key=lambda f: tuple(per_family[f][arm] for arm, _, _ in style[1:]) + (V2_LABEL.get(f, f),))
    top = row_y + 56
    for k in range(5):
        x = track_x + k * unit
        body.append(f'<line x1="{x}" y1="{top - 10}" x2="{x}" y2="{top + pitch * len(order) - 6}" stroke="var(--grid)" stroke-opacity="0.7"/>')
        body.append(t(x, top - 16, str(k), "small muted", "middle"))
    for i, family in enumerate(order):
        y = top + pitch * i + 6
        fits(V2_LABEL[family], 13, track_x - left - 24, family)
        body.append(t(left, y + 4, V2_LABEL[family], "lab"))
        values = [per_family[family][arm] for arm, _, _ in style]
        body.append(f'<line x1="{track_x + min(values) * unit}" y1="{y}" x2="{track_x + max(values) * unit}" y2="{y}" stroke="var(--ink2)" stroke-width="2"/>')
        for lane, (arm, _, shape) in enumerate(style):
            cx = track_x + per_family[family][arm] * unit
            if lanes:
                body.append(_marker(shape, cx, y + (lane - (len(style) - 1) / 2) * 8, "--" + arm, 0.78))
            else:
                body.append(_marker(shape, cx, y, "--" + arm))
        lost = {arm: per_family[family][arm + "Lost"] for arm, _, _ in style if per_family[family][arm + "Lost"]}
        if lost:
            names = ", ".join(f"{n} {arm}" for arm, n in lost.items())
            body.append(t(track_x + 4 * unit + 20, y + 4, f"pairs lost to stops: {names}", "small muted"))
    ly = top + pitch * len(order) + 14
    lx = left
    for arm, name, shape in style:
        body.append(_marker(shape, lx + 8, ly, "--" + arm, stroke=False))
        body.append(t(lx + 24, ly + 4, name, "small"))
        lx += 24 + len(name) * 6.6 + 28
    y0 = ly + 34
    for i, (text, css_class) in enumerate(footer):
        body.append(t(left, y0 + 18 * i, text, css_class))
    height = y0 + 18 * len(footer) + 18
    return document(width, height, title, description, body, css)


def _fmt_p(p):
    return "p < 0.0001" if p < 0.0001 else f"p = {p}"


def three_arm_figure(data):
    mix = data["mix"]
    pdb, psd = data["pairedDefinedBare"], data["pairedSkillDefined"]
    prim, follows = data["primary"], data["follows"]
    only = data["onlySkillFamilies"]
    residual = (f"All {psd['onlyFirst']} units still favouring the skill-style arm are in one family ({V2_LABEL.get(only[0], only[0])}), the preregistered limit: "
                "a hedged sound plan leaves nothing to order.") if len(only) == 1 else \
               f"The {psd['onlyFirst']} units still favouring the skill-style arm fall in {len(only)} families."
    label = "closes the gap" if (pdb["exactTwoSidedSignTestP"] < 0.05 and pdb["onlySecond"] == 0 and psd["onlyFirst"] <= 3) else \
        "partly closes the gap" if pdb["exactTwoSidedSignTestP"] < 0.05 else "does not close the gap"
    footer = [
        (f"Primary (preregistered): skill-style {prim['skill']['count']}/{prim['skill']['of']}, defined {prim['defined']['count']}/{prim['defined']['of']}, bare {prim['bare']['count']}/{prim['bare']['of']} pairs.", "small"),
        (f"Defined against bare: {pdb['onlyFirst']} units favour bare, {pdb['onlySecond']} favour defined ({_fmt_p(pdb['exactTwoSidedSignTestP'])}). "
         f"Defined against skill-style: {psd['onlyFirst']} favour skill-style, {psd['onlySecond']} favour defined ({_fmt_p(psd['exactTwoSidedSignTestP'])}).", "small"),
        (residual, "small"),
        (f"Verdict follows finding: skill-style {follows['skill']['count']}/{follows['skill']['of']}, defined {follows['defined']['count']}/{follows['defined']['of']}, bare {follows['bare']['count']}/{follows['bare']['of']}.", "small"),
        (f"Sound plans were still hedged: clean {mix['defined']['sound']['NO_BLOCKERS_FOUND']} of {sum(mix['defined']['sound'].values())} (defined), "
         f"{mix['skill']['sound']['NO_BLOCKERS_FOUND']} of {sum(mix['skill']['sound'].values())} (skill-style). None was blocked in any arm.", "small"),
        (f"Preregistered label: {label}. A bundle test: other differences from the skill-style arm remain.", "small muted")]
    header = ("Does defining the verdicts close the gap? Three arms, same 40 plans",
              f"{data['model']} through the Claude CLI, 2 trials per arm. The skill-style and bare arms were run earlier, not concurrently.",
              "The bare + defined arm is the bare prompt plus one five-line block saying what GO, GO_WITH_CHANGES and NO_GO mean.")
    return _arms_figure(data, ARM_STYLE, THREE_ARM_CSS, (("sound", "Sound plans"), ("defect", "Defect twins")), header, footer,
                        "Three arms on corpus v2: skill-style, bare, and bare with defined verdicts",
                        f"Verdict mix and per-family pair discrimination: {prim['skill']['count']} of {prim['skill']['of']} (skill-style), "
                        f"{prim['defined']['count']} of {prim['defined']['of']} (defined) and {prim['bare']['count']} of {prim['bare']['of']} (bare) pairs ordered.")


def fourth_arm_label(data):
    """The preregistered label's detection guard and sound-plan rule, as in ablation/analyze.py fourth_arm_label (a test compares them)."""
    clean, lost, skill = data["soundCleanDefinedVsGo"], data["twinCorrectDefinedVsGo"], data["soundCleanSkillVsGo"]
    if lost["onlyFirst"] >= 3:
        return "costs detection"
    if clean["exactTwoSidedSignTestP"] < 0.05 and clean["onlyFirst"] > clean["onlySecond"]:
        return "worse on sound plans"
    if clean["exactTwoSidedSignTestP"] < 0.05:
        return "closes the sound-plan gap" if skill["onlyFirst"] <= 5 else "partly closes the sound-plan gap"
    return "does not close the sound-plan gap"


def four_arm_figure(data):
    mix, prim, strict = data["mix"], data["primary"], data["strict"]
    clean, lost, sk = data["soundCleanDefinedVsGo"], data["twinCorrectDefinedVsGo"], data["soundCleanSkillVsGo"]
    unc = mix["defined-go"]["uncertain"]
    unc_before = mix["defined"]["uncertain"]
    n_unc = sum(unc.values())
    where = ", ".join(V2_LABEL.get(f, f) for f in data["lostFamilies"]) or "none"
    db = data["defectBlocked"]
    only = ", ".join(V2_LABEL.get(f, f) for f in data["lostFamilies"])
    footer = [
        (f"Primary (ordered pairs): skill-style {prim['skill']['count']}/{prim['skill']['of']}, defined + sentence {prim['defined-go']['count']}/{prim['defined-go']['of']}, "
         f"defined {prim['defined']['count']}/{prim['defined']['of']}, bare {prim['bare']['count']}/{prim['bare']['of']}.", "small"),
        (f"Sound plans Clean: {mix['defined-go']['sound']['NO_BLOCKERS_FOUND']} of {sum(mix['defined-go']['sound'].values())} with the sentence, {mix['defined']['sound']['NO_BLOCKERS_FOUND']} of "
         f"{sum(mix['defined']['sound'].values())} without ({clean['onlySecond']} units for, {clean['onlyFirst']} against, {_fmt_p(clean['exactTwoSidedSignTestP'])}); "
         f"skill-style {mix['skill']['sound']['NO_BLOCKERS_FOUND']} of {sum(mix['skill']['sound'].values())}.", "small"),
        (f"Defect twins stayed blocked: {db['defined-go']['count']}/{db['defined-go']['of']} (defined {db['defined']['count']}/{db['defined']['of']}).", "small"),
        (f"Uncertainty twins (correct verdict Changes): Changes {unc_before['CHANGES_RECOMMENDED']} of {sum(unc_before.values())} before, {unc['CHANGES_RECOMMENDED']} of {n_unc} with the sentence; "
         f"the other {lost['onlyFirst']} were judged Clean.", "small"),
        (f"All {lost['onlyFirst']} are in one family ({only}): the unmeasured throughput was filed as an optional suggestion.", "small"),
        (f"Strict pairs (sound twin Clean, changed twin right): defined + sentence {strict['defined-go']['count']}/{strict['defined-go']['of']}, skill-style {strict['skill']['count']}/{strict['skill']['of']}, "
         f"defined {strict['defined']['count']}/{strict['defined']['of']}, bare {strict['bare']['count']}/{strict['bare']['of']}.", "small"),
        (f"Preregistered label: {fourth_arm_label(data)} (the guard is 3 or more lost units; here {lost['onlyFirst']}).", "small"),
        ("The sentence was written after the defined result, on this corpus: a check of the mechanism, not out-of-sample evidence.", "small muted")]
    header = ("One sentence made sound plans clean and let an unmeasured risk through",
              f"{data['model']} through the Claude CLI, 2 trials per arm, same 40 plans; the earlier arms were not run concurrently.",
              "The added sentence says optional robustness suggestions are not needed changes, so GO if that is all.")
    for text, size in [(header[0], 20), (header[1], 13), (header[2], 13)] + [(line, 11.5) for line, _ in footer]:
        fits(text, size, 876, "four-arm text")
    return _arms_figure(data, FOUR_ARM_STYLE, FOUR_ARM_CSS, (("sound", "Sound plans"), ("defect", "Defect twins"), ("uncertain", "Uncertainty twins")),
                        header, footer, "Four arms on corpus v2: the optional-suggestions sentence",
                        f"Verdict mix by arm for sound plans, defect twins and uncertainty twins, and pairs ordered per family: the sentence made "
                        f"{mix['defined-go']['sound']['NO_BLOCKERS_FOUND']} of {sum(mix['defined-go']['sound'].values())} sound plans clean and kept every defect twin blocked, "
                        f"but {unc['NO_BLOCKERS_FOUND']} of {n_unc} uncertainty-twin observations were judged Clean.", lanes=True)


ROUTE_CSS = """
svg { --claude:#2a78d6; --flash:#8a5fd6; }
@media (prefers-color-scheme: dark) { svg { --claude:#3987e5; --flash:#a07ae6; } }
"""
ROUTE_STYLE = (("claude", "Claude Opus 5.5", "circle"), ("flash", "Gemini 3.8 Flash High", "square"))


def load_routes():
    """The same corpus v1 on two routes, from committed ledgers (the Gemini run in its documented-rule view), checked against committed scores."""
    claude_dir = RESULTS_V2 / "pilot1-claude-opus-5-5-high"
    if not GEMINI_RESULTS.is_dir() or not claude_dir.is_dir():
        return None
    base = ROOT / "benchmarks/counterfactual-pairs"
    oracle = {c["case"]: c for c in json.loads((base / "oracle/oracle.json").read_bytes())["cases"]}
    mix, units, strict, verdicts = {}, {}, {}, {}
    mix["claude"], units["claude"], strict["claude"], verdicts["claude"] = _arm_data(claude_dir, oracle)
    mix["flash"], units["flash"], strict["flash"], verdicts["flash"] = _arm_data(GEMINI_RESULTS, oracle, "responses-documented-rule.jsonl")
    for arm, path in (("claude", claude_dir / "score.json"), ("flash", GEMINI_RESULTS / "score-documented-rule.json")):
        score = json.loads(path.read_bytes())["trials"]
        for t_ in (1, 2):
            got = sum(v for (f, w, tr), v in strict[arm].items() if tr == t_)
            if got != score[str(t_)]["pairDiscrimination"]["count"]:
                raise SystemExit("ROUTE_SCORE_STALE:" + arm)
    per_trial = lambda table, arm, skip=(): [sum(v for (f, w, tr), v in table[arm].items() if tr == t_ and f not in skip) for t_ in (1, 2)]
    agree = sum(verdicts["claude"][k] == verdicts["flash"][k] for k in verdicts["claude"])
    flash_stops = sum(1 for t_ in (1, 2) for r in _flash_rows("responses.jsonl")[t_] if r.get("technicalStop"))
    hedged = {arm: mix[arm]["sound"]["CHANGES_RECOMMENDED"] for arm in mix}
    return {"mix": mix, "perFamily": _per_family(units, ["claude", "flash"]), "agree": agree, "total": len(verdicts["claude"]), "stops": flash_stops,
            "ordered": {a: per_trial(units, a) for a in units}, "orderedValid": {a: per_trial(units, a, ("output_bytes",)) for a in units},
            "strict": {a: per_trial(strict, a) for a in strict}, "hedged": hedged, "soundN": {a: sum(mix[a]["sound"].values()) for a in mix}}


def routes_figure(data):
    mix, ordered, valid, strict = data["mix"], data["ordered"], data["orderedValid"], data["strict"]
    footer = [
        (f"Pairs ordered (twin judged more severely than its sound plan), trials 1 and 2: Claude {ordered['claude'][0]}/12 and {ordered['claude'][1]}/12, Gemini {ordered['flash'][0]}/12 and {ordered['flash'][1]}/12.", "small"),
        (f"Without the defective Output byte limit family: Claude {valid['claude'][0]}/10 and {valid['claude'][1]}/10, Gemini {valid['flash'][0]}/10 and {valid['flash'][1]}/10.", "small"),
        (f"Strict pairs (sound plan Clean and twin right): Claude {strict['claude'][0]}/12 and {strict['claude'][1]}/12, Gemini {strict['flash'][0]}/12 and {strict['flash'][1]}/12.", "small"),
        (f"Gemini hedged {data['hedged']['flash']} of {data['soundN']['flash']} sound plans, Claude {data['hedged']['claude']} of {data['soundN']['claude']}. On required coverage Gemini wrote Changes where Claude wrote Blockers.", "small"),
        (f"Verdicts agree in {data['agree']} of {data['total']}. Gemini's {data['stops']} format stops are re-read (documented rule); its model is requested, not attested.", "small muted"),
        ("Different routes and times, one corpus with one flawed family; nothing here is a general accuracy rate.", "small muted")]
    header = ("Same 24 plans, two reviewers: Claude Opus 5.5 and Gemini 3.8 Flash High",
              "Corpus v1, 2 trials each: Claude via claude-cli, Gemini via the native flash-high route; run at different times.",
              "Gemini's four format stops (label S01:3 for line 3) are re-read as line 3; as-run numbers are in the write-up.")
    for text, size in [(header[0], 20), (header[1], 13), (header[2], 13)] + [(line, 11.5) for line, _ in footer]:
        fits(text, size, 876, "routes text")
    return _arms_figure(data, ROUTE_STYLE, ROUTE_CSS, (("sound", "Sound plans"), ("defect", "Defect twins"), ("uncertain", "Uncertainty twin (runtime budget)")),
                        header, footer, "Corpus v1 on two reviewer routes",
                        f"Verdict mix and pairs ordered per family for Claude Opus 5.5 and Gemini 3.8 Flash High on the same 24 plans; verdicts agree in {data['agree']} of {data['total']} observations.", lanes=True)


V3_RESULTS = ROOT / "benchmarks/counterfactual-pairs/results/v3-gemini-flash-high"
V3_LABEL = {"cache_tenant_key": "Cache tenant key", "lock_order": "Lock order", "rate_arithmetic": "Rate arithmetic",
            "payment_idempotency_key": "Payment idempotency key", "cert_rotation": "Certificate rotation",
            "flag_default": "Flag default", "backup_window": "Backup window", "credential_logging": "Credential logging",
            "capacity_headroom": "Capacity headroom", "upgrade_compat": "Upgrade compatibility",
            "retry_idempotent": "Retry idempotence", "rate_limit_quota": "Rate limit quota",
            "unique_constraint": "Unique constraint", "rollback_window": "Rollback window",
            "payload_limit": "Payload limit", "storage_access": "Storage access"}


def load_v3_gemini():
    """The Gemini 3.8 Flash High run on corpus v3 (as run), from committed ledgers, checked against the committed score and analysis."""
    if not V3_RESULTS.is_dir():
        return None
    base = ROOT / "benchmarks/counterfactual-pairs"
    oracle = {c["case"]: c for c in json.loads((base / "v3/oracle/oracle.json").read_bytes())["cases"]}
    rows, stops, kind = {}, [], {}
    for trial in (1, 2):
        for line in (V3_RESULTS / f"trial{trial}/responses.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            truth = oracle[row["case"]]
            key = (truth["family"], truth["wording"], truth["role"], trial)
            rows[key] = "STOP" if row.get("technicalStop") else row["assessment"]
            if truth["role"] == "changed":
                kind[truth["family"]] = (truth["expectedClass"], truth["difficulty"])
            stops += [key] if row.get("technicalStop") else []
    if len(rows) != 128 or len(kind) != 16:
        raise SystemExit("V3_GEMINI_INCOMPLETE")
    score = json.loads((V3_RESULTS / "score.json").read_bytes())["trials"]
    analysis = json.loads((V3_RESULTS / "analysis.json").read_bytes())["arms"]["gemini"]
    strict = [(score[str(t_)]["pairDiscrimination"]["count"], score[str(t_)]["pairDiscrimination"]["of"]) for t_ in (1, 2)]
    for t_ in (1, 2):
        got = sum(1 for f in kind for w in "AB" if "STOP" not in (rows[(f, w, "sound", t_)], rows[(f, w, "changed", t_)])
                  and rows[(f, w, "sound", t_)] == "NO_BLOCKERS_FOUND"
                  and rows[(f, w, "changed", t_)] == ("BLOCKERS_FOUND" if kind[f][0] == "DEFECT" else "CHANGES_RECOMMENDED"))
        if got != strict[t_ - 1][0]:
            raise SystemExit("V3_GEMINI_SCORE_STALE")
    primary = {k: (v["count"], v["of"]) for k, v in analysis["primary"].items()}
    return {"rows": rows, "kind": kind, "stops": stops, "strict": strict, "primary": primary,
            "labels": analysis["secondary"]["snapshotLabelRead"]}


def v3_gemini_figure(data):
    rows, kind, p = data["rows"], data["kind"], data["primary"]
    width, left, label_w, cell_w, cell_h, row_h = 900, 24, 230, 62, 20, 25
    sub = 4
    x_sound = left + label_w
    x_twin = x_sound + 4 * (cell_w + sub) + 28
    families = [f for f in V3_LABEL if kind[f][0] == "DEFECT"] + [f for f in V3_LABEL if kind[f][0] != "DEFECT"]
    top = 150
    height = top + 16 * row_h + 2 * 30 + 130
    body = [t(left, 36, "Gemini 3.8 Flash High on held-out corpus v3: every verdict", "title"),
            t(left, 58, "Route flash-high (native agy), model gemini-3.8-flash-high (requested, not attested); 64 cases, 2 trials, 1 runtime stop.", "sub muted"),
            t(left, 78, f"Sound plans judged Clean {p['soundPlansGo'][0]}/{p['soundPlansGo'][1]}; defect twins Blockers {p['defectTwinsNoGo'][0]}/{p['defectTwinsNoGo'][1]}; "
                        f"evidence-gap twins Changes {p['evidenceGapTwinsGoWithChanges'][0]}/{p['evidenceGapTwinsGoWithChanges'][1]}.", "sub muted")]
    for x0, group in ((x_sound, "Sound plan"), (x_twin, "Changed twin")):
        centre = x0 + (4 * (cell_w + sub) - sub) / 2
        body.append(t(centre, top - 34, group, "head", "middle"))
        for i, (w, t_) in enumerate((("A", 1), ("A", 2), ("B", 1), ("B", 2))):
            body.append(t(x0 + i * (cell_w + sub) + cell_w / 2, top - 12, f"{w} · trial {t_}", "small muted", "middle"))
    y = top
    section = None
    for family in families:
        cls = "Defect families (the twin breaks a stated rule)" if kind[family][0] == "DEFECT" else "Evidence-gap families (one decisive fact is not established)"
        if cls != section:
            y += 10 if section else 0
            section = cls
            fits(cls, 12, 700, cls)
            body.append(t(left, y + 8, cls, "head"))
            y += 22
        detail = {"direct": "direct", "inference": "inference across lines", "evidence_gap": "evidence gap"}[kind[family][1]]
        fits(V3_LABEL[family], 13, label_w - 20, family)
        body.append(t(left, y + 15, f"{V3_LABEL[family]}", "lab"))
        for x0, role in ((x_sound, "sound"), (x_twin, "changed")):
            for i, (w, t_) in enumerate((("A", 1), ("A", 2), ("B", 1), ("B", 2))):
                verdict = rows[(family, w, role, t_)]
                x = x0 + i * (cell_w + sub)
                if verdict == "STOP":
                    body.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" rx="3" fill="none" stroke="var(--ink2)" stroke-dasharray="3 3"/>')
                    body.append(f'<text x="{x + cell_w / 2}" y="{y + 14}" class="small" text-anchor="middle">Stop</text>')
                    continue
                label, fill, ink = VERDICT[verdict]
                body.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" rx="3" fill="{fill}"/>')
                body.append(f'<text x="{x + cell_w / 2}" y="{y + 14}" class="small" text-anchor="middle" fill="{ink}" style="fill:{ink}">{label}</text>')
        y += row_h
    ly = y + 16
    for i, verdict in enumerate(("NO_BLOCKERS_FOUND", "CHANGES_RECOMMENDED", "BLOCKERS_FOUND")):
        label, fill, ink = VERDICT[verdict]
        text = {"NO_BLOCKERS_FOUND": "Clean: no blockers found", "CHANGES_RECOMMENDED": "Changes recommended", "BLOCKERS_FOUND": "Blockers found"}[verdict]
        x = left + i * 250
        body.append(f'<rect x="{x}" y="{ly}" width="26" height="16" rx="3" fill="{fill}"/>')
        body.append(t(x + 34, ly + 12, text, "small"))
    stop_f, stop_w, stop_r, stop_t = data["stops"][0]
    want = lambda f: "BLOCKERS_FOUND" if kind[f][0] == "DEFECT" else "CHANGES_RECOMMENDED"
    twins = [(f, w, t_) for f in kind for w in "AB" for t_ in (1, 2)]
    twins_right = sum(rows[(f, w, "changed", t_)] == want(f) for f, w, t_ in twins)
    not_clean = [f"{V3_LABEL[f]} (trial {t_})" for f, w, t_ in twins if rows[(f, w, "sound", t_)] not in ("NO_BLOCKERS_FOUND", "STOP")]
    footer = [("Right verdict: Clean for a sound plan, Blockers for a defect twin, Changes for an evidence-gap twin.", "small"),
              (f"Twins right in {twins_right} of {len(twins)} observations. Sound plans hedged, never Blockers: " + ", ".join(not_clean) + ".", "small"),
              (f"Dashed cell: runtime stop (error step, no report), {V3_LABEL[stop_f]} sound plan, trial {stop_t}; not rerun, in no denominator.", "small muted"),
              (f"Pairs discriminated, strict: {data['strict'][0][0]}/{data['strict'][0][1]} and {data['strict'][1][0]}/{data['strict'][1][1]}. Zero unsupported VERIFIED findings.", "small muted"),
              (f"{data['labels']} reports used the label S01:n as the line number (read as that line, preregistered).", "small muted"),
              ("One reviewer, one route, one corpus written by Claude; a ceiling result is not a general accuracy rate.", "small muted")]
    for i, (text, css) in enumerate(footer):
        fits(text, 11.5, 876, "v3 footer")
        body.append(t(left, ly + 40 + 18 * i, text, css))
    height = ly + 40 + 18 * len(footer) + 6
    return document(width, height, "Gemini 3.8 Flash High on corpus v3: verdicts",
                    f"Every verdict of two trials on 64 held-out cases; sound plans Clean {p['soundPlansGo'][0]} of {p['soundPlansGo'][1]}, "
                    f"defect twins Blockers {p['defectTwinsNoGo'][0]} of {p['defectTwinsNoGo'][1]}, evidence-gap twins Changes {p['evidenceGapTwinsGoWithChanges'][0]} of {p['evidenceGapTwinsGoWithChanges'][1]}.", body)


V3_CLAUDE = ROOT / "benchmarks/counterfactual-pairs/results/v3-claude-opus-5-5-high"
V3_ROWS = (("skill", "Claude skill-style", V3_CLAUDE / "skill"), ("defined", "Claude defined", V3_CLAUDE / "defined"),
           ("defined-go", "Claude + sentence", V3_CLAUDE / "defined-go"), ("gemini", "Gemini skill-style", V3_RESULTS))
V3_PANELS = (("sound", "Sound plans", "NO_BLOCKERS_FOUND", "Clean"), ("defect", "Defect twins", "BLOCKERS_FOUND", "Blockers"),
             ("gap", "Evidence-gap twins", "CHANGES_RECOMMENDED", "Changes"))


def load_v3_arms():
    """Verdict mix per arm and group on corpus v3 from committed ledgers, checked against the committed three-arm analysis."""
    if not V3_CLAUDE.is_dir() or not V3_RESULTS.is_dir():
        return None
    base = ROOT / "benchmarks/counterfactual-pairs"
    oracle = {c["case"]: c for c in json.loads((base / "v3/oracle/oracle.json").read_bytes())["cases"]}
    analysis = json.loads((V3_CLAUDE / "analysis.json").read_bytes())["arms"]
    mixes, stops = {}, {}
    for arm, _, directory in V3_ROWS:
        mix = {g: dict.fromkeys(VERDICT_ORDER, 0) for g, *_ in V3_PANELS}
        stops[arm] = 0
        for trial in (1, 2):
            for line in (directory / f"trial{trial}/responses.jsonl").read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                if row.get("technicalStop"):
                    stops[arm] += 1
                    continue
                truth = oracle[row["case"]]
                group = "sound" if truth["role"] == "sound" else "defect" if truth["expectedClass"] == "DEFECT" else "gap"
                mix[group][row["assessment"]] += 1
        mixes[arm] = mix
    for arm, key in (("skill", "skill"), ("defined", "defined"), ("defined-go", "defined-go"), ("gemini", None)):
        if key is None:
            expected = json.loads((V3_RESULTS / "analysis.json").read_bytes())["arms"]["gemini"]["primary"]
        else:
            expected = analysis[key]["primary"]
        got = (mixes[arm]["sound"]["NO_BLOCKERS_FOUND"], mixes[arm]["defect"]["BLOCKERS_FOUND"], mixes[arm]["gap"]["CHANGES_RECOMMENDED"])
        want = (expected["soundPlansGo"]["count"], expected["defectTwinsNoGo"]["count"], expected["evidenceGapTwinsGoWithChanges"]["count"])
        if got != want:
            raise SystemExit("V3_ARMS_ANALYSIS_STALE:" + arm)
    return {"mix": mixes, "stops": stops}


def v3_arms_figure(data):
    mix, stops = data["mix"], data["stops"]
    width, left, label_w, panel_w, gap, row_h = 900, 24, 176, 220, 14, 54
    top = 142
    colours = {"NO_BLOCKERS_FOUND": ("Clean", "#cde2fb", "#0b0b0b"), "CHANGES_RECOMMENDED": ("Changes", "#6da7ec", "#0b0b0b"),
               "BLOCKERS_FOUND": ("Blockers", "#184f95", "#ffffff")}
    body = [t(left, 36, "Corpus v3: four reviewers, verdict mix per kind of case", "title"),
            t(left, 58, "Claude Opus 5.5 via the Claude CLI (three prompt arms) and Gemini 3.8 Flash High via the native route; 64 cases, 2 trials each.", "sub muted"),
            t(left, 78, "The right verdict is Clean for a sound plan, Blockers for a defect twin and Changes for an evidence-gap twin (outlined).", "sub muted")]
    for i, (group, title, right, short) in enumerate(V3_PANELS):
        x = left + label_w + i * (panel_w + gap)
        body.append(t(x, top - 14, title, "head"))
    y = top
    for arm, label, _ in V3_ROWS:
        fits(label, 13, label_w - 12, label)
        body.append(t(left, y + 24, label, "lab"))
        for i, (group, title, right, short) in enumerate(V3_PANELS):
            x0 = left + label_w + i * (panel_w + gap)
            counts = mix[arm][group]
            n = sum(counts.values())
            x = x0
            for verdict in VERDICT_ORDER:
                count = counts[verdict]
                if not count:
                    continue
                w = panel_w * count / n
                name, fill, ink = colours[verdict]
                outline = ' stroke="var(--ink)" stroke-width="2"' if verdict == right else ""
                body.append(f'<rect x="{x:.1f}" y="{y + 6}" width="{w:.1f}" height="28" fill="{fill}"{outline}><title>{name}: {count} of {n}</title></rect>')
                if w >= 22:
                    body.append(f'<text x="{x + w / 2:.1f}" y="{y + 25}" class="small" text-anchor="middle" fill="{ink}" style="fill:{ink}">{count}</text>')
                x += w
            body.append(t(x0, y + 48, f"{counts[right]} of {n} right", "small muted"))
        y += row_h
    ly = y + 14
    for i, verdict in enumerate(VERDICT_ORDER):
        name, fill, ink = colours[verdict]
        text = {"NO_BLOCKERS_FOUND": "Clean: no blockers found", "CHANGES_RECOMMENDED": "Changes recommended", "BLOCKERS_FOUND": "Blockers found"}[verdict]
        x = left + i * 250
        body.append(f'<rect x="{x}" y="{ly}" width="26" height="16" rx="3" fill="{fill}"/>')
        body.append(t(x + 34, ly + 12, text, "small"))
    sound_skill = mix["skill"]["sound"]["NO_BLOCKERS_FOUND"]
    footer = [(f"Counts are observations over two trials. Gemini had {stops['gemini']} runtime stop (a sound plan), removed from every denominator.", "small"),
              (f"Claude's verdict-only arms overclaimed the evidence gap as a blocker ({mix['defined']['gap']['BLOCKERS_FOUND']} and {mix['defined-go']['gap']['BLOCKERS_FOUND']} of 32); "
               f"the sentence arm waved through {mix['defined-go']['gap']['NO_BLOCKERS_FOUND']}.", "small"),
              (f"The skill-style prompt hedged {mix['skill']['sound']['CHANGES_RECOMMENDED']} of 64 sound plans on Claude and {mix['gemini']['sound']['CHANGES_RECOMMENDED']} of 63 on Gemini.", "small"),
              ("Different routes, wrappers and days: Claude against Gemini is a difference as run, not between models.", "small muted")]
    for text, css in footer:
        fits(text, 11.5, 876, "v3 arms footer")
    for i, (text, css) in enumerate(footer):
        body.append(t(left, ly + 40 + 18 * i, text, css))
    height = ly + 40 + 18 * len(footer) + 6
    return document(width, height, "Corpus v3: verdict mix for four reviewers",
                    "Verdict counts for sound plans, defect twins and evidence-gap twins from three Claude prompt arms and one Gemini run on corpus v3, two trials each.", body)


def build(inputs):
    figures = {"fault-gate-matrix.svg": fault_matrix(inputs["results"]),
               "offline-evidence.svg": evidence_overview(inputs)}
    if inputs.get("pilot"):
        figures["pilot1-verdict-matrix.svg"] = pair_matrix(inputs["pilot"])
    if inputs.get("pilot2"):
        figures["pilot2-verdict-matrix.svg"] = pair_matrix(inputs["pilot2"])
    if inputs.get("ablation"):
        figures["ablation-bare-vs-skill.svg"] = ablation_figure(inputs["ablation"])
    if inputs.get("threeArms"):
        figures["ablation-three-arms.svg"] = three_arm_figure(inputs["threeArms"])
    if inputs.get("fourArms"):
        figures["ablation-four-arms.svg"] = four_arm_figure(inputs["fourArms"])
    if inputs.get("flash"):
        flash = inputs["flash"]
        figures["pilot-flash-verdict-matrix.svg"] = pair_matrix(dict(
            flash, subtitle2=f"Route flash-high (native agy), model {flash['model']} (requested, not attested), effort {flash['effort']}; 24 cases, 2 trials, {flash['stops']} format stops marked *.",
            subtitle3=f"Pre-registered strict score on the documented-rule view: {flash['strict'][0]}/12 and {flash['strict'][1]}/12 (as run, with the stops removed: "
                      f"{flash['asRunStrict'][0][0]}/{flash['asRunStrict'][0][1]} and {flash['asRunStrict'][1][0]}/{flash['asRunStrict'][1][1]}).",
            title="Gemini 3.8 Flash High: sound plans and their changed twins",
            footer=[(f"Ordinal reading, five valid families: the changed twin was judged strictly more severely than its sound twin in {flash['ordinal']} of 20 pair-observations.", "small"),
                    ("* The report ended with a correct BLOCKER whose line field was the label S01:3; the strict parser stopped it. Read here as line 3 (documented rule).", "small muted"),
                    ("Both required-coverage twins got Changes (a RISK), not Blockers: the reviewer said the diff's contents are not in the snapshot.", "small muted"),
                    ("Dashed cells: Output byte limit is excluded as a corpus defect (pilot 1). This reviewer judged both of its sound plans clean.", "small muted")]))
    if inputs.get("routes"):
        figures["pilot-routes-comparison.svg"] = routes_figure(inputs["routes"])
    if inputs.get("v3Gemini"):
        figures["v3-gemini-verdicts.svg"] = v3_gemini_figure(inputs["v3Gemini"])
    if inputs.get("v3Arms"):
        figures["v3-four-reviewers.svg"] = v3_arms_figure(inputs["v3Arms"])
    return figures


def main(argv):
    check = "--check" in argv
    paths = [a for a in argv if not a.startswith("--")]
    output = Path(paths[0]) if paths else DEFAULT_OUTPUT
    figures = build(collect_inputs())
    if check:
        stale = [n for n, svg in figures.items()
                 if not (output / n).is_file() or (output / n).read_text(encoding="utf-8") != svg]
        if stale:
            print(json.dumps({"status": "STALE_FIGURES", "files": stale}))
            return 1
    else:
        output.mkdir(parents=True, exist_ok=True)
        for name, svg in figures.items():
            (output / name).write_text(svg, encoding="utf-8")
    print(json.dumps({"status": "PASS", "figures": sorted(figures), "providerCalls": 0}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
