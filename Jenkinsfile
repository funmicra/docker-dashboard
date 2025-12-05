pipeline {
    agent any

    environment {
        // Docker image name & tags
        IMAGE_NAME = 'docker-dashboard'
        IMAGE_TAG = "latest"
        
        // DockerHub credentials ID in Jenkins
        DOCKERHUB_CRED = 'DOCKER_HUB'
        
        // Private registry credentials ID
        PRIVATE_REG_CRED = 'nexus_registry_login'
        
        // SSH credentials ID for remote server
        SSH_CRED = 'DEBIANSERVER'
        
        // Remote server info
        REMOTE_HOST = '192.168.88.22'
        REMOTE_USER = 'funmicra'
    }

    triggers {
        // Trigger on GitHub push
        githubPush()
    }

    stages {
        stage('Checkout') {
            steps {
                git url: 'https://github.com/yourusername/yourrepo.git', branch: 'master'
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    docker.build("${IMAGE_NAME}:latest")
                }
            }
        }

        stage('Push to DockerHub') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', DOCKERHUB_CRED) {
                        docker.image("${IMAGE_NAME}:${IMAGE_TAG}").push()
                    }
                }
            }
        }

        stage('Push to Private Registry') {
            steps {
                script {
                    docker.withRegistry('https://registry.black-crab.cc', PRIVATE_REG_CRED) {
                        docker.image("${IMAGE_NAME}:${IMAGE_TAG}").push()
                    }
                }
            }
        }

        stage('Deploy to Remote Server') {
            steps {
                script {
                    sshagent([SSH_CRED]) {
                        // Pull the new image on remote server
                        sh """
                        ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} '
                            docker pull registry.black-crab.cc/${IMAGE_NAME}:${IMAGE_TAG} &&
                            docker stop ${IMAGE_NAME} || true &&
                            docker rm ${IMAGE_NAME} || true &&
                            docker run -d --name ${IMAGE_NAME} -v /var/run/docker.sock:/var/run/docker.sock registry.black-crab.cc/${IMAGE_NAME}:${IMAGE_TAG}
                        '
                        """
                    }
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline finished successfully!"
        }
        failure {
            echo "Pipeline failed!"
        }
    }
}
