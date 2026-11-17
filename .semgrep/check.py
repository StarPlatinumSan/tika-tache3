#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
import tomllib
from urllib.request import Request, urlopen


def download_rules(directory, log):
    lock = Path(__file__).with_name("rules.lock.toml")
    with lock.open("rb") as source:
        packs = tomllib.load(source)["packs"]

    options = []
    for index, pack in enumerate(packs):
        request = Request(pack["url"], headers={"User-Agent": "tika-semgrep-ci"})
        with urlopen(request, timeout=30) as response:
            contents = response.read()
        checksum = hashlib.sha256(contents).hexdigest()
        if checksum != pack["sha256"]:
            raise RuntimeError(f"Rule pack {pack['name']} changed. Expected {pack['sha256']}, got {checksum}")
        destination = directory / f"rules-{index}.yml"
        destination.write_bytes(contents)
        options.extend(("--config", str(destination)))
        print(f"Verified {pack['name']} SHA-256 {checksum}", file=log, flush=True)
    return options


def scan(baseline, reports, summary, log):
    if not re.fullmatch(r"[0-9a-f]{40}", baseline) or baseline == "0" * 40:
        raise RuntimeError("GitHub did not provide a usable baseline commit")
    summary["head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    subprocess.run(["git", "cat-file", "-e", f"{baseline}^{{commit}}"], stderr=log, check=True)
    ancestry = subprocess.run(["git", "merge-base", "--is-ancestor", baseline, "HEAD"], stderr=log)
    if ancestry.returncode != 0:
        raise RuntimeError("The baseline is not an ancestor of the checked-out commit")
    print(f"Baseline {baseline}\nHead {summary['head']}", file=log, flush=True)

    semgrep = shutil.which("semgrep")
    if semgrep is None:
        raise RuntimeError("Semgrep is missing from PATH")

    report_path = reports / "semgrep.json"
    with TemporaryDirectory(prefix="tika-semgrep-rules-") as directory:
        rule_options = download_rules(Path(directory), log)
        command = [
            semgrep, "scan", "--experimental", "--baseline-commit", baseline,
            *rule_options, "--no-rewrite-rule-ids", "--metrics=off",
            "--disable-version-check", "--no-autofix", "--use-git-ignore",
            "--max-target-bytes=1000000", "--strict", "--error", "--verbose", "--json", ".",
        ]
        print(f"Command {json.dumps(command)}", file=log, flush=True)
        with report_path.open("wb") as output:
            process = subprocess.run(command, stdout=output, stderr=log, check=False)
        summary["semgrep_exit_code"] = process.returncode

    try:
        report = json.loads(report_path.read_bytes())
    except (UnicodeError, json.JSONDecodeError) as exc:
        report_path.replace(reports / "semgrep.stdout")
        raise RuntimeError(f"Semgrep did not return valid JSON (exit {process.returncode})") from exc

    if not isinstance(report, dict) or any(
        not isinstance(report.get(field), list) for field in ("results", "errors")
    ):
        raise RuntimeError("Semgrep report is missing the results or errors list")
    summary["semgrep_version"] = report.get("version")
    if report["errors"] or report.get("skipped_rules"):
        raise RuntimeError("Semgrep reported scan errors or skipped rules. See semgrep.json")
    count = len(report["results"])
    if process.returncode != int(count > 0):
        raise RuntimeError(f"Semgrep returned exit {process.returncode} with {count} findings")
    return count


def main():
    parser = argparse.ArgumentParser(description="Check for new Semgrep findings against a Git commit.")
    parser.add_argument("baseline")
    parser.add_argument("reports", type=Path)
    args = parser.parse_args()
    args.reports.mkdir(parents=True, exist_ok=True)

    summary = {"baseline": args.baseline, "head": None, "new_findings": None}
    with (args.reports / "semgrep.log").open("w", encoding="utf-8") as log:
        try:
            count = scan(args.baseline, args.reports, summary, log)
        except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
            summary["status"] = "scan_error"
            message = f"Semgrep scan failed. {exc}"
            exit_code = 2
        else:
            summary["status"] = "new_findings" if count else "passed"
            summary["new_findings"] = count
            message = f"New Semgrep findings: {count}"
            exit_code = int(count > 0)
        print(message, file=log)

    summary["message"] = message
    (args.reports / "scan-summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(message)
    if summary_file := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary_file).open("a", encoding="utf-8") as output:
            output.write(f"## Semgrep\n\n{message}\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
