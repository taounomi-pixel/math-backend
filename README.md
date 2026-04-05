# MathVis - 定理可视化平台 (Backend)

本仓库为 MathVis 平台的后端 API 服务。它为前端提供稳定、安全的数据支撑，处理用户认证、视频元数据管理以及高并发状态下的评论同步逻辑。

## 核心架构设计
* **极简且健壮：** 采用纯粹的 Python 架构设计，剥离冗余依赖，保障在有限内存下（512MB 环境）的极速响应。
* **安全认证隔离：** 独立的 `auth.py` 模块处理鉴权，敏感环境变量严格通过云端加载。
* **容器化部署：** 提供完整的 `Dockerfile`，保障本地开发与云端生产环境的高度一致性。

## 技术栈
* **核心语言：** Python 3
* **数据库：** PostgreSQL (负责持久化存储用户关系与视频结构树)
* **容器化：** Docker
* **云端部署：** Render (构建自动化 Web Service)
* **API 域名：** `api.math-vis.xin`

## 本地运行指南
1.  克隆仓库并进入目录：
    ```bash
    git clone [https://github.com/taounomi-pixel/math-backend.git](https://github.com/taounomi-pixel/math-backend.git)
    cd math-backend
    ```
2.  安装 Python 依赖：
    ```bash
    pip install -r requirements.txt
    ```
3.  环境变量配置：
    复制 `.env.example` 文件并重命名为 `.env`，填入你本地的数据库连接串和密钥。
4.  启动后端服务 (以实际启动命令为准)：
    ```bash
    python main.py 
    ```
