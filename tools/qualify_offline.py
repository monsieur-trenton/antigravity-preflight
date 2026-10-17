"""Run the retained 332-case harness twice; never call a real native runtime."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def pin(path):
    data = path.read_bytes()
    return dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def main(destination):
    destination = destination.absolute()
    if destination.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("OUTPUT_MUST_BE_OUTSIDE_REPOSITORY")
    destination.mkdir(parents=True, exist_ok=False)
    package = ROOT / "runtime/flash-high"
    runtime_pins = json.loads((ROOT / "qualification/runtime-pins.json").read_bytes())["packageFiles"]
    for name, expected in runtime_pins.items():
        if pin(package / name) != expected:
            raise ValueError("RUNTIME_PIN")
    runs = []
    for number in (1, 2):
        output = destination / f"run-{number}"
        command = [sys.executable, "-B", "-I", str(package / "scripts/qualify_cli_launcher.py"), str(output)]
        process = subprocess.run(command, capture_output=True, timeout=360)
        (destination / f"run-{number}.stdout").write_bytes(process.stdout)
        (destination / f"run-{number}.stderr").write_bytes(process.stderr)
        if process.returncode:
            raise ValueError(f"OFFLINE_RUN_{number}_STOPPED")
        result = json.loads((output / "RESULT.json").read_bytes())
        if result["status"] != "PASS" or result["totalCases"] != 332 or result["sourcePackageCustody"] != "EXACT":
            raise ValueError(f"OFFLINE_RUN_{number}_RESULT")
        runs.append(dict(id=f"run-{number}", status="PASS", cases=332,
                         result=pin(output / "RESULT.json"), suites=result["suites"]))
        print(json.dumps(dict(run=number, status="PASS", cases=332)), flush=True)
    result = dict(status="PASS", scope="OFFLINE_ONLY", twoFreshRuns=True,
                  packageFiles=runtime_pins, casesPerRun=332, totalCases=664, runs=runs,
                  sharedImplementationAndHost=True, nativeCalls=0, proxyCalls=0,
                  providerCalls=0, generativeCalls=0, qualificationCredit=0,
                  limits="Synthetic process/transport doubles only; no native qualification or owner authorization.")
    (destination / "DUAL-OFFLINE-QUALIFICATION.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(status="PASS", runs=2, totalCases=664, nativeCalls=0, providerCalls=0)))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 -B -I tools/qualify_offline.py <new-output-directory>")
    main(Path(sys.argv[1]))
