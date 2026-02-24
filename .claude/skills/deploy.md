# deploy

发布博客到 GitHub Pages。

## 使用场景

当用户完成文章编写或修改后，想要发布博客时使用。

## 调用方式

```
/deploy
```

## 执行步骤

### 1. 前置检查

- 运行 `git status` 查看当前变更
- 确认当前分支（应在 `hugo-dev` 或 `master`）
- 检查是否有未提交的变更

如果没有任何变更，告诉用户没有需要发布的内容。

### 2. 检查草稿状态

搜索 `content/post/` 下所有 `index.md`，检查是否有 `draft: true` 的文章。

如果有草稿文章，提醒用户：
- 列出草稿文章标题
- 询问用户是否要先把草稿改为发布状态（`draft: false`）
- 如果用户确认发布某些草稿，帮忙修改 `draft: true` 为 `draft: false`

### 3. 本地构建验证

运行 `hugo --gc --minify` 验证构建是否成功。如果构建失败，分析错误并帮用户修复。

### 4. 提交变更

- 用 `git add` 添加所有变更文件（注意排查敏感文件）
- 生成清晰的 commit message，格式参考：
  - 新文章：`post: 文章标题`
  - 配置修改：`config: 修改内容描述`
  - 多项变更：`update: 简要描述`
- 末尾加上 `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`

### 5. 推送到远程

根据当前分支执行不同操作：

**如果在 `hugo-dev` 分支：**
1. 推送 `hugo-dev` 到远程：`git push origin hugo-dev`
2. 切换到 `master`：`git checkout master`
3. 合并：`git merge hugo-dev`
4. 推送 `master`：`git push origin master`
5. 切回 `hugo-dev`：`git checkout hugo-dev`

**如果在 `master` 分支：**
1. 直接推送：`git push origin master`

> 注意：推送命令需要配置代理：
> ```bash
> export https_proxy=http://127.0.0.1:7897 http_proxy=http://127.0.0.1:7897 all_proxy=socks5://127.0.0.1:7897
> ```

### 6. 确认部署

推送后告诉用户：
- 代码已推送，GitHub Actions 会自动构建部署
- 查看部署状态：`https://github.com/crmo/crmo.github.io/actions`
- 部署完成后访问：`https://crmo.github.io/`
- 通常 1-2 分钟内完成

## 项目信息

- 远程仓库：`https://github.com/crmo/crmo.github.io.git`
- 部署方式：GitHub Actions（`.github/workflows/deploy.yml`）
- 触发条件：push 到 `master` 分支
- 开发分支：`hugo-dev`
- 主分支：`master`

## 首次部署注意

如果是从 Hexo 迁移后的首次部署，需要提醒用户去 GitHub 修改设置：
> **GitHub 仓库 → Settings → Pages → Build and deployment → Source**
> 从 "Deploy from a branch" 改为 **"GitHub Actions"**
