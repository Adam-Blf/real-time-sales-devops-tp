"""Captures réelles de Jenkins et SonarQube pour le rapport.

Les mots de passe sont lus dans .env et ne sont jamais affichés.
Usage : python docs/rapport/capture.py   (stack Jenkins + SonarQube démarrée)
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "figures"
JENKINS = "http://localhost:8082"
SONAR = "http://localhost:9000"
JOB = "real-time-sales-pipeline"


def read_env():
    values = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def shot(page, name, height=900):
    # Recadrage sur la zone utile : le bas des pages Jenkins est vide.
    page.screenshot(path=str(OUT / name), clip={"x": 0, "y": 0, "width": 1440, "height": height})
    print("capture", name)


def jenkins(page, password):
    page.goto(f"{JENKINS}/login")
    page.fill("#j_username", "admin")
    page.fill("input[name=j_password]", password)
    page.press("input[name=j_password]", "Enter")
    page.wait_for_url(f"{JENKINS}/**")
    page.goto(f"{JENKINS}/job/{JOB}/")
    page.wait_for_load_state("networkidle")
    shot(page, "jenkins-job.png", 690)
    page.goto(f"{JENKINS}/job/{JOB}/3/testReport/")
    page.wait_for_load_state("networkidle")
    shot(page, "jenkins-tests.png", 660)


def sonar(page, password):
    page.goto(f"{SONAR}/sessions/new")
    page.fill("input[name=login]", "admin")
    page.fill("input[name=password]", password)
    page.press("input[name=password]", "Enter")
    page.wait_for_url(lambda url: "/sessions/new" not in url)
    for key, name in (("real-time-sales-devops", "sonar-apres.png"),
                      ("real-time-sales-devops-baseline", "sonar-avant.png")):
        page.goto(f"{SONAR}/dashboard?id={key}&codeScope=overall")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2500)
        # Fenêtres promotionnelles de SonarQube Community, sans rapport avec l'analyse
        banner = page.locator("[role=alert] button, .it__banner button").first
        if banner.count():
            banner.click()
        page.wait_for_timeout(500)
        # Recadrage au-dessus de l'encart promotionnel, qui ne se ferme pas de façon fiable :
        # la note du Quality Gate, les problèmes, la couverture et les duplications tiennent dans cette zone.
        shot(page, name, 700)


def main():
    env = read_env()
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")  # Chrome du poste, pas de téléchargement
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
        jenkins(page, env["JENKINS_ADMIN_PASSWORD"])
        sonar(page, env["SONAR_ADMIN_PASSWORD"])
        browser.close()


if __name__ == "__main__":
    main()
