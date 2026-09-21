# 发布到 GitHub

只上传公开目录 `public/ml-benchmark/` 内的文件。`ml-benchmark-administrator-PRIVATE.zip` 和整个完整交付 ZIP 用于私下交接，不应上传到公开仓库或公开 Release。

发布前，在公开目录执行：

```bash
python scripts/verify_report.py
python -m pytest -q
shasum -a 256 -c SHA256SUMS
```

然后使用自己的 GitHub 仓库地址：

```bash
git init -b main
git add .
git status --short
git commit -m "Release ML Benchmark public package"
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

不要把账号凭据、连接配置、比赛数据、运行日志或管理员目录加入公开仓库。`.gitignore` 已覆盖常见运行目录，但不能代替检查 `git status`。此交付没有创建远程仓库，也没有执行 push。

数据由使用者依据源站规则取得；本次打包不新增整库开源授权或第三方数据再许可。参见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。
