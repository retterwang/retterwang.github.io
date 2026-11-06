# retter.wang — 个人主页

[English](README.md) | 简体中文

我的个人主页源码，通过 GitHub Pages 发布于 **[retter.wang](https://retter.wang)**。

## 页面内容

单页自包含站点 —— 无构建步骤、无框架、无外部 JavaScript。包含三部分：

- **关于** — 简短的中英双语自我介绍
- **项目** — 我在做和维护的东西，包括 iOS 应用
  [Saudade](https://apps.apple.com/cn/app/saudade/id6827383744)、
  [CAMCOP](https://camera.abetterplace2.live) 相机对比工具（1,144 台相机、五视角对比，另有微信小程序），
  以及 `abetterplace2.live` 站点集群
- **履历** — 精简的工作经历

页面支持 8 种语言 —— 简体中文、繁體中文、English、日本語、한국어、Français、Español、Deutsch，
与 Saudade 站保持同一套语言。两种中文视图在每条内容下保留英文对照行，其余语言为单语阅读。
切换器在右上角，选择记在 `localStorage`，也可以用 `?lang=ja` 这样的地址直接打开某一语言；
正文本身以中文写入 HTML，关闭 JavaScript 也能正常阅读。

## 项目结构

```
├── index.html            # 整站（HTML + 内联 CSS/JS）
├── CNAME                 # 自定义域名：retter.wang
├── .nojekyll             # 跳过 GitHub Pages 的 Jekyll 处理
├── portrait.jpg          # 头像
├── camcop-miniprogram.jpg
└── favicon*.png / apple-touch-icon.png
```

## 部署

提交到 `main` 分支后由 GitHub Pages 自动发布 —— 没有构建或 CI 步骤。

```bash
git add .
git commit -m "content: ..."
git push
```

`retter.wang` 的 DNS 指向 GitHub Pages，自定义域名记录在 `CNAME` 文件中，TLS 由 GitHub 签发。

## 许可证

© 王文昊，保留所有权利。
