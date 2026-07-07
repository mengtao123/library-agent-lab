pipeline {
    agent any

    environment {
        POLICY_K = '3'
        PYTHONIOENCODING = 'utf-8'
        PATH = "D:\\anaconda;D:\\anaconda\\Scripts;${env.PATH}"
        PYTHONPATH = "${env.WORKSPACE}"
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
                bat '"D:\\anaconda\\Scripts\\pip.exe" install numpy requests'
                echo '✅ 依赖安装完成'
            }
        }

        stage('运行评测') {
            steps {
                echo '🧪 启动微服务并运行评测...'
                bat 'set PYTHONPATH=%WORKSPACE% && start /B D:\\anaconda\\python.exe application/services/reader_service.py'
                bat 'set PYTHONPATH=%WORKSPACE% && start /B D:\\anaconda\\python.exe application/services/book_service.py'
                bat 'set PYTHONPATH=%WORKSPACE% && start /B D:\\anaconda\\python.exe application/services/record_service.py'
                bat 'ping 127.0.0.1 -n 4 > nul'
                bat 'set PYTHONPATH=%WORKSPACE% && chcp 65001 && D:\\anaconda\\python.exe -c "from infrastructure.evaluate import run_eval; run_eval()"'
                echo '✅ 评测通过'
            }
        }

        stage('构建 Docker 镜像') {
    steps {
        echo '🐳 构建 Docker 镜像...'
        bat '"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe" build -f D:\\Github\\library-agent-lab\\Dockerfile -t library-agent:latest D:\\Github\\library-agent-lab'
        echo '✅ Docker 镜像构建完成'
    }
}

        stage('部署服务') {
            steps {
                echo '🚀 启动 Docker 容器...'
                bat '"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe" compose down'
                bat '"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe" compose up -d'
                echo '✅ 部署完成，服务已启动'
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