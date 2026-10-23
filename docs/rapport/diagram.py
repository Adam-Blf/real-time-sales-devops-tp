"""Schémas d'architecture du rapport, rendus en HTML puis capturés par Chrome headless.

Usage : python docs/rapport/diagram.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "figures"

BASE = """
body { margin: 0; padding: 16px; background: #fff; font-family: 'Segoe UI', sans-serif; }
.frame { width: 980px; padding: 22px 24px; border: 1px solid #d6dde8; border-radius: 12px; }
.row { display: flex; align-items: center; justify-content: space-between; }
.box { width: 170px; padding: 12px 10px; border-radius: 9px; text-align: center; color: #fff;
       background: #163767; box-shadow: 0 2px 6px rgba(5,24,50,.18); }
.box b { display: block; font-size: 15px; } .box span { font-size: 12px; opacity: .85; }
.box.data { background: #0c78b4; } .box.ci { background: #051832; }
.box.ok { background: #16966e; } .box.ko { background: #c82846; }
.arrow { flex: 1; text-align: center; color: #ff43b8; font-size: 12px; position: relative; }
.arrow:after { content: ""; display: block; height: 2px; background: #ff43b8; margin: 4px 6px 0; }
.arrow.tip:before { content: "\\25B6"; position: absolute; right: 0; bottom: -8px; font-size: 11px; }
.lane { font-size: 12px; font-weight: 700; color: #163767; letter-spacing: .06em;
        text-transform: uppercase; margin: 2px 0 10px; }
.sep { height: 1px; background: #d6dde8; margin: 20px 0 16px; }
.k8s { border: 2px dashed #0c78b4; border-radius: 12px; padding: 16px 14px 14px; margin-top: 8px; }
.ns { font-size: 12px; color: #0c78b4; font-weight: 700; margin-bottom: 10px; }
.box.small { width: 112px; padding: 10px 6px; } .box.small b { font-size: 14px; }
.arrow { white-space: nowrap; min-width: 64px; font-size: 11px; }
.svc { font-size: 11px; color: #163767; background: #eef3fa; border-radius: 6px;
       padding: 3px 6px; margin-top: 6px; display: inline-block; }
"""


def box(title, sub, kind=""):
    return f'<div class="box {kind}"><b>{title}</b><span>{sub}</span></div>'


def arrow(label=""):
    return f'<div class="arrow tip">{label}</div>'


PIPELINE = f"""
<div class="frame">
  <div class="lane">Flux de données</div>
  <div class="row">{box("Sales API", "FastAPI")}{arrow("POST /api/orders")}
    {box("Kafka", "topic sales.orders", "data")}{arrow("lecture")}
    {box("PySpark", "Structured Streaming")}{arrow("INSERT idempotent")}
    {box("PostgreSQL", "processed_orders", "data")}</div>
  <div class="sep"></div>
  <div class="lane">Chaîne de contrôle, à chaque commit</div>
  <div class="row">{box("Git", "branche dev", "ci")}{arrow("poll SCM")}
    {box("Jenkins", "tests, build, E2E", "ci")}{arrow("analyse")}
    {box("SonarQube", "Quality Gate", "ci")}{arrow("")}
    <div style="width:170px">{box("Pipeline OK", "Gate validé", "ok")}
      <div style="height:8px"></div>{box("Pipeline STOP", "Gate en échec", "ko")}</div></div>
</div>
"""

KUBERNETES = f"""
<div class="frame">
  <div class="row" style="align-items:stretch">
    <div style="display:flex;align-items:center">{box("Poste local", "curl, navigateur", "ci small")}</div>
    <div style="display:flex;align-items:center;flex:1">{arrow("port-forward")}</div>
    <div class="k8s" style="flex:none;width:690px;margin-top:0">
      <div class="ns">Cluster Minikube, namespace sales</div>
      <div class="row">
        <div style="text-align:center">{box("sales-api", "1 à 3 Pods", "small")}
          <span class="svc">Service :8000</span></div>{arrow("")}
        <div style="text-align:center">{box("Kafka", "+ ZooKeeper", "data small")}
          <span class="svc">Job kafka-init</span></div>{arrow("")}
        <div style="text-align:center">{box("Spark", "local[2]", "small")}
          <span class="svc">PVC checkpoints</span></div>{arrow("")}
        <div style="text-align:center">{box("PostgreSQL", "+ PVC", "data small")}
          <span class="svc">Service :5432</span></div>
      </div>
      <div style="margin-top:14px;font-size:12px;color:#163767">ConfigMap sales-config (hôtes, topic, base)
        &nbsp;|&nbsp; Secret postgres-credentials, créé hors Git</div>
    </div>
  </div>
</div>
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        page = browser.new_page(device_scale_factor=2)
        for name, body in (("schema-pipeline.png", PIPELINE), ("schema-kubernetes.png", KUBERNETES)):
            page.set_content(f"<html><head><style>{BASE}</style></head><body>{body}</body></html>")
            page.locator(".frame").screenshot(path=str(OUT / name))
            print("schéma", name)
        browser.close()


if __name__ == "__main__":
    main()
