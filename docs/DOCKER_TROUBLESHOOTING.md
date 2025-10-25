# Docker部署问题排查指南

本文档记录常见的Docker部署问题及其解决方案。

## 常见问题

### 1. "No module named streamlit" 错误

**症状:**
```
/usr/local/bin/python: No module named streamlit
```

**原因:**
- 依赖安装过程失败
- 网络问题导致pip安装中断
- 使用了不兼容的镜像源

**解决方案:**
1. 确保使用最新的Dockerfile（已优化多源轮询安装）
2. 重新构建镜像，确保完整安装:
   ```bash
   docker-compose build --no-cache
   docker-compose up -d
   ```
3. 检查构建日志，确认streamlit是否成功安装:
   ```bash
   docker-compose build web 2>&1 | grep -i streamlit
   ```

### 2. "Server is already active for display 99" 错误

**症状:**
```
Fatal server error:
(EE) Server is already active for display 99
If this server is no longer running, remove /tmp/.X99-lock
and start again.
```

**原因:**
- Xvfb虚拟显示器启动脚本没有处理已存在的X server进程
- 容器重启时遗留的锁文件

**解决方案:**
已在最新的Dockerfile中修复。start-xvfb.sh脚本现在会:
1. 自动删除过期的锁文件 (`/tmp/.X99-lock`)
2. 终止现有的Xvfb进程
3. 等待2秒确保Xvfb完全启动

如果仍然遇到此问题，请手动清理:
```bash
# 进入容器
docker-compose exec web bash

# 删除锁文件
rm -f /tmp/.X99-lock

# 终止Xvfb进程
pkill -f "Xvfb :99"

# 退出容器
exit

# 重启服务
docker-compose restart web
```

### 3. "pull access denied for tradingagents-cn" 错误

**症状:**
```
! web Warning pull access denied for tradingagents-cn, repository does not exist or may require 'docker login'
```

**原因:**
- Docker Compose尝试从远程仓库拉取镜像，但镜像只存在于本地
- 首次运行时没有使用 `--build` 参数

**解决方案:**
使用正确的启动命令:
```bash
# 首次启动或代码更新后
docker-compose up -d --build

# 或者分步执行
docker build -t tradingagents-cn:latest .
docker-compose up -d
```

### 4. 依赖安装失败或超时

**症状:**
- 构建过程中pip安装卡住
- 显示网络超时错误
- 某些包安装失败

**解决方案:**
1. Dockerfile已配置多个镜像源自动轮询:
   - 阿里云镜像 (主要)
   - 清华大学镜像 (备用)
   - 豆瓣镜像 (备用)
   - PyPI官方源 (最后备用)

2. 如果仍然失败，可以手动指定镜像源:
   ```dockerfile
   # 在Dockerfile中修改
   RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

3. 对于国内用户，建议配置Docker镜像加速:
   ```json
   {
     "registry-mirrors": [
       "https://registry.docker-cn.com",
       "https://docker.mirrors.ustc.edu.cn"
     ]
   }
   ```

### 5. 健康检查失败

**症状:**
```
docker-compose ps
# 显示 web 服务状态为 unhealthy
```

**原因:**
- curl命令未安装
- Streamlit应用启动失败
- 端口8501未正确监听

**解决方案:**
1. 最新Dockerfile已包含curl安装
2. 查看容器日志:
   ```bash
   docker-compose logs -f web
   ```
3. 检查容器内部:
   ```bash
   docker-compose exec web bash
   curl -f http://localhost:8501/_stcore/health
   ```

## 验证工具

使用项目提供的验证脚本检查Docker环境:

```bash
python scripts/validation/check_docker_setup.py
```

此脚本会检查:
- Docker是否安装
- Docker Compose是否安装
- Docker服务是否运行
- .env文件是否配置
- Dockerfile是否存在
- docker-compose.yml是否配置

## 调试技巧

### 查看完整构建日志
```bash
docker-compose build --no-cache web 2>&1 | tee build.log
```

### 进入运行中的容器
```bash
docker-compose exec web bash
```

### 测试streamlit是否可用
```bash
docker-compose exec web python -c "import streamlit; print(streamlit.__version__)"
```

### 查看容器资源使用
```bash
docker stats TradingAgents-web
```

### 清理并重新开始
```bash
# 停止并删除所有容器
docker-compose down

# 删除旧镜像
docker rmi tradingagents-cn:latest

# 清理构建缓存
docker builder prune -a

# 重新构建
docker-compose up -d --build
```

## 最佳实践

1. **首次部署**
   ```bash
   # 1. 克隆项目
   git clone https://github.com/hsliuping/TradingAgents-CN.git
   cd TradingAgents-CN
   
   # 2. 配置环境
   cp .env.example .env
   # 编辑.env文件
   
   # 3. 验证环境
   python scripts/validation/check_docker_setup.py
   
   # 4. 构建并启动
   docker-compose up -d --build
   
   # 5. 查看日志
   docker-compose logs -f web
   ```

2. **日常开发**
   ```bash
   # 启动服务（不重新构建）
   docker-compose up -d
   
   # 代码修改后重新构建
   docker-compose up -d --build
   
   # 查看日志
   docker-compose logs -f web
   
   # 停止服务
   docker-compose down
   ```

3. **版本更新**
   ```bash
   # 拉取最新代码
   git pull
   
   # 重新构建镜像
   docker-compose up -d --build
   ```

## 性能优化

### 使用.dockerignore
项目已包含优化的.dockerignore文件，排除不必要的文件:
- Git历史和配置
- Python缓存和虚拟环境
- IDE配置文件
- 临时文件和日志
- 测试文件

### 多阶段构建（可选优化）
如果需要进一步减小镜像大小，可以考虑使用多阶段构建，但当前单阶段构建已经足够高效。

## 获取帮助

如果以上方法都无法解决问题:

1. 运行验证脚本并保存输出:
   ```bash
   python scripts/validation/check_docker_setup.py > docker_check.log 2>&1
   ```

2. 保存构建日志:
   ```bash
   docker-compose build --no-cache 2>&1 | tee docker_build.log
   ```

3. 保存运行日志:
   ```bash
   docker-compose logs web > docker_run.log 2>&1
   ```

4. 在GitHub上提交Issue，并附上以上日志文件:
   https://github.com/hsliuping/TradingAgents-CN/issues

## 更新记录

- 2025-10-25: 修复streamlit未安装问题，优化Xvfb启动脚本，添加.dockerignore
- 创建Docker验证工具和排查指南
