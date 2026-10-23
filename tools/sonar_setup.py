"""Configure une fois le SonarQube local : projet, Quality Gate et jeton d'analyse pour Jenkins.

Usage: python tools/sonar_setup.py
Env:   SONAR_HOST_URL (défaut http://localhost:9000),
       SONAR_ADMIN_LOGIN / SONAR_ADMIN_PASSWORD (défaut admin/admin, le compte d'une installation neuve)
Le jeton est écrit dans .env (ignoré par git) sous SONAR_TOKEN, d'où docker compose le transmet à Jenkins.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sonar_client import HTTPError, SonarClient  # noqa: E402

PROJECT_KEY = "real-time-sales-devops"
PROJECT_NAME = "Real-Time Sales DevOps TP"
GATE_NAME = "Data Pipeline Gate"
TOKEN_NAME = "jenkins"
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

# Conditions sur le code global : le TP demande des seuils absolus sur tout le projet.
CONDITIONS = [
    ("coverage", "LT", "80"),                 # couverture >= 80 %
    ("bugs", "GT", "0"),                      # bugs = 0
    ("vulnerabilities", "GT", "0"),           # vulnérabilités = 0
    ("duplicated_lines_density", "GT", "3"),  # duplications <= 3 %
]


def wait_until_up(client, timeout=300):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if client.get("/api/system/status")["status"] == "UP":
                return
        except (OSError, HTTPError, KeyError):
            pass
        time.sleep(5)
    raise TimeoutError("SonarQube did not come up")


def ensure_project(client):
    if not client.get("/api/projects/search", projects=PROJECT_KEY)["components"]:
        client.post("/api/projects/create", project=PROJECT_KEY, name=PROJECT_NAME)
        print(f"Project {PROJECT_KEY} created")


def ensure_gate(client):
    gates = {gate["name"] for gate in client.get("/api/qualitygates/list")["qualitygates"]}
    if GATE_NAME not in gates:
        client.post("/api/qualitygates/create", name=GATE_NAME)
        print(f"Quality Gate '{GATE_NAME}' created")
    for condition in client.get("/api/qualitygates/show", name=GATE_NAME).get("conditions", []):
        client.post("/api/qualitygates/delete_condition", id=condition["id"])
    for metric, operator, threshold in CONDITIONS:
        client.post("/api/qualitygates/create_condition", gateName=GATE_NAME,
                    metric=metric, op=operator, error=threshold)
    client.post("/api/qualitygates/select", gateName=GATE_NAME, projectKey=PROJECT_KEY)
    print(f"Quality Gate '{GATE_NAME}' bound to {PROJECT_KEY} with {len(CONDITIONS)} conditions")


def write_token(client):
    try:
        client.post("/api/user_tokens/revoke", name=TOKEN_NAME)
    except HTTPError:
        pass
    token = client.post("/api/user_tokens/generate", name=TOKEN_NAME,
                        type="PROJECT_ANALYSIS_TOKEN", projectKey=PROJECT_KEY)["token"]
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, encoding="utf-8") as handle:
            lines = [line for line in handle if not line.startswith("SONAR_TOKEN=")]
    lines.append(f"SONAR_TOKEN={token}\n")
    with open(ENV_FILE, "w", encoding="utf-8") as handle:
        handle.writelines(lines)
    print(f"Analysis token written to {ENV_FILE}")


def main():
    client = SonarClient(login=os.getenv("SONAR_ADMIN_LOGIN", "admin"),
                         password=os.getenv("SONAR_ADMIN_PASSWORD", "admin"))
    wait_until_up(client)
    ensure_project(client)
    ensure_gate(client)
    write_token(client)


if __name__ == "__main__":
    main()
