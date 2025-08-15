# app.py
from flask import Flask, Response, render_template
import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin
import os

app = Flask(__name__)

USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
)

# CSS (container 800px, dark mode, text-scale, controls, etc.)
INJECT_CSS = """\
:root {
  --page-bg: #f3f6fb;
  --container-bg: #ffffff;
  --text: #0b1220;
  --accent: #1e66d0;
  --accent-strong: #174ea6;
  --banner-bg: #eef6ff;
  --muted: #6b7280;
  --mirage-font-scale: 1;
}
html.dark {
  --page-bg: #0b1220;
  --container-bg: #0f1724;
  --text: #e6eef8;
  --accent: #5ea3ff;
  --accent-strong: #2b7be6;
  --banner-bg: #07203a;
  --muted: #9aa9bf;
}
body {
  margin: 0;
  background: linear-gradient(180deg, var(--page-bg), var(--page-bg));
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
/* centered container: 800px default, responsive on small screens */
.mirage-container {
  width: 800px;
  max-width: calc(100% - 32px);
  margin: 36px auto;
  background: var(--container-bg);
  padding: 18px;
  box-shadow: 0 6px 18px rgba(11,18,32,0.06);
  border-radius: 6px;
  box-sizing: border-box;
  overflow-wrap: break-word;
}
/* banner and divider */
.mirage-banner {
  border-top: 1px solid rgba(0,0,0,0.06);
  padding-top: 12px;
  margin-bottom: 14px;
  font-size: 13px;
  color: var(--muted);
  display: block;
}
.mirage-banner strong {
  color: var(--text);
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
}
/* content styling uses font-scale variable */
#content {
  line-height: 1.6;
  font-size: calc(16px * var(--mirage-font-scale));
  box-sizing: border-box;
}
#content h1, #content h2, #content h3 {
  color: var(--accent-strong);
}
a {
  color: var(--accent);
  text-decoration: none;
}
a:hover { text-decoration: underline; }
/* categories */
ul.categories { list-style: none; padding: 0; margin-top: 1.2rem; border-top: 1px solid rgba(0,0,0,0.06); padding-top: 8px; }
ul.categories li { display: inline; margin-right: 0.6rem; font-size: 13px; color: var(--muted); }
/* images */
#content img { max-width: 100%; height: auto; display: block; margin: 0.6rem 0; }
/* templates / infoboxes / navboxes: make them responsive and non-floating */
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
/* ensure images inside templates are constrained */
#content .infobox img,
#content .thumb img,
#content .portable-infobox img {
  max-width: 100% !important;
  height: auto !important;
  display: block;
}
/* tables: default center unless explicitly aligned/float classes present */
#content table {
  margin-left: auto;
  margin-right: auto;
  box-sizing: border-box;
  max-width: 100%;
  overflow: auto;
}
/* preserve tables that explicitly float or declare alignment */
#content table.floatleft,
#content table.floatright,
#content table[align],
#content table[style*="float"] {
  margin-left: 0;
  margin-right: 0;
}
/* YouTube placeholder styling */
.mirage-embed-wrapper { margin: 0.6rem 0; text-align: center; }
.mirage-yt-placeholder {
  background: rgba(0,0,0,0.03);
  padding: 10px;
  border-radius: 6px;
  display: inline-block;
  max-width: 100%;
}
.mirage-yt-placeholder p { margin: 0 0 8px 0; color: var(--muted); font-size: 14px; }
.mirage-yt-allow { background: var(--accent); color: white; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; }
.mirage-yt-allow:hover { background: var(--accent-strong); }
/* control buttons (dark mode & text size) */
.mirage-controls { position: fixed; right: 18px; top: 12px; z-index: 1200; display:flex; gap:8px; }
.mirage-btn {
  background: var(--container-bg);
  color: var(--text);
  border: 1px solid rgba(0,0,0,0.06);
  padding: 6px 8px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(11,18,32,0.06);
}
.mirage-btn:focus { outline: 2px solid var(--accent); outline-offset: 2px; }
/* responsive adjustments */
@media (max-width: 820px) {
  .mirage-container { width: auto; margin: 16px; padding: 12px; }
  .mirage-controls { right: 12px; top: 8px; }
  .mirage-btn { padding: 5px 6px; font-size: 12px; }
}
"""

# JavaScript: dark-mode, text-scale controls, YouTube consent (cookies)
INJECT_JS = """\
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

  function applyMode(mode) {
    if (mode === 'dark') document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
  }
  var storedMode = localStorage.getItem('mirage_mode');
  if (storedMode) applyMode(storedMode);

  function applyTextScale(scale) {
    if (!scale) scale = 1;
    document.documentElement.style.setProperty('--mirage-font-scale', String(parseFloat(scale)));
  }
  var ts = getCookie('mirage_text_scale') || '1';
  applyTextScale(ts);

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

    var decBtn = document.createElement('button');
    decBtn.className = 'mirage-btn';
    decBtn.title = 'Decrease text size';
    decBtn.textContent = 'A-';
    var incBtn = document.createElement('button');
    incBtn.className = 'mirage-btn';
    incBtn.title = 'Increase text size';
    incBtn.textContent = 'A+';
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
    container.appendChild(decBtn);
    container.appendChild(incBtn);
    container.appendChild(lbl);
    document.body.appendChild(container);
  }

  document.addEventListener('DOMContentLoaded', function () {
    buildControls();
    setupPlaceholders();
  });
})();
"""

def fetch_remote(url):
    headers = {"User-Agent": USER_AGENT}
    return requests.get(url, headers=headers, timeout=15)

def rewrite_links_in_tag(tag, wiki, base_url):
    for a in tag.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("javascript:") or href.startswith("mailto:"):
            continue
        if href.startswith("http://") or href.startswith("https://"):
            parsed = urlparse(href)
            host = parsed.netloc.lower()
            if host.endswith(".miraheze.org"):
                sub = host.split(".")[0]
                new = urljoin("/", f"{sub}{parsed.path}")
                if parsed.query:
                    new += "?" + parsed.query
                a["href"] = new
            else:
                a["target"] = "_blank"
        elif href.startswith("//"):
            a["href"] = "https:" + href
        elif href.startswith("/"):
            a["href"] = f"/{wiki}{href}"
        else:
            a["href"] = f"/{wiki}/wiki/{href}"

def normalize_images_in_tag(tag, wiki, base_url):
    for img in tag.find_all("img", src=True):
        src = img["src"].strip()
        if src.startswith("//"):
            img["src"] = "https:" + src
        elif src.startswith("http://") or src.startswith("https://"):
            pass
        elif src.startswith("/"):
            img["src"] = f"https://{wiki}.miraheze.org{src}"
        else:
            img["src"] = urljoin(base_url, src)

def remove_unwanted_global(soup):
    # Remove scripts, style tags, and remote stylesheet links
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

    # Remove elements with id/class containing 'cookie' (case-insensitive)
    for el in list(soup.find_all()):
        if not isinstance(el, Tag):
            continue
        try:
            id_attr = el.get("id", "") or ""
            class_attr = " ".join(el.get("class", [])) if el.get("class") else ""
            combined = (id_attr + " " + class_attr).lower()
            if "cookie" in combined or "cookies" in combined:
                el.decompose()
                continue
            text = (el.get_text(" ", strip=True) or "").lower()
            if ("we use cookies" in text) or ("this site uses cookies" in text) or ("cookie" in text and len(text) < 200 and ("consent" in text or "accept" in text or "use cookies" in text)):
                el.decompose()
                continue
        except Exception:
            continue

    # Remove other obvious header/footer selectors
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

def find_categories_early(soup, wiki):
    """
    Look for categories before we strip anything.
    Uses a whitelist of known selectors used by MediaWiki variants.
    Returns list of (text, link) tuples or None.
    Removes the cat container it finds to avoid duplication.
    """
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
                    link = f"/{wiki}{href}"
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
    # if none found using those selectors, return None
    return None

def extract_categories_from_content(content_tag, wiki):
    """Fallback: try to extract categories from inside the content fragment."""
    # common cat containers inside content
    for sel in [".mw-catlinks", "#catlinks", ".mw-normal-catlinks", ".catlinks"]:
        node = content_tag.select_one(sel)
        if node:
            anchors = node.find_all("a", href=True)
            items = []
            for a in anchors:
                text = a.get_text(strip=True)
                href = a["href"].strip()
                if href.startswith("/wiki/"):
                    link = f"/{wiki}{href}"
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

def remove_unwanted_global(soup):
    # Remove scripts, style tags, and remote stylesheet links
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

    # Remove elements with id/class containing 'cookie' (case-insensitive)
    for el in list(soup.find_all()):
        if not isinstance(el, Tag):
            continue
        try:
            id_attr = el.get("id", "") or ""
            class_attr = " ".join(el.get("class", [])) if el.get("class") else ""
            combined = (id_attr + " " + class_attr).lower()
            if "cookie" in combined or "cookies" in combined:
                el.decompose()
                continue
            text = (el.get_text(" ", strip=True) or "").lower()
            if ("we use cookies" in text) or ("this site uses cookies" in text) or ("cookie" in text and len(text) < 200 and ("consent" in text or "accept" in text or "use cookies" in text)):
                el.decompose()
                continue
        except Exception:
            continue

    # Remove other obvious header/footer selectors
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

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/<wiki>/wiki/<path:page>")
def page_proxy(wiki, page):
    remote_url = f"https://{wiki}.miraheze.org/wiki/{page}"
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

    # Extract categories immediately (before any cleanup)
    categories = find_categories_early(original, wiki)

    # Now remove global unwanted elements
    remove_unwanted_global(original)

    # If categories still not found, we will try to find them inside content later
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

    # Defensive removal
    c = content_tag.find(id="mw-cookiewarning-container")
    if c:
        try:
            c.decompose()
        except Exception:
            pass

    for edit in list(content_tag.select(".mw-editsection")):
        try:
            edit.decompose()
        except Exception:
            pass

    # Build output document
    doc = BeautifulSoup("<!doctype html><html><head></head><body></body></html>", "lxml")
    head = doc.head
    meta = doc.new_tag("meta", charset="utf-8")
    head.append(meta)
    style_tag = doc.new_tag("style")
    style_tag.string = INJECT_CSS
    head.append(style_tag)
    script_tag = doc.new_tag("script")
    script_tag.string = INJECT_JS
    head.append(script_tag)

    # Banner
    banner_div = doc.new_tag("div", **{"class": "mirage-banner"})
    strong = doc.new_tag("strong")
    strong.string = "You're viewing this page on Mirage, a privacy frontend to Miraheze licensed under GPL 3.0."
    banner_div.append(strong)
    banner_text = doc.new_tag("span")
    banner_text.string = "All text content on Miraheze is licensed under Creative Commons licenses."
    banner_div.append(banner_text)

    container = doc.new_tag("div", **{"class": "mirage-container"})
    container.append(banner_div)

    # Reparse content for safe manipulation
    content_fragment = BeautifulSoup(str(content_tag), "lxml")
    content_only = content_fragment.find(id="content")
    if not content_only:
        return Response("Unexpected error extracting content.", status=500)

    rewrite_links_in_tag(content_only, wiki, remote_url)
    normalize_images_in_tag(content_only, wiki, remote_url)
    detect_and_replace_youtube(content_only)
    reformat_templates_and_tables(content_only)

    # If we did not find categories earlier, try to extract from content fragment
    if not categories:
        categories = extract_categories_from_content(content_only, wiki)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=False)
