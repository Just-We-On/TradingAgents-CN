#!/usr/bin/env python3
"""
Docker部署验证脚本
验证Docker环境是否正确配置，并测试镜像构建

使用方法:
    python scripts/validation/check_docker_setup.py
"""

import os
import sys
import subprocess
import json
from pathlib import Path


def print_step(step_num, message):
    """打印步骤信息"""
    print(f"\n{'='*60}")
    print(f"步骤 {step_num}: {message}")
    print('='*60)


def run_command(cmd, shell=False, capture_output=True):
    """运行命令并返回结果"""
    try:
        if isinstance(cmd, str):
            cmd = cmd.split() if not shell else cmd
        
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=capture_output,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "命令执行超时"
    except Exception as e:
        return False, "", str(e)


def check_docker_installed():
    """检查Docker是否安装"""
    print_step(1, "检查Docker是否安装")
    
    success, stdout, stderr = run_command("docker --version")
    if success:
        print(f"✅ Docker已安装: {stdout.strip()}")
        return True
    else:
        print(f"❌ Docker未安装或未正确配置")
        print(f"   错误信息: {stderr}")
        return False


def check_docker_compose_installed():
    """检查Docker Compose是否安装"""
    print_step(2, "检查Docker Compose是否安装")
    
    # 尝试 docker compose (新版本)
    success, stdout, stderr = run_command("docker compose version")
    if success:
        print(f"✅ Docker Compose已安装: {stdout.strip()}")
        return True
    
    # 尝试 docker-compose (旧版本)
    success, stdout, stderr = run_command("docker-compose --version")
    if success:
        print(f"✅ Docker Compose已安装: {stdout.strip()}")
        print(f"   提示: 您使用的是旧版本的docker-compose，建议升级到docker compose")
        return True
    
    print(f"❌ Docker Compose未安装")
    print(f"   错误信息: {stderr}")
    return False


def check_docker_running():
    """检查Docker是否运行"""
    print_step(3, "检查Docker服务是否运行")
    
    success, stdout, stderr = run_command("docker info")
    if success:
        print(f"✅ Docker服务正在运行")
        # 提取一些有用信息
        lines = stdout.split('\n')
        for line in lines[:10]:
            if any(keyword in line for keyword in ['Server Version', 'Storage Driver', 'Operating System']):
                print(f"   {line.strip()}")
        return True
    else:
        print(f"❌ Docker服务未运行")
        print(f"   错误信息: {stderr}")
        print(f"   请启动Docker Desktop或Docker服务")
        return False


def check_env_file():
    """检查.env文件是否存在"""
    print_step(4, "检查环境配置文件")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print(f"✅ .env文件已创建")
        
        # 检查是否包含关键配置
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_keys = [
            'DEEPSEEK_API_KEY',
            'TUSHARE_TOKEN',
            'DASHSCOPE_API_KEY'
        ]
        
        missing_keys = []
        for key in required_keys:
            # Check if key exists in content
            if key not in content:
                missing_keys.append(key)
                continue
            
            # Check if key has a value after '='
            key_pattern = f'{key}='
            if key_pattern in content:
                parts = content.split(key_pattern, 1)  # Split only once
                if len(parts) > 1:
                    value = parts[1].split('\n')[0].strip()
                    if not value or value.startswith('#'):
                        missing_keys.append(key)
        
        if missing_keys:
            print(f"   ⚠️  以下配置项未设置或为空: {', '.join(missing_keys)}")
            print(f"   提示: 这些配置项是可选的，但建议至少配置一个LLM API密钥")
        else:
            print(f"   所有必要的配置项都已设置")
        
        return True
    elif env_example.exists():
        print(f"❌ .env文件不存在")
        print(f"   请执行: cp .env.example .env")
        print(f"   然后编辑.env文件，填入您的API密钥")
        return False
    else:
        print(f"❌ .env.example文件也不存在，项目文件可能不完整")
        return False


def check_dockerfile():
    """检查Dockerfile是否存在"""
    print_step(5, "检查Dockerfile")
    
    dockerfile = Path("Dockerfile")
    if dockerfile.exists():
        print(f"✅ Dockerfile存在")
        
        # 读取并检查关键内容
        with open(dockerfile, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ('FROM python:3.10', 'Python基础镜像'),
            ('COPY requirements.txt', '依赖文件复制'),
            ('pip install', 'Python包安装'),
            ('streamlit', 'Streamlit安装'),
            ('start-xvfb.sh', 'Xvfb启动脚本'),
        ]
        
        for check_str, description in checks:
            if check_str in content:
                print(f"   ✓ {description}: 已配置")
            else:
                print(f"   ✗ {description}: 未找到")
        
        return True
    else:
        print(f"❌ Dockerfile不存在")
        return False


def check_docker_compose_file():
    """检查docker-compose.yml是否存在"""
    print_step(6, "检查docker-compose.yml")
    
    compose_file = Path("docker-compose.yml")
    if compose_file.exists():
        print(f"✅ docker-compose.yml存在")
        
        # 读取并检查服务配置
        with open(compose_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        services = ['web', 'mongodb', 'redis']
        for service in services:
            if f'{service}:' in content:
                print(f"   ✓ 服务 '{service}': 已配置")
            else:
                print(f"   ✗ 服务 '{service}': 未配置")
        
        return True
    else:
        print(f"❌ docker-compose.yml不存在")
        return False


def provide_recommendations(results):
    """提供修复建议"""
    print("\n" + "="*60)
    print("检查结果汇总")
    print("="*60)
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ 所有检查都通过！您可以开始构建Docker镜像了。")
        print("\n推荐的启动步骤:")
        print("  1. 确保.env文件中已填入API密钥")
        print("  2. 运行: docker-compose up -d --build")
        print("  3. 等待镜像构建完成（首次约5-10分钟）")
        print("  4. 访问: http://localhost:8501")
        print("\n查看日志:")
        print("  docker-compose logs -f web")
        print("\n停止服务:")
        print("  docker-compose down")
    else:
        print("\n❌ 部分检查未通过，请按照以下建议修复:\n")
        
        if not results.get('docker_installed'):
            print("1. 安装Docker:")
            print("   - Windows/Mac: 下载并安装 Docker Desktop")
            print("   - Linux: 参考官方文档 https://docs.docker.com/engine/install/")
        
        if not results.get('docker_compose_installed'):
            print("2. 安装Docker Compose:")
            print("   - 最新版Docker Desktop已内置")
            print("   - Linux单独安装: https://docs.docker.com/compose/install/")
        
        if not results.get('docker_running'):
            print("3. 启动Docker服务:")
            print("   - Windows/Mac: 打开Docker Desktop")
            print("   - Linux: sudo systemctl start docker")
        
        if not results.get('env_file'):
            print("4. 创建并配置.env文件:")
            print("   cp .env.example .env")
            print("   # 然后编辑.env文件，填入API密钥")
        
        if not results.get('dockerfile') or not results.get('docker_compose'):
            print("5. 确保项目文件完整:")
            print("   git clone https://github.com/hsliuping/TradingAgents-CN.git")
    
    print("\n" + "="*60)
    print("如果遇到问题，请查看:")
    print("  - 快速开始指南: QUICKSTART.md")
    print("  - 详细文档: docs/INSTALLATION_GUIDE.md")
    print("  - 提交Issue: https://github.com/hsliuping/TradingAgents-CN/issues")
    print("="*60 + "\n")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("TradingAgents-CN Docker环境验证工具")
    print("="*60)
    
    # 切换到项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent
    os.chdir(project_root)
    
    print(f"\n当前工作目录: {os.getcwd()}")
    
    # 执行检查
    results = {
        'docker_installed': check_docker_installed(),
        'docker_compose_installed': check_docker_compose_installed(),
        'docker_running': check_docker_running(),
        'env_file': check_env_file(),
        'dockerfile': check_dockerfile(),
        'docker_compose': check_docker_compose_file(),
    }
    
    # 提供建议
    provide_recommendations(results)
    
    # 返回状态码
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
