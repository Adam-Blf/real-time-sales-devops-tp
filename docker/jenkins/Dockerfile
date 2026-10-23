FROM jenkins/jenkins:lts-jdk17

USER root

# Le CLI Docker et le plugin compose viennent du dépôt Docker : le docker.io de Debian n'a pas `docker compose`.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg git python3 python3-venv \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
       > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

COPY docker/jenkins/plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Hors de /var/jenkins_home : ce dossier est un volume, qui masquerait le fichier de l image.
COPY docker/jenkins/casc.yaml /opt/jenkins-casc/casc.yaml
ENV CASC_JENKINS_CONFIG=/opt/jenkins-casc/casc.yaml

RUN python3 --version && docker --version && docker compose version

USER jenkins
