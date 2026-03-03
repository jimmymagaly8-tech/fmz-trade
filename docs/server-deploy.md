# 服务器部署操作手册

## 环境信息

| 项目 | 值 |
|------|----|
| 服务器 IP | 192.168.31.128 |
| 访问地址 | http://192.168.31.128:8000 |
| 项目目录 | /root/fmz (或 git clone 的目录) |
| 代码仓库 | https://github.com/jimmymagaly8-tech/fmz-trade |

---

## 一、首次部署

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# 2. 拉取代码
cd /opt
git clone https://github.com/jimmymagaly8-tech/fmz-trade.git
cd fmz-trade

# 3. 开放防火墙端口
firewall-cmd --add-port=8000/tcp --permanent
firewall-cmd --reload

# 4. 构建并启动
docker compose up -d --build
```

---

## 二、更新代码后重新部署

每次代码有更新，在服务器上执行：

```bash
cd /opt/fmz-trade
git pull
docker compose up -d --build
```

---

## 三、日常操作

### 查看运行状态
```bash
docker ps
```

### 查看日志
```bash
docker logs fmz-trade-fmz-trade-1 -f --tail 100
```

### 停止服务
```bash
docker compose down
```

### 重启服务（不重新构建）
```bash
docker compose restart
```

---

## 四、常见问题

### 页面打不开
1. 确认容器在运行：`docker ps`
2. 确认防火墙已放行：`firewall-cmd --list-ports`
3. Chrome 代理插件拦截：把 `192.168.31.128` 加入直连列表，或换浏览器

### 回测失败 "Task not found"
多进程内存不共享导致，确认 Dockerfile CMD 没有 `--workers` 参数

### 回测失败 "Backtest timeout"
超时时间默认 30 分钟，1分钟周期建议回测区间不超过 3 个月

### 镜像拉取失败（Docker Hub 被墙）
```bash
# 配置国内镜像源
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
EOF
systemctl restart docker
```
