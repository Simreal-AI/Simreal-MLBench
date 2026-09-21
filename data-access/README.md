# 数据获取

包内提供 60 项任务目录与下载工具，不重新分发 Kaggle 原始数据。数据账号持有人自行阅读并接受各比赛规则，再下载其有权使用的数据。训练容器和 agent 不持有该账号的凭据。

在此目录执行：

```bash
bash setup.sh
.venv/bin/kaggle auth login --no-launch-browser
.venv/bin/python download.py --help
```

按终端提示登录，然后使用 `download.py --help` 中的 `download` 与 `verify` 命令，把压缩包放到仓库外的存储目录。`competitions.json` 与当前公开目录一致，包含 60 个比赛链接。工具只下载并校验源文件，不训练、不提交，也不代替你接受条款。

原始压缩包由可信数据管理员保管。按比赛要求审核文件、预训练权重和外部数据，生成任务专用输入。最终官方评测使用原有 test identity；训练 agent 可以在原始训练数据内创建验证集。

RL/RLVR 的研究奖励分区是另一个实验协议，必须从允许用于训练的数据构建；不能用官方最终评测集调试 reward 或挑选 agent 版本。
