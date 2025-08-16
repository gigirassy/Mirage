# app.py
from flask import Flask, Response, render_template, request
import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin, quote
import os

app = Flask(__name__)

USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
)

# Improved responsive CSS + gentler light mode + gallery improvements
INJECT_CSS = r"""
:root {
  --page-bg: #f6f8fa;
  --container-bg: #ffffff;
  --text: #12121a;
  --accent: #1976d2;
  --accent-strong: #115293;
  --muted: #556070;
  --mirage-font-scale: 1;
  --container-side-padding: 16px;
  --container-max-width: 800px;
  --control-size: 44px;
  --gap: 10px;
}
/* Prevent iOS Safari auto text-size shrinking */
html, body {
  -webkit-text-size-adjust: 100%;
  -ms-text-size-adjust: 100%;
}
html.dark {
  --page-bg: #071120;
  --container-bg: #0a1724;
  --text: #dbeafc;
  --accent: #5ea3ff;
  --accent-strong: #2b7be6;
  --muted: #9aa9bf;
}
body {
  margin: 0;
  background: linear-gradient(180deg, var(--page-bg), var(--page-bg));
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-size: 16px; /* base for rem calculations */
}

/* Responsive container: width 100% with max-width */
.mirage-container {
  width: 100%;
  max-width: var(--container-max-width);
  margin: 28px auto;
  padding: 20px;
  padding-left: var(--container-side-padding);
  padding-right: var(--container-side-padding);
  background: var(--container-bg);
  box-shadow: 0 6px 18px rgba(11,18,32,0.04);
  border-radius: 8px;
  box-sizing: border-box;
  overflow-wrap: break-word;
}

/* Banner */
.mirage-banner {
  border-top: 1px solid rgba(0,0,0,0.04);
  padding-top: 12px;
  margin-bottom: 14px;
  font-size: 0.875rem;
  color: var(--muted);
  display: block;
}
.mirage-banner strong {
  color: var(--text);
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
}

/* Content text sizing uses rem and the --mirage-font-scale variable */
#content {
  line-height: 1.65;
  font-size: calc(1rem * var(--mirage-font-scale)); /* 1rem == 16px */
  box-sizing: border-box;
  word-break: break-word;
}
#content h1, #content h2, #content h3 {
  color: var(--accent-strong);
  margin-top: 1.2rem;
  margin-bottom: 0.6rem;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Hide pagetop and vector pre-content markers */
#content .pagetop,
.vector-body-before-content { display: none !important; visibility: hidden !important; }

/* Gallery: flexible responsive layout */
.mirage-gallery {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap);
  margin: 0.6rem 0;
  justify-content: flex-start;
  align-items: flex-start;
}
.mirage-gallery-item {
  box-sizing: border-box;
  flex: 0 1 calc(33.333% - var(--gap));
  max-width: calc(33.333% - var(--gap));
  text-align: center;
}
.mirage-gallery-item img {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 6px;
}
.mirage-gallery-item .caption {
  font-size: 0.8125rem;
  color: var(--muted);
  margin-top: 6px;
  line-height: 1.25;
}

/* Ensure images scale within content */
#content img { max-width: 100%; height: auto; display: block; margin: 0.6rem 0; }

/* Templates and infoboxes become full-width and non-floating */
#content .infobox,
#content .portable-infobox,
#content .vertical-navbox,
#content .navbox,
#content .thumb,
#content .thumbinner,
#content .sidebar,
#content .metadata,
#content .mbox,
#content .ambox,
#content .hatnote {
  float: none !important;
  clear: both !important;
  display: block !important;
  width: auto !important;
  max-width: 100% !important;
  margin: 0.6rem auto !important;
  box-sizing: border-box !important;
}

/* Tables: center by default */
#content table {
  margin-left: auto;
  margin-right: auto;
  box-sizing: border-box;
  max-width: 100%;
  overflow: auto;
}
#content table.floatleft,
#content table.floatright,
#content table[align],
#content table[style*="float"] {
  margin-left: 0;
  margin-right: 0;
}

/* YouTube placeholder */
.mirage-embed-wrapper { margin: 0.6rem 0; text-align: center; }
.mirage-yt-placeholder {
  background: rgba(0,0,0,0.03);
  padding: 10px;
  border-radius: 6px;
  display: inline-block;
  max-width: 100%;
}
.mirage-yt-placeholder p { margin: 0 0 8px 0; color: var(--muted); font-size: 0.875rem; }
.mirage-yt-allow { background: var(--accent); color: #fff; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; }
.mirage-yt-allow:hover { background: var(--accent-strong); }

/* Controls: vertical stack */
.mirage-controls {
  position: fixed;
  right: 12px;
  top: 12px;
  z-index: 1200;
  display:flex;
  flex-direction: column;
  gap:8px;
  align-items: flex-end;
}
.mirage-btn {
  background: var(--container-bg);
  color: var(--text);
  border: 1px solid rgba(0,0,0,0.06);
  padding: 6px 8px;
  border-radius: 8px;
  font-size: 0.875rem;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(11,18,32,0.04);
  min-width: var(--control-size);
}
.mirage-btn:focus { outline: 2px solid var(--accent); outline-offset: 2px; }

/* Categories */
ul.categories { list-style: none; padding: 0; margin-top: 1.2rem; border-top: 1px solid rgba(0,0,0,0.04); padding-top: 8px; }
ul.categories li { display: inline; margin-right: 0.6rem; font-size: 0.8125rem; color: var(--muted); }

/* Responsive adjustments for small screens */
@media (max-width: 880px) {
  .mirage-container {
    margin: 16px auto;
    padding-left: 14px;
    padding-right: 14px;
  }
  .mirage-gallery-item { flex: 0 1 calc(50% - var(--gap)); max-width: calc(50% - var(--gap)); }
  .mirage-controls { right: 8px; top: 8px; }
  .mirage-btn { padding: 6px 6px; font-size: 0.8125rem; min-width: 40px; }
}
@media (max-width: 520px) {
  .mirage-container { margin: 12px; padding-left: 12px; padding-right: 12px; border-radius: 6px; }
  .mirage-gallery-item { flex: 0 1 100%; max-width: 100%; }
  .mirage-controls { right: 8px; top: 8px; }
  .mirage-btn { padding: 5px 6px; font-size: 0.8125rem; min-width: 36px; }
}
"""

# Keep the same JS (dark mode, text-scale cookie, YouTube consent)
INJECT_JS = r"""
(function () {
  function setCookie(name, value, days) {
    var expires = "";
    if (days) {
      var d = new Date();
      d.setTime(d.getTime() + (days*24*60*60*1000));
      expires = "; expires=" + d.toUTCString();
    }
    document.cookie = name + "=" + encodeURIComponent(value || "")  + expires + "; path=/";
  }
  function getCookie(name) {
    var nameEQ = name + "=";
    var ca = document.cookie.split(';');
    for(var i=0;i < ca.length;i++) {
      var c = ca[i];
      while (c.charAt(0)==' ') c = c.substring(1,c.length);
      if (c.indexOf(nameEQ) === 0) return decodeURIComponent(c.substring(nameEQ.length,c.length));
    }
    return null;
  }

  // Apply saved dark mode
  function applyMode(mode) {
    if (mode === 'dark') document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
  }
  var storedMode = localStorage.getItem('mirage_mode');
  if (storedMode) applyMode(storedMode);

  // Apply saved text scale (cookie)
  function applyTextScale(scale) {
    if (!scale) scale = 1;
    document.documentElement.style.setProperty('--mirage-font-scale', String(parseFloat(scale)));
  }
  var ts = getCookie('mirage_text_scale') || '1';
  applyTextScale(ts);

  // YouTube consent handling
  function showAllYouTubeEmbeds() {
    document.querySelectorAll('.mirage-embed-wrapper').forEach(function(w) {
      var tpl = w.querySelector('template.mirage-embed-template');
      var placeholder = w.querySelector('.mirage-yt-placeholder');
      if (tpl && placeholder) {
        var clone = tpl.content.cloneNode(true);
        placeholder.parentNode.replaceChild(clone, placeholder);
      }
    });
  }
  function setupPlaceholders() {
    var consent = getCookie('mirage_allow_youtube');
    document.querySelectorAll('.mirage-embed-wrapper').forEach(function(w) {
      var placeholder = w.querySelector('.mirage-yt-placeholder');
      if (!placeholder) return;
      if (consent === 'yes') {
        var tpl = w.querySelector('template.mirage-embed-template');
        if (tpl) {
          var clone = tpl.content.cloneNode(true);
          placeholder.parentNode.replaceChild(clone, placeholder);
        }
      } else {
        var btn = placeholder.querySelector('.mirage-yt-allow');
        if (btn) {
          btn.addEventListener('click', function () {
            setCookie('mirage_allow_youtube', 'yes', 365);
            showAllYouTubeEmbeds();
          });
        }
      }
    });
  }

  // Build vertical controls and label
  function buildControls() {
    var container = document.createElement('div');
    container.className = 'mirage-controls';

    var darkBtn = document.createElement('button');
    darkBtn.className = 'mirage-btn';
    darkBtn.id = 'mirage-dark-toggle';
    darkBtn.textContent = document.documentElement.classList.contains('dark') ? 'Light' : 'Dark';
    darkBtn.addEventListener('click', function () {
      var isDark = document.documentElement.classList.toggle('dark');
      localStorage.setItem('mirage_mode', isDark ? 'dark' : 'light');
      darkBtn.textContent = isDark ? 'Light' : 'Dark';
    });

    var incBtn = document.createElement('button');
    incBtn.className = 'mirage-btn';
    incBtn.title = 'Increase text size';
    incBtn.textContent = 'A+';
    var decBtn = document.createElement('button');
    decBtn.className = 'mirage-btn';
    decBtn.title = 'Decrease text size';
    decBtn.textContent = 'A-';
    var lbl = document.createElement('div');
    lbl.style.padding = '6px 8px';
    lbl.style.fontSize = '13px';
    lbl.style.color = 'var(--muted)';
    lbl.id = 'mirage-font-label';

    function updateLabel(scale) {
      var pct = Math.round(parseFloat(scale) * 100);
      lbl.textContent = pct + '%';
    }

    decBtn.addEventListener('click', function () {
      var cur = parseFloat(getCookie('mirage_text_scale') || '1');
      var next = Math.max(0.8, Math.round((cur - 0.1)*10)/10);
      setCookie('mirage_text_scale', String(next), 365);
      applyTextScale(next);
      updateLabel(next);
    });
    incBtn.addEventListener('click', function () {
      var cur = parseFloat(getCookie('mirage_text_scale') || '1');
      var next = Math.min(2.0, Math.round((cur + 0.1)*10)/10);
      setCookie('mirage_text_scale', String(next), 365);
      applyTextScale(next);
      updateLabel(next);
    });

    updateLabel(ts || '1');
    container.appendChild(darkBtn);
    container.appendChild(incBtn);
    container.appendChild(decBtn);
    container.appendChild(lbl);
    document.body.appendChild(container);
  }

  document.addEventListener('DOMContentLoaded', function () {
    buildControls();
    setupPlaceholders();
  });
})();
"""

# Utility functions and the rest of the app logic remain identical to the previous working version
# For brevity I reuse the robust helpers from previous version (custom-host detection, gallery reformat, link rewriting, categories, etc.)
# The important change for responsiveness is the CSS above and adding the viewport meta tag to each generated page.

# --- Helpers (derive_remote_subdomain, detect_custom_host_from_soup, fetch_remote) ---
def derive_remote_subdomain(wiki_param: str) -> str:
    if '.' in wiki_param:
        return wiki_param.split('.')[0]
    return wiki_param

def detect_custom_host_from_soup(soup: BeautifulSoup):
    c = soup.find('link', rel=lambda r: r and 'canonical' in r)
    if c and c.get('href'):
        try:
            parsed = urlparse(c['href'])
            if parsed.netloc and not parsed.netloc.endswith('.miraheze.org'):
                return parsed.netloc
        except Exception:
            pass
    og = soup.find('meta', property='og:url')
    if og and og.get('content'):
        try:
            parsed = urlparse(og['content'])
            if parsed.netloc and not parsed.netloc.endswith('.miraheze.org'):
                return parsed.netloc
        except Exception:
            pass
    og2 = soup.find('meta', attrs={'name': 'og:url'}) or soup.find('meta', attrs={'name': 'twitter:url'})
    if og2 and og2.get('content'):
        try:
            parsed = urlparse(og2['content'])
            if parsed.netloc and not parsed.netloc.endswith('.miraheze.org'):
                return parsed.netloc
        except Exception:
            pass
    return None

def fetch_remote(url):
    headers = {"User-Agent": USER_AGENT}
    return requests.get(url, headers=headers, timeout=15)

# The app uses the same robust helpers for rewriting links, normalizing images, reformatting galleries/tables,
# removing cookie banners and unwanted elements, youtube placeholders, and categories as in prior version.
# For clarity and to keep this patch self-contained, I include those helpers unchanged below:

#--- link rewriting (aware of remote_sub and custom_host) ---
from urllib.parse import urlparse, urljoin, quote

def rewrite_links_in_tag(tag, wiki_param, remote_sub, custom_host, base_url):
    """
    Rewrite anchors to keep navigation within this proxy.
    Special handling for Category pagination:
      - Query-only ?... links on /wiki/Category:... pages are rewritten to
        /{host}/w/index.php?title=Category:...&... so upstream handles pagination correctly.
      - Absolute /wiki/Category:... links with query are likewise rewritten to index.php.
    """
    base_parsed = urlparse(base_url)
    base_path = base_parsed.path or ""
    base_query = base_parsed.query or ""

    # helper to choose host segment (custom host if present, else remote_sub)
    def host_segment():
        return custom_host if custom_host else remote_sub

    for a in tag.find_all("a", href=True):
        raw = (a["href"] or "").strip()
        if not raw:
            continue
        # leave javascript/mailto alone
        if raw.startswith("javascript:") or raw.startswith("mailto:"):
            continue

        # fragment-only links: do NOT rewrite to wiki path (important for anchors like #mw-pages)
        if raw.startswith("#"):
            a["href"] = raw
            continue

        # protocol-relative -> https:
        if raw.startswith("//"):
            a["href"] = "https:" + raw
            continue

        # absolute URLs
        if raw.startswith("http://") or raw.startswith("https://"):
            parsed = urlparse(raw)
            host = parsed.netloc.lower()
            # handle miraheze absolute links
            if host.endswith(".miraheze.org"):
                sub = host.split(".")[0]
                seg = host_segment() if sub == remote_sub and custom_host else sub
                # If it's a /wiki/Category:... with query, rewrite to /w/index.php?title=...
                if parsed.path.startswith("/wiki/Category:") and parsed.query:
                    title = parsed.path[len("/wiki/"):]  # "Category:Name"
                    new = f"/{quote(seg, safe='')}/w/index.php?title={quote(title, safe='')}"
                    if parsed.query:
                        new += "&" + parsed.query
                    if parsed.fragment:
                        new += "#" + parsed.fragment
                    a["href"] = new
                else:
                    new = f"/{quote(seg, safe='')}{parsed.path}"
                    if parsed.query:
                        new += "?" + parsed.query
                    if parsed.fragment:
                        new += "#" + parsed.fragment
                    a["href"] = new
            else:
                # external hosts: open in new tab
                a["target"] = "_blank"
            continue

        # root-relative links (start with '/')
        if raw.startswith("/"):
            parsed = urlparse(raw)
            # If link points to /wiki/Category:... and includes query (pagefrom/from), map to index.php form
            if parsed.path.startswith("/wiki/Category:") and parsed.query:
                seg = host_segment()
                title = parsed.path[len("/wiki/"):]  # "Category:Name"
                new = f"/{quote(seg, safe='')}/w/index.php?title={quote(title, safe='')}"
                if parsed.query:
                    new += "&" + parsed.query
                if parsed.fragment:
                    new += "#" + parsed.fragment
                a["href"] = new
                continue
            # otherwise, prefix with wiki (use custom_host if present)
            seg = host_segment()
            a["href"] = f"/{quote(seg, safe='')}{raw}"
            continue

        # query-only links (start with '?')
        if raw.startswith("?"):
            # If the current page is a wiki Category page, rewrite to index.php with title param
            # Detect category via base_path (/wiki/Category:...) or base_query (title=Category:...)
            if base_path.startswith("/wiki/Category:") or ("title=Category:" in base_query):
                # derive title
                if base_path.startswith("/wiki/"):
                    title = base_path[len("/wiki/"):]  # "Category:Name"
                else:
                    # fallback to extracting title from base_query if possible
                    # naive extraction: find "title=" substring
                    title = ""
                    for part in base_query.split("&"):
                        if part.startswith("title="):
                            title = part[len("title="):]
                            break
                seg = host_segment()
                # construct index.php URL: /{seg}/w/index.php?title={title}{raw}
                # raw already begins with "?", so append directly
                if title:
                    a["href"] = f"/{quote(seg, safe='')}/w/index.php?title={quote(title, safe='')}{raw}"
                else:
                    # fallback: attach to base path (preserve behavior)
                    a["href"] = f"/{quote(seg, safe='')}{base_path}{raw}"
                continue
            # Not a category page: attach query to base_path (maintain previous behavior)
            seg = host_segment()
            a["href"] = f"/{quote(seg, safe='')}{base_path}{raw}"
            continue

        # relative paths (no leading slash): treat as wiki page name
        seg = host_segment()
        a["href"] = f"/{quote(seg, safe='')}/wiki/{quote(raw, safe='')}"


def normalize_images_in_tag(tag, remote_sub, base_url):
    for img in tag.find_all("img", src=True):
        src = (img["src"] or "").strip()
        if src.startswith("//"):
            img["src"] = "https:" + src
        elif src.startswith("http://") or src.startswith("https://"):
            pass
        elif src.startswith("/"):
            img["src"] = f"https://{remote_sub}.miraheze.org{src}"
        else:
            img["src"] = urljoin(base_url, src)

def find_categories_early(soup, wiki_param, remote_sub, custom_host):
    selectors = [
        ".mw-catlinks", "#catlinks", ".mw-normal-catlinks", ".catlinks",
        "div#catlinks", "div.mw-catlinks"
    ]
    for sel in selectors:
        node = soup.select_one(sel)
        if node:
            anchors = node.find_all("a", href=True)
            items = []
            for a in anchors:
                text = a.get_text(strip=True)
                href = a["href"].strip()
                if href.startswith("/wiki/"):
                    if custom_host:
                        link = f"/{custom_host}{href}"
                    else:
                        link = f"/{remote_sub}{href}"
                elif href.startswith("http://") or href.startswith("https://"):
                    link = href
                else:
                    link = href
                items.append((text, link))
            try:
                node.decompose()
            except Exception:
                pass
            if items:
                return items
    return None

def extract_categories_from_content(content_tag, wiki_param, remote_sub, custom_host):
    for sel in [".mw-catlinks", "#catlinks", ".mw-normal-catlinks", ".catlinks"]:
        node = content_tag.select_one(sel)
        if node:
            anchors = node.find_all("a", href=True)
            items = []
            for a in anchors:
                text = a.get_text(strip=True)
                href = a["href"].strip()
                if href.startswith("/wiki/"):
                    if custom_host:
                        link = f"/{custom_host}{href}"
                    else:
                        link = f"/{remote_sub}{href}"
                elif href.startswith("http://") or href.startswith("https://"):
                    link = href
                else:
                    link = href
                items.append((text, link))
            try:
                node.decompose()
            except Exception:
                pass
            if items:
                return items
    return None

def remove_unwanted_global(soup):
    for tag in list(soup.find_all(["script", "style"])):
        try:
            tag.decompose()
        except Exception:
            pass
    for link in list(soup.find_all("link", rel=True)):
        try:
            if link.get("rel") and ("stylesheet" in link.get("rel") or "preload" in link.get("rel")):
                link.decompose()
        except Exception:
            pass
    for el in list(soup.find_all()):
        if not isinstance(el, Tag):
            continue
        try:
            id_attr = el.get("id", "") or ""
            class_attr = " ".join(el.get("class", [])) if el.get("class") else ""
            combined = (id_attr + " " + class_attr).lower()
            if "cookie" in combined or "cookies" in combined or "vector-body-before-content" in combined:
                el.decompose()
                continue
            text = (el.get_text(" ", strip=True) or "").lower()
            if ("we use cookies" in text) or ("this site uses cookies" in text) or ("cookie" in text and len(text) < 200 and ("consent" in text or "accept" in text or "use cookies" in text)):
                el.decompose()
                continue
        except Exception:
            continue
    selectors = [
        "#mw-head", "header", "nav", ".site-header", "#p-logo", ".portal",
        ".mw-portlet", ".sidebar", ".mw-sidebar", "#footer", ".mw-footer", ".site-footer",
        ".siteNotice", ".sitenotice", ".printfooter", "#catlinks", ".searchbox"
    ]
    for sel in selectors:
        for el in list(soup.select(sel)):
            try:
                el.decompose()
            except Exception:
                pass

def reformat_templates_and_tables(content_tag):
    template_selectors = [
        ".infobox", ".portable-infobox", ".vertical-navbox", ".navbox",
        ".thumb", ".thumbinner", ".sidebar", ".metadata", ".mbox",
        ".ambox", ".hatnote", ".toc"
    ]
    for sel in template_selectors:
        for node in list(content_tag.select(sel)):
            try:
                style = node.get("style", "")
                if style and "float" in style:
                    new_style = ";".join([p for p in style.split(";") if "float" not in p.strip().lower()])
                    new_style = new_style.strip(" ;")
                    if new_style:
                        node["style"] = new_style
                    else:
                        if "style" in node.attrs:
                            del node.attrs["style"]
                classes = node.get("class", [])
                classes = [c for c in classes if c.lower() not in ("floatleft", "floatright", "tright", "tleft")]
                if classes:
                    node["class"] = classes
                else:
                    if "class" in node.attrs and not classes:
                        del node.attrs["class"]
                existing_style = node.get("style", "")
                additions = "max-width:100%!important;float:none!important;clear:both!important;display:block!important;margin:0.6rem auto!important;box-sizing:border-box!important;"
                node["style"] = (existing_style + ";" + additions).strip(";")
                for img in node.find_all("img", src=True):
                    img_style = img.get("style", "")
                    if "max-width" not in img_style:
                        img["style"] = (img_style + ";max-width:100%!important;height:auto!important;display:block;").strip(";")
            except Exception:
                continue
    for table in list(content_tag.find_all("table")):
        try:
            if table.has_attr("align"):
                continue
            style = table.get("style", "")
            if style and "float" in style.lower():
                continue
            classes = [c.lower() for c in table.get("class", [])]
            if any(c in ("floatleft", "floatright", "tleft", "tright") for c in classes):
                continue
            existing_style = table.get("style", "")
            additions = "margin-left:auto;margin-right:auto;max-width:100%;"
            table["style"] = (existing_style + ";" + additions).strip(";")
        except Exception:
            continue

def reformat_galleries(content_tag, remote_sub, base_url):
    for gallery in list(content_tag.select(".gallery, .mw-gallery, .gallerybox")):
        try:
            items = []
            for img_node in gallery.select("img"):
                caption = None
                parent_li = img_node.find_parent(["li", "div"])
                if parent_li:
                    cap = parent_li.select_one(".gallerytext, .gallerycaption")
                    if cap:
                        caption = cap.get_text(" ", strip=True)
                if not caption:
                    caption = img_node.get("alt") or img_node.get("title") or ""
                src = img_node.get("src") or ""
                if src.startswith("//"):
                    src = "https:" + src
                elif src.startswith("/"):
                    src = f"https://{remote_sub}.miraheze.org{src}"
                elif not (src.startswith("http://") or src.startswith("https://")):
                    src = urljoin(base_url, src)
                items.append((src, caption))
            if not items:
                for a in gallery.select("a.galleryimage, a"):
                    img = a.find("img")
                    if not img:
                        continue
                    src = img.get("src") or ""
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = f"https://{remote_sub}.miraheze.org{src}"
                    elif not (src.startswith("http://") or src.startswith("https://")):
                        src = urljoin(base_url, src)
                    caption = img.get("alt") or img.get("title") or a.get("title") or ""
                    items.append((src, caption))
            if not items:
                continue
            gal = BeautifulSoup("", "lxml").new_tag("div", **{"class": "mirage-gallery"})
            for src, caption in items:
                item = BeautifulSoup("", "lxml").new_tag("div", **{"class": "mirage-gallery-item"})
                imgtag = BeautifulSoup("", "lxml").new_tag("img", src=src)
                item.append(imgtag)
                if caption:
                    c = BeautifulSoup("", "lxml").new_tag("div", **{"class": "caption"})
                    c.string = caption
                    item.append(c)
                gal.append(item)
            gallery.replace_with(gal)
        except Exception:
            continue

def detect_and_replace_youtube(content_tag):
    builder = BeautifulSoup("", "lxml")
    for iframe in list(content_tag.find_all("iframe", src=True)):
        src = iframe.get("src", "") or ""
        if ("youtube.com" in src.lower()) or ("youtu.be" in src.lower()) or ("youtube-nocookie.com" in src.lower()):
            try:
                wrapper = builder.new_tag("div", **{"class": "mirage-embed-wrapper"})
                tpl = builder.new_tag("template", **{"class": "mirage-embed-template"})
                parent = iframe.parent
                insert_index = None
                if parent is not None:
                    for idx, child in enumerate(list(parent.contents)):
                        if child is iframe:
                            insert_index = idx
                            break
                iframe_obj = iframe.extract()
                tpl.append(iframe_obj)
                placeholder = builder.new_tag("div", **{"class": "mirage-yt-placeholder"})
                p = builder.new_tag("p")
                p.string = "This Miraheze article contains an embedded YouTube video. Press yes if you're okay seeing it."
                btn = builder.new_tag("button", **{"class": "mirage-yt-allow", "type": "button"})
                btn.string = "Yes"
                placeholder.append(p)
                placeholder.append(btn)
                wrapper.append(tpl)
                wrapper.append(placeholder)
                if parent is not None and insert_index is not None:
                    parent.insert(insert_index, wrapper)
                elif parent is not None:
                    parent.append(wrapper)
                else:
                    content_tag.append(wrapper)
            except Exception:
                continue
    for edit in list(content_tag.select(".mw-editsection")):
        try:
            edit.decompose()
        except Exception:
            pass

# Core fetch-and-transform (keeps custom-host detection and redirects as previously implemented)
def fetch_and_transform(wiki_param, path, mode='wiki', qs=''):
    remote_sub = derive_remote_subdomain(wiki_param)
    if mode == 'wiki':
        remote_url = f"https://{remote_sub}.miraheze.org/wiki/{path}"
    else:
        remote_url = f"https://{remote_sub}.miraheze.org/w/{path}"
        if qs:
            remote_url += '?' + qs

    try:
        r = fetch_remote(remote_url)
    except requests.RequestException as e:
        return Response(f"Error fetching remote wiki: {e}", status=502)
    if r.status_code >= 400:
        return Response(f"Remote returned {r.status_code}", status=r.status_code)
    content_type = r.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        resp = Response(r.content, status=r.status_code)
        resp.headers["Content-Type"] = content_type
        return resp

    original = BeautifulSoup(r.text, "lxml")

    # detect custom host
    detected_host = detect_custom_host_from_soup(original)
    custom_host = None
    if detected_host and not detected_host.endswith('.miraheze.org'):
        custom_host = detected_host

    # redirect to custom host path if appropriate (incoming wiki_param was raw subdomain without dot)
    if custom_host and '.' not in wiki_param:
        out_path = path
        out_qs = qs
        location = f"/{custom_host}/{ 'wiki' if mode=='wiki' else 'w' }/{out_path}"
        if out_qs:
            location = location + "?" + out_qs
        return Response(status=302, headers={"Location": location})

    categories = find_categories_early(original, wiki_param, remote_sub, custom_host)
    remove_unwanted_global(original)

    content_tag = original.find(id="content")
    if not content_tag:
        candidate = original.select_one("#mw-content-text, #bodyContent, main")
        if candidate:
            wrapper = original.new_tag("div", id="content")
            for child in list(candidate.contents):
                wrapper.append(child.extract())
            candidate.replace_with(wrapper)
            content_tag = wrapper
    if not content_tag:
        return Response("No content found on remote page.", status=502)

    for bad in list(content_tag.select("#mw-cookiewarning-container, .pagetop, .vector-body-before-content")):
        try:
            bad.decompose()
        except Exception:
            pass
    for edit in list(content_tag.select(".mw-editsection")):
        try:
            edit.decompose()
        except Exception:
            pass

    doc = BeautifulSoup("<!doctype html><html><head></head><body></body></html>", "lxml")
    head = doc.head
    # meta: charset + viewport to ensure mobile scaling is correct
    head.append(doc.new_tag("meta", charset="utf-8"))
    head.append(doc.new_tag("meta", attrs={
        "name": "viewport",
        "content": "width=device-width, initial-scale=1"
    }))

    style_tag = doc.new_tag("style")
    style_tag.string = INJECT_CSS
    head.append(style_tag)
    script_tag = doc.new_tag("script")
    script_tag.string = INJECT_JS
    head.append(script_tag)

    banner_div = doc.new_tag("div", **{"class": "mirage-banner"})
    strong = doc.new_tag("strong")
    strong.string = "You're viewing this page on Mirage, a privacy frontend to Miraheze licensed under GPL 3.0."
    banner_div.append(strong)
    banner_text = doc.new_tag("span")
    banner_text.string = "All text content on Miraheze is licensed under Creative Commons licenses."
    banner_div.append(banner_text)

    container = doc.new_tag("div", **{"class": "mirage-container"})
    container.append(banner_div)

    content_fragment = BeautifulSoup(str(content_tag), "lxml")
    content_only = content_fragment.find(id="content")
    if not content_only:
        return Response("Unexpected error extracting content.", status=500)

    rewrite_links_in_tag(content_only, wiki_param, remote_sub, custom_host, remote_url)
    normalize_images_in_tag(content_only, remote_sub, remote_url)
    reformat_galleries(content_only, remote_sub, remote_url)
    detect_and_replace_youtube(content_only)
    reformat_templates_and_tables(content_only)

    if not categories:
        categories = extract_categories_from_content(content_only, wiki_param, remote_sub, custom_host)

    container.append(content_only)

    if categories:
        ul = doc.new_tag("ul", **{"class": "categories"})
        for text, link in categories:
            li = doc.new_tag("li")
            a = doc.new_tag("a", href=link)
            a.string = text
            li.append(a)
            ul.append(li)
        container.append(ul)

    doc.body.append(container)
    final_html = str(doc)
    return Response(final_html, content_type="text/html; charset=utf-8")

# Routes accept dots in the wiki path segment
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/<path:wiki>/wiki/<path:page>")
def page_proxy(wiki, page):
    return fetch_and_transform(wiki, page, mode='wiki', qs='')

@app.route("/<path:wiki>/w/<path:rest>")
def w_proxy(wiki, rest):
    qs = request.query_string.decode() or ""
    return fetch_and_transform(wiki, rest, mode='w', qs=qs)

@app.route('/go', methods=['GET', 'POST'])
def go():
    wiki = (request.values.get('wiki') or '').strip()
    page = (request.values.get('page') or '').strip()
    if not wiki or not page:
        return render_template("index.html")
    wiki_safe = "".join([c for c in wiki if c.isalnum() or c in "-_."])
    if not wiki_safe:
        return render_template("index.html")
    segments = [quote(seg, safe='') for seg in page.split('/')]
    page_path = '/'.join(segments)
    return Response(status=302, headers={"Location": f'/{wiki_safe}/wiki/{page_path}'})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)
