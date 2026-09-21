# Agent 接入

公开包提供 `mleb-remote` 客户端。管理员在受控主机上运行 `mleb-ssh-v1` JSON 接口，并提供受限 SSH 连接；本包没有预设公共服务器。

## 检查连接

管理员配置 SSH 专用 Host 别名并交付连接信息后，在公开包根目录执行：

```bash
cp sdk/connection.example.json connection.json
mleb-remote --connection connection.json '{"op":"ping"}'
```

请将 `ssh_host` 改成自己的 SSH 配置别名。SSH 密钥必须绑定管理员的 forced command，不能授予训练数据、评测文件所在账号的任意 shell。主机指纹应由管理员确认。

## 接入自定义 agent

[sdk/requests.json](../sdk/requests.json) 给出实际请求格式。管理员负责 `begin`、任务分配和运行配置，agent 仅能操作自己被分配的 run：

| 操作 | 用途 |
| --- | --- |
| `task`, `status` | 任务描述、预算、运行状态 |
| `list`, `read`, `write` | 分配目录内文件操作；读写内容使用 base64 |
| `job`, `job-status` | 提交容器训练任务，查询结果和日志 |
| `evaluate`, `evaluation-status` | 请求冻结评测，查询允许返回的反馈 |
| `finish` | 结束研究并进入收尾 |

模型产生工具调用 → 客户端发送 JSON → 控制器校验 run 和路径 → worker 执行 → 返回工具结果 → 模型继续研究。把远程调用包装成自己的工具函数即可；`begin` 和管理员配置不能作为可自由调用的研究工具。

Python 客户端用法：

```python
from mle_benchmark.remote_client import request
response = request({"ssh_host": "mleb-worker"}, {"op": "ping"})
```

这是现有 SSH 协议客户端，不是完整 Gymnasium 环境或开箱即用的 RL trainer。RL rollout adapter 需另外实现轨迹记录、训练奖励和策略更新的连接。不同操作持续时间不同，应保留耗时和剩余预算。

## 管理员准备

在单独管理员包按 `README.md` 安装，运行合成自检，再按 `deploy/README.md` 配置 forced-command SSH、Docker worker 和任务目录。真实比赛的官方评分需管理员单独配置账号与 evaluation route；本交付不包含已授权的账号或服务地址。
