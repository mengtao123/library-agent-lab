pipeline {
    agent any

    environment {
        POLICY_K = '3'
    }

    stages {
        stage('代码拉取') {
            steps {
                echo '📦 拉取代码...'
                checkout scm
                echo '✅ 代码拉取完成'
            }
        }

        stage('安装依赖') {
            steps {
                echo '📦 安装依赖...'
                bat 'pip install numpy requests'
                echo '✅ 依赖安装完成'
            }
        }

        stage('运行评测') {
            steps {
                echo '🧪 运行评测...'
                bat 'python -c "from infrastructure.evaluate import run_eval; run_eval()"'
                echo '✅ 评测通过'
            }
        }

        stage('构建 Docker 镜像') {
            steps {
                echo '🐳 构建 Docker 镜像...'
                bat 'docker build -t library-agent:latest .'
                echo '✅ Docker 镜像构建完成'
            }
        }
    }

    post {
        success {
            echo '🎉 流水线全部成功！'
        }
        failure {
            echo '❌ 流水线失败，请检查日志。'
        }
    }
}