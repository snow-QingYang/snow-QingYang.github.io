# Qingyang Bao Personal Website

Static personal website rebuilt from the old Hexo blog archive.

## Preview

Run a local static server:

```powershell
python -m http.server 8080 --bind 127.0.0.1
```

Then visit `http://127.0.0.1:8080`.

## Build

Markdown files are the source of truth. Run this after editing posts:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

This converts Markdown into Hexo-style static folders:

- `content/posts/*.md` -> `blog/<slug>/index.html`
- `content/research/*.md` -> `research/<slug>/index.html`

The URLs are served as `/blog/<slug>/` and `/research/<slug>/`.

## Deploy

After configuring the GitHub Pages remote, deploy with:

```powershell
powershell -ExecutionPolicy Bypass -File .\deploy.ps1 -Message "Add new post"
```

If the remote is not configured yet, add it once:

```powershell
git remote add origin https://github.com/snow-QingYang/snow-QingYang.github.io.git
```

`deploy.ps1` runs the build, stages the site files, commits, and pushes the current branch.

## Migrated Content

- Original Markdown posts are preserved in `content/posts`.
- Research notes are written in `content/research`.
- The original about page is preserved in `content/pages/about.md`.
- Original blog images are preserved in `assets/images`.

The visible site is split into static folders:

- Home: `/`
- Research list: `/research/`
- Blog list: `/blog/`
- Research article: `/research/<slug>/`
- Blog article: `/blog/<slug>/`

Research notes and Blog posts are generated as static pages from Markdown.

## Writing Blog Posts

1. Add a Markdown file to `content/posts`. This folder is only for Blog articles.
2. Use Hexo-style frontmatter:

```md
---
title: My New Post
date: 2026-06-16
tags: technical blog
cover: images/evening.png
---

Write the article here.
```

3. Rebuild the static blog pages:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

This creates `blog/index.html` for the Blog list and `blog/<slug>/index.html` for each post. The URL is served as `/blog/<slug>/`, matching Hexo-style pretty URLs.

Set `listed: false` in a post's frontmatter to keep its page available by direct URL while hiding it from the Blog list.

## Writing Research Notes

1. Add a Markdown file to `content/research`.
2. Use the same frontmatter:

```md
---
title: My Research Note
date: 2026-06-16
tags: Research
cover: images/murasame.webp
published: true
---

Write the research note here.
```

3. Rebuild with the same command:

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

This creates `research/index.html` for the Research list and `research/<slug>/index.html` for each research note. The URL is served as `/research/<slug>/`.

## Profile Links

The homepage links to:

- GitHub: `https://github.com/snow-QingYang`
- Email: `qingyangbao@cs.toronto.edu`
- X / Twitter: `https://x.com/snowclears`
- Google Scholar: `https://scholar.google.com/citations?hl=en&user=rGb2tWcAAAAJ`
- CV: `assets/Qingyang_Bao_CV.pdf`

Place the CV PDF at `assets/Qingyang_Bao_CV.pdf` when it is ready.

## Writing Math

MathJax is enabled. Use TeX delimiters inside article Markdown:

- Inline math: `\( e^{i\pi} + 1 = 0 \)` or `$e^{i\pi} + 1 = 0$`
- Display math: `\[ \int_{\mathbb{R}} e^{-x^2}\,dx = \sqrt{\pi} \]` or `$$...$$`

In Markdown files you can write normal TeX delimiters directly.
