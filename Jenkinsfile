pipeline {
    agent any
    triggers {
        githubPush()
    }

    environment {
        IMAGE_NAME = 'docker-dashboard'
        IMAGE_TAG = "latest"
        BUILD_TAG = "${env.BUILD_NUMBER}"
        
        FULL_IMAGE = "${IMAGE_NAME}:${IMAGE_TAG}"
        BUILD_IMAGE = "${IMAGE_NAME}:${BUILD_TAG}"
        
        // DockerHub credentials ID in Jenkins
        DOCKERHUB_CRED = 'DOCKER_HUB'
        
        // Private registry credentials ID
        PRIVATE_REG_CRED = 'nexus_registry_login'
        
        // SSH credentials ID for remote server
        SSH_CRED = 'DEBIANSERVER'
        
        REMOTE_HOST = '192.168.88.22'
        REMOTE_USER = 'funmicra'
        
        // Namespaces / repos
        DOCKERHUB_REPO = 'funmicra/docker-dashboard'
        PRIVATE_REG_REPO = 'registry.black-crab.cc/docker-dashboard'
    }

    triggers {
        githubPush()
    }

    stages {
        stage('Checkout') {
            steps {
                git url: 'https://github.com/funmicra/docker-dashboard.git', branch: 'master'
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                docker build -t ${FULL_IMAGE} .
                docker tag ${FULL_IMAGE} ${BUILD_IMAGE}
                """
            }
        }

        stage('Push to DockerHub') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', DOCKER_HUB) {
                        sh """
                        docker tag ${FULL_IMAGE} ${DOCKERHUB_REPO}:${IMAGE_TAG}
                        docker tag ${FULL_IMAGE} ${DOCKERHUB_REPO}:${BUILD_TAG}
                        docker push ${DOCKERHUB_REPO}:${IMAGE_TAG}
                        docker push ${DOCKERHUB_REPO}:${BUILD_TAG}
                        """
                    }
                }
            }
        }

        stage('Push to Private Registry') {
            steps {
                script {
                    docker.withRegistry('https://registry.black-crab.cc', nexus_registry_login) {
                        sh """
                        docker tag ${FULL_IMAGE} ${PRIVATE_REG_REPO}:${IMAGE_TAG}
                        docker tag ${FULL_IMAGE} ${PRIVATE_REG_REPO}:${BUILD_TAG}
                        docker push ${PRIVATE_REG_REPO}:${IMAGE_TAG}
                        docker push ${PRIVATE_REG_REPO}:${BUILD_TAG}
                        """
                    }
                }
            }
        }

        stage('Deploy to Remote Server') {
            steps {
                script {
                    sshagent([SSH_CRED]) {
                        sh """
                        ssh -o StrictHostKeyChecking=no ${REMOTE_USER}@${REMOTE_HOST} '
                            docker pull ${PRIVATE_REG_REPO}:${IMAGE_TAG} &&
                            docker stop ${IMAGE_NAME} || true &&
                            docker rm ${IMAGE_NAME} || true &&
                            docker run -d --name ${IMAGE_NAME} -v /var/run/docker.sock:/var/run/docker.sock ${PRIVATE_REG_REPO}:${IMAGE_TAG}
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
