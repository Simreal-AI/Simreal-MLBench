# 环境搭建

## 使用公开包

Python 3.11 及以上，推荐先使用已验证的 Python 3.12。在仓库根目录运行：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
mleb validate configs/catalog.json
python scripts/verify_report.py
python -m pytest -q
```

评分示例不需要模型 API、Kaggle 账号或 GPU：

```bash
mleb grade examples/snapshot.json examples/result.json
mleb aggregate-experiment examples/experiment/manifest.json examples/experiment/tasks.json examples/experiment/results.json
```

这些是虚构数值，用于检查评分链路。真实数据按[下载说明](../data-access/README.md)获取；访问受限比赛需要数据使用者自己的权限。

## 运行研究任务

公开包不包含训练控制器。向管理员取得已分配的 gateway，按[接入说明](GATEWAY.md)配置。管理员持有独立包，在 Ubuntu 上构建 CPU/GPU Docker worker，并配置任务预算、输入目录和官方提交渠道。

管理员包带合成任务自检，可以先验证排队、读写、训练、冻结、两次评分和最终选择，不必调用模型。真实 Docker、自有 GPU、远程 SSH 与官方账号需要在目标服务器各自检查。

训练环境与模型推理/权重训练环境分开：API agent 可使用远程模型；任务训练按对应 tier 使用 CPU/GPU；更新模型权重需另配训练基础设施。公开包和管理员包包含同名 Python namespace，使用不同虚拟环境，不要混装。
