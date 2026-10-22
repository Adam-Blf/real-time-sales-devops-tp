"""Captures de terminal pour le rapport.

Chaque capture exécute réellement ses commandes, puis rend la sortie obtenue dans une
fenêtre de terminal (HTML + Chrome headless). Rien n'est saisi à la main.
Prérequis : plateforme Docker Compose démarrée et cluster Minikube avec le namespace sales.
Usage : python docs/rapport/terminal.py [nom ...]
"""

import html
import re
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "figures"
PY = ".venv/Scripts/python"
GIT_BASH = r"C:\Program Files\Git\bin\bash.exe"
FORWARD_PORT = 8001  # le port 8000 est déjà pris par l'API du compose

STYLE = """
body { margin: 0; padding: 18px; background: #ffffff; }
.win { width: 1000px; border-radius: 10px; overflow: hidden; background: #051832;
       box-shadow: 0 6px 24px rgba(5, 24, 50, .28); }
.bar { height: 30px; background: #163767; display: flex; align-items: center; padding: 0 12px; }
.dot { width: 11px; height: 11px; border-radius: 50%; margin-right: 7px; }
.title { color: #c9d4e6; font: 12px 'Segoe UI', sans-serif; margin-left: 14px; }
pre { margin: 0; padding: 14px 16px 16px; color: #e6edf7; white-space: pre-wrap;
      word-break: break-all; font: 12.5px/1.45 'Cascadia Mono', Consolas, monospace; }
.p { color: #ff43b8; } .d { color: #5fb4ea; } .c { color: #ffffff; font-weight: 600; }
.ok { color: #4ade80; } .ko { color: #f87171; } .mute { color: #8a9bb8; }
"""


def run(cmd, timeout=600):
    # Chemin absolu : sous Windows, « bash » seul résout vers le bash de WSL, pas vers Git Bash.
    done = subprocess.run([GIT_BASH, "-c", cmd], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)
    return (done.stdout + done.stderr).rstrip("\n")


def colorize(line):
    text = html.escape(line)
    if re.search(r"\b(FAILED|ERROR|Failed)\b|STOP", line):
        return f'<span class="ko">{text}</span>'
    if re.search(r"\bPASSED\b|\bpassed\b|Quality Gate: OK|\[OK\]|Pipeline OK|Running|condition met|"
                 r"successfully|SUCCESS", line):
        return f'<span class="ok">{text}</span>'
    return text


def render(page, name, title, steps, prompt=("adam@efrei", "~/real-time-sales-devops-tp")):
    body = []
    for shown, output in steps:
        body.append(f'<span class="p">{prompt[0]}</span> <span class="d">{prompt[1]}</span>'
                    f' <span class="mute">$</span> <span class="c">{html.escape(shown)}</span>')
        body.extend(colorize(line) for line in output.splitlines())
        body.append("")
    doc = (f"<html><head><style>{STYLE}</style></head><body><div class='win'><div class='bar'>"
           "<span class='dot' style='background:#ff5f57'></span>"
           "<span class='dot' style='background:#febc2e'></span>"
           "<span class='dot' style='background:#28c840'></span>"
           f"<span class='title'>{html.escape(title)}</span></div>"
           f"<pre>{chr(10).join(body).rstrip()}</pre></div></body></html>")
    page.set_content(doc)
    page.locator(".win").screenshot(path=str(OUT / f"term-{name}.png"))
    print("capture", f"term-{name}.png")


def tail(text, n):
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def strip_pytest_noise(text):
    # Les avertissements de dépréciation de pytest n'apportent rien au lecteur.
    keep, skipping = [], False
    for line in text.splitlines():
        if line.startswith("=") and "warnings summary" in line:
            skipping = True
            continue
        if skipping and line.startswith("-- Docs"):
            skipping = False
            continue
        if not skipping:
            keep.append(line)
    return "\n".join(keep)


def unit():
    out = run(f"{PY} -m pytest tests/unit -q -p no:cacheprovider --cov=app --cov-report=term-missing")
    return [("pytest tests/unit -q --cov=app --cov-report=term-missing", strip_pytest_noise(out))]


def integration():
    out = run(f"{PY} -m pytest tests/integration tests/e2e -v -p no:cacheprovider")
    out = "\n".join(l for l in strip_pytest_noise(out).splitlines()
                    if not l.startswith(("platform ", "cachedir", "rootdir", "configfile", "plugins")))
    return [("pytest tests/integration tests/e2e -v", out.strip())]


def compose():
    out = run("docker compose ps --format 'table {{.Name}}\\t{{.Image}}\\t{{.Status}}'")
    return [("docker compose ps", out)]


def jenkins_gate():
    log = (ROOT / "docs/evidence/jenkins-build-5.log").read_text(encoding="utf-8")
    log = re.sub(r"^\[[0-9T:.\-Z]+\] ", "", log, flags=re.M)
    start = log.index("Quality Gate:")
    block = log[start:log.index("Finished:", start) + len("Finished: SUCCESS")]
    lines = [l for l in block.splitlines() if not l.startswith("[Pipeline]") and "Masking" not in l
             and "Recording" not in l and "Checks API" not in l and "Archiving" not in l]
    return [('"$VENV/bin/python" tools/quality_gate.py .scannerwork/report-task.txt',
             "\n".join(lines))]


def k8s_state():
    return [("kubectl get nodes", run("kubectl get nodes")),
            ("kubectl -n sales get deployments,services",
             run("kubectl -n sales get deployments,services"))]


def k8s_flow():
    forward = subprocess.Popen(["kubectl", "-n", "sales", "port-forward", "service/sales-api",
                                f"{FORWARD_PORT}:8000"], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    try:
        payload = '{"customer_id":"C100","product_id":"P001","quantity":3,"unit_price":100}'
        health = ""
        for _ in range(30):  # attend que le port-forward accepte les connexions
            health = run(f"curl -s localhost:{FORWARD_PORT}/api/health")
            if '"UP"' in health:
                break
            time.sleep(1)
        posted = run(f"curl -s -X POST localhost:{FORWARD_PORT}/api/orders "
                     f"-H 'Content-Type: application/json' -d '{payload}'")
        order_id = re.search(r'"order_id":"([^"]+)"', posted).group(1)
        query = ("select order_id, customer_id, product_id, quantity, total_amount "
                 f"from processed_orders where order_id='{order_id}';")
        row = ""
        for _ in range(30):  # Spark écrit en micro-batch : on attend la ligne au lieu d'un délai fixe
            row = run(f'kubectl -n sales exec deploy/postgres -- psql -U sales -d sales -c "{query}"')
            if order_id in row:
                break
            time.sleep(2)
    finally:
        forward.terminate()
    return [(f"kubectl -n sales port-forward service/sales-api {FORWARD_PORT}:8000 &", ""),
            (f"curl localhost:{FORWARD_PORT}/api/health", health),
            (f"curl -X POST localhost:{FORWARD_PORT}/api/orders -d '{payload}'", posted),
            (f'kubectl -n sales exec deploy/postgres -- psql -U sales -d sales -c "{query}"', row)]


def k8s_scale():
    steps = [("kubectl -n sales scale deployment/sales-api --replicas=3",
              run("kubectl -n sales scale deployment/sales-api --replicas=3"))]
    run("kubectl -n sales rollout status deployment/sales-api --timeout=120s")
    steps.append(("kubectl -n sales get pods -l app=sales-api -o wide",
                  run("kubectl -n sales get pods -l app=sales-api -o wide")))
    steps.append(("kubectl -n sales get deployment sales-api",
                  run("kubectl -n sales get deployment sales-api")))
    steps.append(("kubectl -n sales scale deployment/sales-api --replicas=1",
                  run("kubectl -n sales scale deployment/sales-api --replicas=1")))
    return steps


def k8s_heal():
    run("kubectl -n sales rollout status deployment/sales-api --timeout=120s")
    time.sleep(20)  # laisse disparaître les Pods en trop du test de scaling
    pod = run("kubectl -n sales get pods -l app=sales-api -o jsonpath='{.items[0].metadata.name}'")
    before = run("kubectl -n sales get pods -l app=sales-api")
    watch = subprocess.Popen(["kubectl", "-n", "sales", "get", "pods", "-l", "app=sales-api", "-w",
                              "--output-watch-events"], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
    time.sleep(2)
    deleted = run(f"kubectl -n sales delete pod {pod}")
    time.sleep(20)
    watch.terminate()
    events = watch.communicate()[0].rstrip()
    return [("kubectl -n sales get pods -l app=sales-api", before),
            (f"kubectl -n sales delete pod {pod}", deleted),
            ("kubectl -n sales get pods -l app=sales-api -w --output-watch-events", events)]


# La capture du Quality Gate reprend la console Jenkins : l'invite le dit.
PROMPTS = {"gate": ("jenkins@sales-jenkins", "workspace/real-time-sales-pipeline")}

CAPTURES = {
    "unit": ("bash, tests unitaires", unit),
    "integration": ("bash, tests d'intégration et E2E", integration),
    "compose": ("bash, plateforme Docker Compose", compose),
    "gate": ("Console Jenkins, build #5, étape Quality Gate", jenkins_gate),
    "k8s-state": ("bash, cluster Minikube", k8s_state),
    "k8s-flow": ("bash, test du flux dans le cluster", k8s_flow),
    "k8s-scale": ("bash, mise à l'échelle", k8s_scale),
    "k8s-heal": ("bash, suppression d'un Pod", k8s_heal),
}


def main(names):
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(device_scale_factor=2)
        for name in names or CAPTURES:
            title, producer = CAPTURES[name]
            prompt = PROMPTS.get(name, ("adam@efrei", "~/real-time-sales-devops-tp"))
            render(page, name, title, producer(), prompt)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
