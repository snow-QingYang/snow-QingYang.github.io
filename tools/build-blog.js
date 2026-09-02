const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const postsDir = path.join(root, "content", "posts");
const researchDir = path.join(root, "content", "research");
const outDir = path.join(root, "blog");
const researchOutDir = path.join(root, "research");

const site = {
  title: "Qingyang Bao",
  author: "Qingyang Bao",
  homeUrl: "../../index.html"
};

function slugify(fileName) {
  return fileName.replace(/\.md$/i, "");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function parseFrontmatter(source) {
  if (!source.startsWith("---")) {
    return { data: {}, body: source.trim() };
  }

  const end = source.indexOf("\n---", 3);
  if (end === -1) {
    return { data: {}, body: source.trim() };
  }

  const raw = source.slice(3, end).trim();
  const body = source.slice(end + 4).trim();
  const data = {};

  raw.split(/\r?\n/).forEach((line) => {
    const match = line.match(/^([^:]+):\s*(.*)$/);
    if (!match) return;
    const key = match[1].trim();
    let value = match[2].trim();
    value = value.replace(/^['"]|['"]$/g, "");
    if (value === "false") value = false;
    if (value === "true") value = true;
    data[key] = value;
  });

  return { data, body };
}

function normalizeCover(cover, depth = "../..") {
  if (!cover) return `${depth}/assets/images/background.jpg`;
  return `${depth}/assets/${cover.replace(/^assets\//, "").replace(/^images\//, "images/")}`;
}

function coverForIndex(cover) {
  if (!cover) return "assets/images/background.jpg";
  return `assets/${cover.replace(/^assets\//, "").replace(/^images\//, "images/")}`;
}

function inlineMarkdown(text) {
  let output = escapeHtml(text);
  output = output.replace(/`([^`]+)`/g, "<code>$1</code>");
  output = output.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  output = output.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  output = output.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  return output;
}

function markdownToHtml(markdown) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let paragraph = [];
  let list = [];
  let mathBlock = [];
  let mathBlockClose = "";

  function flushParagraph() {
    if (!paragraph.length) return;
    html.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
    paragraph = [];
  }

  function flushList() {
    if (!list.length) return;
    html.push(`<ul>${list.map((item) => `<li>${inlineMarkdown(item)}</li>`).join("")}</ul>`);
    list = [];
  }

  for (const line of lines) {
    const trimmed = line.trim();

    if (mathBlock.length) {
      mathBlock.push(trimmed);
      if (trimmed === mathBlockClose) {
        html.push(`<div class="math-block">${escapeHtml(mathBlock.join("\n"))}</div>`);
        mathBlock = [];
        mathBlockClose = "";
      }
      continue;
    }

    if (!trimmed) {
      flushParagraph();
      flushList();
      continue;
    }

    if (/^\\\[.+\\\]$/.test(trimmed) || /^\$\$.+\$\$$/.test(trimmed)) {
      flushParagraph();
      flushList();
      html.push(`<div class="math-block">${escapeHtml(trimmed)}</div>`);
      continue;
    }

    if (trimmed === "\\[" || trimmed === "$$") {
      flushParagraph();
      flushList();
      mathBlock = [trimmed];
      mathBlockClose = trimmed === "\\[" ? "\\]" : "$$";
      continue;
    }

    const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      html.push(`<h${level}>${inlineMarkdown(heading[2])}</h${level}>`);
      continue;
    }

    if (/^#{1,4}$/.test(trimmed)) {
      flushParagraph();
      flushList();
      continue;
    }

    if (/^(\\\(|\\\))/.test(trimmed)) {
      flushParagraph();
      flushList();
      html.push(`<p>${escapeHtml(trimmed)}</p>`);
      continue;
    }

    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      list.push(bullet[1]);
      continue;
    }

    flushList();
    paragraph.push(trimmed);
  }

  flushParagraph();
  flushList();
  if (mathBlock.length) {
    html.push(`<div class="math-block">${escapeHtml(mathBlock.join("\n"))}</div>`);
  }
  return html.join("\n");
}

function excerptFrom(markdown) {
  const line = markdown
    .split(/\r?\n/)
    .map((item) => item.trim())
    .find((item) => item && !item.startsWith("#"));
  if (!line) return "";
  return line
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1")
    .replace(/\s+/g, " ")
    .slice(0, 120);
}

function navTemplate(activeView, depth) {
  return `<header class="topbar">
      <a class="brand" href="${depth}/" aria-label="Qingyang Bao home">
        <img class="brand__mark" src="${depth}/assets/images/front.jpg" alt="" />
        <span>Qingyang Bao</span>
      </a>
      <nav class="nav" aria-label="Primary navigation">
        <a class="nav__item${activeView === "home" ? " is-active" : ""}" href="${depth}/">Home</a>
        <a class="nav__item${activeView === "research" ? " is-active" : ""}" href="${depth}/research/">Research</a>
        <a class="nav__item${activeView === "blog" ? " is-active" : ""}" href="${depth}/blog/">Blog</a>
      </nav>
    </header>`;
}

function footerTemplate(depth) {
  return `<footer class="footer">
      <span>&copy; 2026 Qingyang Bao</span>
      <span id="lastUpdated">Last updated</span>
    </footer>

    <script src="${depth}/script.js"></script>`;
}

function cardTemplate(post, coverPath) {
  return `<a class="post-card" href="${post.slug}/" aria-label="Open ${escapeHtml(post.title)}">
          <img class="post-card__image" src="${coverPath}" alt="${escapeHtml(post.title)}" />
          <div class="post-card__body">
            <div class="post-card__meta">
              <span>${escapeHtml(post.tag)}</span>
              <span>${escapeHtml(post.date)}</span>
            </div>
            <h3>${escapeHtml(post.title)}</h3>
            <p>${escapeHtml(post.excerpt)}</p>
            <span class="post-card__status">${escapeHtml(post.status)}</span>
          </div>
        </a>`;
}

function listPageTemplate(section, posts) {
  const depth = "..";
  const cards = posts
    .map((post) => cardTemplate(post, post.coverList))
    .join("\n");

  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${section.label} | ${site.title}</title>
    <meta name="description" content="${escapeHtml(section.description)}" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,300;0,400;0,700;1,300;1,400;1,700&display=swap" rel="stylesheet" />
    <link rel="icon" href="../assets/images/front.jpg" />
    <link rel="stylesheet" href="../styles.css" />
  </head>
  <body data-view="${section.id}">
    <div class="site-bg" aria-hidden="true">
      <img src="../assets/images/background.jpg" alt="" />
      <div class="site-bg__wash"></div>
    </div>

    ${navTemplate(section.id, depth)}

    <main class="shell">
      <div class="post-grid">
${cards}
      </div>
    </main>

    ${footerTemplate(depth)}
  </body>
</html>
`;
}

function pageTemplate(post, bodyHtml, section) {
  const activeView = section.id;
  const backHref = "../";
  const backLabel = `Back to ${section.label}`;
  const depth = "../..";
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${escapeHtml(post.title)} | ${site.title}</title>
    <meta name="description" content="${escapeHtml(post.excerpt)}" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,300;0,400;0,700;1,300;1,400;1,700&display=swap" rel="stylesheet" />
    <link rel="icon" href="../../assets/images/front.jpg" />
    <link rel="stylesheet" href="../../styles.css" />
    <script>
      window.MathJax = {
        tex: {
          inlineMath: [["\\\\(", "\\\\)"], ["$", "$"]],
          displayMath: [["\\\\[", "\\\\]"], ["$$", "$$"]],
          processEscapes: true
        },
        options: {
          skipHtmlTags: ["script", "noscript", "style", "textarea", "pre", "code"]
        }
      };
    </script>
    <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
  </head>
  <body class="post-page" data-view="${section.id}">
    <div class="site-bg" aria-hidden="true">
      <img src="../../assets/images/background.jpg" alt="" />
      <div class="site-bg__wash"></div>
    </div>

    ${navTemplate(activeView, depth)}

    <main class="post-shell">
      <article class="post-page__card">
        <header class="post-page__header">
          <a class="post-page__back" href="${backHref}">${backLabel}</a>
          <div class="post-page__meta">
            <span>${escapeHtml(post.tag)}</span>
            <time datetime="${escapeHtml(post.date)}">${escapeHtml(post.date)}</time>
          </div>
          <h1>${escapeHtml(post.title)}</h1>
        </header>
        <div class="prose prose--article">
${bodyHtml}
        </div>
      </article>
    </main>
    ${footerTemplate(depth)}
  </body>
</html>
`;
}

function readEntries(inputDir) {
  if (!fs.existsSync(inputDir)) return [];

  return fs
    .readdirSync(inputDir)
    .filter((file) => file.endsWith(".md"))
    .map((file) => {
      const fullPath = path.join(inputDir, file);
      const source = fs.readFileSync(fullPath, "utf8");
      const { data, body } = parseFrontmatter(source);
      const slug = slugify(file);
      const title = data.title || slug;
      const tag = data.tags || "Blog";
      const date = data.date || (slug === "trip-to-ann-arbor" ? "2023-11-01" : "2024-12-20");
      const excerpt = excerptFrom(body);
      const status = data.published === false ? "Draft" : "Post";
      const coverIndex = coverForIndex(data.cover);
      const coverList = normalizeCover(data.cover, "..");
      const coverPage = normalizeCover(data.cover);
      const published = data.published !== false;
      return { slug, title, tag, date, excerpt, status, coverIndex, coverList, coverPage, body, published };
    });
}

function buildSection(section) {
  fs.mkdirSync(section.outDir, { recursive: true });

  const sourcePosts = readEntries(section.inputDir);
  const sourceSlugs = new Set(sourcePosts.map((post) => post.slug));

  fs.readdirSync(section.outDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !sourceSlugs.has(entry.name))
    .forEach((entry) => {
      fs.rmSync(path.join(section.outDir, entry.name), { recursive: true, force: true });
    });

  sourcePosts
    .filter((post) => !post.published)
    .forEach((post) => {
      fs.rmSync(path.join(section.outDir, post.slug), { recursive: true, force: true });
    });

  const posts = sourcePosts
    .filter((post) => post.published)
    .sort((a, b) => String(b.date).localeCompare(String(a.date)));

  for (const post of posts) {
    const dir = path.join(section.outDir, post.slug);
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, "index.html"), pageTemplate(post, markdownToHtml(post.body), section), "utf8");
  }

  fs.writeFileSync(path.join(section.outDir, "index.html"), listPageTemplate(section, posts), "utf8");

  const indexData = posts.map((post) => ({
    slug: post.slug,
    title: post.title,
    tag: post.tag,
    date: post.date,
    excerpt: post.excerpt,
    status: post.status,
    cover: post.coverIndex,
    url: `${section.id}/${post.slug}/`
  }));

  fs.writeFileSync(
    path.join(section.outDir, "posts.js"),
    `window.${section.globalName} = ${JSON.stringify(indexData, null, 2)};\n`,
    "utf8"
  );
}

function build() {
  buildSection({
    id: "blog",
    label: "Blog",
    description: "Blog posts by Qingyang Bao.",
    inputDir: postsDir,
    outDir,
    globalName: "BLOG_POSTS"
  });

  buildSection({
    id: "research",
    label: "Research",
    description: "Research notes by Qingyang Bao.",
    inputDir: researchDir,
    outDir: researchOutDir,
    globalName: "RESEARCH_POSTS"
  });
}

build();
