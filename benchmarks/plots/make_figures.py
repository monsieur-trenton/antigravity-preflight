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


def document(width, height, title, description, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}" role="img" aria-labelledby="t d">\n'
            f'<title id="t">{escape(title)}</title><desc id="d">{escape(description)}</desc>\n'
            f'<style>{STYLE}</style>\n'
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
            t(left, 58, f"Route claude-cli, model {pilot['model']}, effort {pilot['effort']}; {len(families) * 4} cases, 2 trials, 0 technical stops, 0 unsupported VERIFIED findings.", "sub muted"),
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


def build(inputs):
    figures = {"fault-gate-matrix.svg": fault_matrix(inputs["results"]),
               "offline-evidence.svg": evidence_overview(inputs)}
    if inputs.get("pilot"):
        figures["pilot1-verdict-matrix.svg"] = pair_matrix(inputs["pilot"])
    if inputs.get("pilot2"):
        figures["pilot2-verdict-matrix.svg"] = pair_matrix(inputs["pilot2"])
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
