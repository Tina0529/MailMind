# MailMind AI - Railway 部署指南

本指南将指导您将 **前端 (Next.js)** 和 **后端 (FastAPI)** 都部署到 **Railway** 平台。

## 📦 项目结构说明

这是一个 Monorepo 项目，包含两个服务：

- `backend/`: Python FastAPI 服务
- `frontend/`: Next.js React 服务

在 Railway 中，我们将创建**两个服务 (Services)**，分别指向同一个 GitHub 仓库的两个不同目录。

---

## 🚀 部署步骤

### 第一步：创建项目

1. 登录 [Railway Dashboard](https://railway.app/)。
2. 点击 **"New Project"** -> **"Deploy from GitHub repo"**。
3. 选择您的仓库 `MailMind`。
4. **重要**：先只添加仓库，不要立即点击部署（或者部署失败也没关系，我们需要配置）。

### 第二步：配置后端服务 (Backend)

1. 在 Railway 项目视图中，点击刚刚创建的服务，重命名为 `backend`（可选）。
2. 进入 **Settings**:

   - **Root Directory**: 输入 `/backend`
   - **Build Command**: (留空，Railway 会自动识别 requirements.txt)
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
3. 进入 **Variables**，添加环境变量：

   - `ANTHROPIC_API_KEY`: `sk-ant-xxxx...`
   - `ANTHROPIC_BASE_URL`: `https://one-dev.felo.me/v1` (可选，默认为官方API)
   - `ZOHO_CLIENT_ID`: `1000.xxxx...`
   - `ZOHO_CLIENT_SECRET`: `xxxx...`
   - `FRONTEND_URL`: `https://your-frontend-domain.up.railway.app` (稍后创建前端后回来填写)
   - `ZOHO_REDIRECT_URI`: `https://your-frontend-domain.up.railway.app/oauth/callback`
   - `PORT`: `8000`
4. **持久化存储 (重要)**:

   - 由于使用 SQLite，必须挂载 Volume 防止数据丢失。
   - 在该服务上右键 -> **Volume** -> **Add Volume**。
   - 挂载路径 (Mount Path): `/app/backend/data` (或者 `/backend/data`，取决于 Railway 的构建路径，通常是 `/app` 开头)。
   - _建议_: 生产环境强烈建议在 Railway 创建一个 **PostgreSQL** 数据库，并将 `DATABASE_URL` 变量设置为 PG 的连接地址。

### 第三步：配置前端服务 (Frontend)

1. 在项目视图点击 **"New Service"** -> **"GitHub Repo"** -> 再次选择同一个 `MailMind` 仓库。
2. 点击新服务，重命名为 `frontend`。
3. 进入 **Settings**:
   - **Root Directory**: 输入 `/frontend`
   - **Build Command**: `npm run build`
   - **Start Command**: `npm start`
4. 进入 **Variables**:
   - `NEXT_PUBLIC_API_URL`: 填写后端的域名 (例如 `https://backend-production.up.railway.app`) (注意不要带末尾斜杠)
5. **Networking**:
   - 点击 **Generate Domain** 生成一个公网访问域名（例如 `frontend-production.up.railway.app`）。

### 第四步：关联配置

1. 拿到前端域名后，**回到后端服务**：
   - 更新 `FRONTEND_URL` 为前端域名。
   - 更新 `ZOHO_REDIRECT_URI` 为前端域名 + `/oauth/callback`。
2. **Zoho 控制台**:
   - 去 [Zoho API Console](https://api-console.zoho.com/)。
   - 将 Redirect URI 更新为新的生产环境地址。

---

## 🛠 常见问题

### SQLite 数据丢失？

Railway 每次重新部署都会重置文件系统。

- **解决方案 A (当前)**: 必须添加 Volume 并挂载到 `data/` 目录。
- **解决方案 B (推荐)**: 在 Railway 添加一个 PostgreSQL 插件，替换 SQLite。

### 后端健康检查失败？

- 确保 `HOST` 是 `0.0.0.0` 而不是 `127.0.0.1`。
- 确保 `PORT` 变量被正确传递（Railway 会自动注入 `$PORT`）。

## 📝 环境变量清单

| 服务           | 变量名                      | 值                                           |
| -------------- | --------------------------- | -------------------------------------------- |
| **后端** | `ANTHROPIC_API_KEY`       | `sk-...`                                   |
|                | `ZOHO_CLIENT_ID`          | `1000...`                                  |
|                | `ZOHO_CLIENT_SECRET`      | `...`                                      |
|                | `FRONTEND_URL`            | `https://xx.up.railway.app`                |
|                | `ZOHO_REDIRECT_URI`       | `https://xx.up.railway.app/oauth/callback` |
|                | `NIXPACKS_PYTHON_VERSION` | `3.11` (可选，指定Python版本)              |
| **前端** | `NEXT_PUBLIC_API_URL`     | `https://xx-backend.up.railway.app`        |
