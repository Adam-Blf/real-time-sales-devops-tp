pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    environment {
        VENV = "${WORKSPACE}/.venv"
        COMPOSE_PROJECT = 'real-time-sales-devops-tp'
        DOCKER_NETWORK = 'real-time-sales-devops-tp_data-platform'
        // Jenkins tourne dans le réseau de la plateforme : les services se joignent par leur nom compose.
        API_URL = 'http://sales-api:8000'
        KAFKA_BOOTSTRAP_SERVERS = 'kafka:29092'
        POSTGRES_HOST = 'postgres'
        SONAR_HOST_URL = 'http://sonarqube:9000'
        SCANNER_IMAGE = 'sonarsource/sonar-scanner-cli:11'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }

        stage('Install') {
            steps {
                sh '''
                    python3 -m venv "$VENV"
                    "$VENV/bin/pip" install --quiet --upgrade pip
                    "$VENV/bin/pip" install --quiet -r requirements-dev.txt
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    mkdir -p reports
                    "$VENV/bin/python" -m pytest tests/unit \
                      --junitxml=reports/unit.xml \
                      --cov=app --cov-report=term-missing --cov-report=xml:coverage.xml
                '''
            }
        }

        stage('Integration Tests') {
            steps {
                sh '"$VENV/bin/python" -m pytest tests/integration -v --junitxml=reports/integration.xml'
            }
        }

        stage('Build') {
            steps {
                sh 'docker compose -p "$COMPOSE_PROJECT" build sales-api spark-streaming'
            }
        }

        stage('Deploy') {
            steps {
                // Déploie les images tout juste construites, pour que l'E2E valide exactement ce commit.
                sh 'docker compose -p "$COMPOSE_PROJECT" up -d --no-deps sales-api spark-streaming'
            }
        }

        stage('E2E Tests') {
            steps {
                sh '"$VENV/bin/python" -m pytest tests/e2e -v --junitxml=reports/e2e.xml'
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                    // Le scanner tourne dans un conteneur frère : --volumes-from partage le workspace Jenkins.
                    // L'image écrit par défaut dans /tmp/.scannerwork, perdu avec --rm : le Quality Gate a besoin du report-task.txt.
                    sh '''
                        docker run --rm \
                          --network "$DOCKER_NETWORK" \
                          --volumes-from "$(hostname)" \
                          -w "$WORKSPACE" \
                          -u "$(id -u):$(id -g)" \
                          -e SONAR_TOKEN \
                          -e SONAR_HOST_URL \
                          "$SCANNER_IMAGE" \
                          -Dsonar.projectBaseDir="$WORKSPACE" \
                          -Dsonar.working.directory="$WORKSPACE/.scannerwork" \
                          -Dsonar.scm.revision="$(git rev-parse HEAD)"
                    '''
                }
            }
        }

        stage('Quality Gate') {
            steps {
                withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                    sh '"$VENV/bin/python" tools/quality_gate.py .scannerwork/report-task.txt'
                }
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/*.xml'
            archiveArtifacts allowEmptyArchive: true, artifacts: 'coverage.xml, reports/*.xml'
        }
        success {
            echo 'Pipeline OK: tests green and Quality Gate passed.'
        }
        failure {
            echo 'Pipeline STOP: a test level or the Quality Gate failed.'
        }
    }
}
