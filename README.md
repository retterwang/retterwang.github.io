# retter.wang — personal homepage

English | [简体中文](README.zh-CN.md)

Source of my personal homepage, served at **[retter.wang](https://retter.wang)** via GitHub Pages.

## What's in it

A single self-contained page — no build step, no framework, no external JavaScript. It covers:

- **About** — a short bilingual introduction
- **Projects** — the things I build and maintain, including the
  [CAMCOP](https://camera.abetterplace2.live) camera comparison tool (1,140 cameras, five views,
  plus a WeChat Mini Program) and the `abetterplace2.live` site cluster
- **Experience** — a condensed work history

The page is written bilingual: Chinese and English text sit side by side rather than being
toggled, so both render from the same markup.

## Structure

```
├── index.html            # The entire site (HTML + inline CSS/JS)
├── CNAME                 # Custom domain: retter.wang
├── .nojekyll             # Skip Jekyll processing on GitHub Pages
├── portrait.jpg          # Profile photo
├── camcop-miniprogram.jpg
└── favicon*.png / apple-touch-icon.png
```

## Deployment

Commits to `main` are published automatically by GitHub Pages — there is no build or CI step.

```bash
git add .
git commit -m "content: ..."
git push
```

DNS for `retter.wang` points at GitHub Pages, with the custom domain recorded in `CNAME`.
TLS is provisioned by GitHub.

## License

© Retter Wang. All rights reserved.
