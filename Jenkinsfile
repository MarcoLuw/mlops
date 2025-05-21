def DOCKER_HUB = "hoanganh26"
def IMAGE_NAME = "python-mlops"
def HOST = "http://43.200.50.207:8080/pipeline"
def NAMESPACE = "kubeflow-user-example-com"
def PIPELINE_NAME = "mlops"
def EXPERIMENT_NAME = "mlops-exp"

pipeline {
    agent any
    
    stages {
        stage('Checkout Code') {
            steps {
                checkout scm
                sh 'ls -la'
            }
        }
        stage('Lint') {
            steps {
                sh 'echo -------------------------------'
                sh 'echo "Lint for testing"'
                sh 'echo -------------------------------'
            }
        }
        stage('Test') {
            steps {
                sh 'echo -------------------------------'
                sh 'echo "Pytest for testing"'
                sh 'echo -------------------------------'
            }
        }
        // stage('Debug Docker') {
        //     steps {
        //         script{
        //             sh 'whoami'
        //             sh 'id'
        //             sh 'ls -l /var/run/docker.sock'
        //             sh 'docker info || echo "Docker failed"'
        //         }
        //     }
        // }
        // stage('Build Python Docker Image') {
        //     steps {
        //         script {
        //             sh 'whoami'
        //             sh "docker rmi ${DOCKER_HUB}/${IMAGE_NAME} || true"
        //             sh "docker build -t ${DOCKER_HUB}/${IMAGE_NAME} ."
        //             sh "echo Build Docker Image Clone"
        //         }
        //     }
        // }
        // stage('Push Docker Images') {
        //     steps {
        //         script {
        //             // Login to Docker Hub using credentials
        //             docker.withRegistry('https://index.docker.io/v1/', 'docker_hub_cred') {
        //                 // Push Docker images to Docker Hub
        //                 sh "docker push ${DOCKER_HUB}/${IMAGE_NAME}"
        //             }
        //             sh "echo Push Docker Image Clone"
        //         }
        //     }
        // }
        stage('Build MLOps Pipeline') {
            steps {
                sh 'python3 components/pipeline.py'
                archiveArtifacts artifacts: 'manifests/bike_sharing_pipeline.yaml', fingerprint: true, allowEmptyArchive: true
            }
        }
        stage('Run Pipeline on Kubeflow') {
            // when {
            //     branch 'main'
            // }
            steps {
                script {
                    sh "python3 utils/run_pipeline.py --host ${HOST} --pipeline_name ${PIPELINE_NAME} --experiment_name ${EXPERIMENT_NAME}"
                }
            }
        }
    }
}