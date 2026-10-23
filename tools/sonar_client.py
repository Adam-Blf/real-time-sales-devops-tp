"""Client minimal de l'API Web SonarQube (bibliothèque standard seule, utilisable depuis Jenkins et le poste)."""

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request

HTTPError = urllib.error.HTTPError


class SonarClient:
    def __init__(self, base_url=None, token=None, login=None, password=None):
        self.base_url = (base_url or os.getenv("SONAR_HOST_URL", "http://localhost:9000")).rstrip("/")
        credentials = f"{token}:" if token else f"{login}:{password}"
        self.auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()

    def call(self, method, path, **params):
        url = f"{self.base_url}{path}"
        encoded = urllib.parse.urlencode(params)
        data = None
        if method == "GET" and encoded:
            url = f"{url}?{encoded}"
        elif encoded:
            data = encoded.encode()
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Authorization", self.auth_header)
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read()
        return json.loads(body) if body else {}

    def get(self, path, **params):
        return self.call("GET", path, **params)

    def post(self, path, **params):
        return self.call("POST", path, **params)
