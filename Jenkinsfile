pipeline {
    agent any

    environment {
        POLICY_K = '3'
        PYTHONIOENCODING = 'utf-8'
        PATH = "D:\\anaconda;D:\\anaconda\\Scripts;${env.PATH}"
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
                // 后台启动三个微服务
                bat 'start /B D:\\anaconda\\python.exe application/services/reader_service.py'
                bat 'start /B D:\\anaconda\\python.exe application/services/book_service.py'
                bat 'start /B D:\\anaconda\\python.exe application/services/record_service.py'
                // 等待微服务启动
                bat 'timeout /t 3'
                // 运行评测
                bat 'chcp 65001 && D:\\anaconda\\python.exe -c "from infrastructure.evaluate import run_eval; run_eval()"'
                echo '✅ 评测通过'
            }
        }

        stage('构建 Docker 镜像') {
            steps {
                echo '🐳 构建 Docker 镜像...'
                bat '"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe" build -t library-agent:latest .'
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