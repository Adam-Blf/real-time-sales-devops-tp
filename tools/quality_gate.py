"""Attend la fin de l'analyse SonarQube, affiche le Quality Gate et fait échouer le build s'il n'est pas OK.

Usage: python tools/quality_gate.py .scannerwork/report-task.txt
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sonar_client import SonarClient  # noqa: E402

TIMEOUT_SECONDS = 300
POLL_SECONDS = 3


def read_report_task(path):
    with open(path, encoding="utf-8") as handle:
        return dict(line.strip().split("=", 1) for line in handle if "=" in line)


def wait_for_analysis(client, task_id):
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        task = client.get("/api/ce/task", id=task_id)["task"]
        if task["status"] in ("SUCCESS", "FAILED", "CANCELED"):
            return task
        time.sleep(POLL_SECONDS)
    raise TimeoutError(f"SonarQube task {task_id} not finished after {TIMEOUT_SECONDS}s")


def main(report_path):
    report = read_report_task(report_path)
    client = SonarClient(base_url=os.getenv("SONAR_HOST_URL", report.get("serverUrl")),
                         token=os.environ["SONAR_TOKEN"])

    task = wait_for_analysis(client, report["ceTaskId"])
    if task["status"] != "SUCCESS":
        print(f"Analysis {task['status']}: {task.get('errorMessage', '')}")
        return 1

    status = client.get("/api/qualitygates/project_status", analysisId=task["analysisId"])["projectStatus"]
    print(f"Quality Gate: {status['status']}")
    for condition in status.get("conditions", []):
        print(f"  [{condition['status']}] {condition['metricKey']} {condition['comparator']} "
              f"{condition['errorThreshold']} (actual {condition.get('actualValue', '-')})")
    print(f"Dashboard: {report.get('dashboardUrl', '')}")
    return 0 if status["status"] == "OK" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ".scannerwork/report-task.txt"))
