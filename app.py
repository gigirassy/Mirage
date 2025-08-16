# app.py
from flask import Flask, Response, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, urljoin, quote
import os
import hashlib
import json
import time
import gzip
from pathlib import Path

app = Flask(__name__)

USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0"
)

# --- CSS (responsive, gentle light mode, gallery, vertical controls, search panel) ---
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
html, body { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
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
  font-size: 16px;
}
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
.mirage-banner {
  border-top: 1px solid rgba(0,0,0,0.04);
  padding-top: 12px;
  margin-bottom: 14px;
  font-size: 0.875rem;
  color: var(--muted);
  display: block;
}
.mirage-banner strong { color: var(--text); display: block; margin-bottom: 6px; font-weight: 600; }
#content {
  line-height: 1.65;
  font-size: calc(1rem * var(--mirage-font-scale));
  box-sizing: border-box;
  word-break: break-word;
}
#content h1, #content h2, #content h3 { color: var(--accent-strong); margin-top: 1.2rem; margin-bottom: 0.6rem; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* hide pagetop and vector pre-content markers */
#content .pagetop,
.vector-body-before-content { display: none !important; visibility: hidden !important; }

/* Gallery styles */
.mirage-gallery { display: flex; flex-wrap: wrap; gap: var(--gap); margin: 0.6rem 0; justify-content: flex-start; align-items: flex-start; }
.mirage-gallery-item { box-sizing: border-box; flex: 0 1 calc(33.333% - var(--gap)); max-width: calc(33.333% - var(--gap)); text-align: center; }
.mirage-gallery-item img { width: 100%; height: auto; display: block; border-radius: 6px; }
.mirage-gallery-item .caption { font-size: 0.8125rem; color: var(--muted); margin-top: 6px; line-height: 1.25; }
@media (max-width: 880px) { .mirage-gallery-item { flex: 0 1 calc(50% - var(--gap)); max-width: calc(50% - var(--gap)); } }
@media (max-width: 520px) { .mirage-gallery-item { flex: 0 1 100%; max-width: 100%; } }

#content img { max-width: 100%; height: auto; display: block; margin: 0.6rem 0; }

/* templates / infoboxes / navboxes: responsive */
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

/* Tables: center by default unless alignment/float explicitly set */
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
#content table[style*="float"] { margin-left: 0; margin-right: 0; }

/* YouTube placeholder */
.mirage-embed-wrapper { margin: 0.6rem 0; text-align: center; }
.mirage-yt-placeholder { background: rgba(0,0,0,0.03); padding: 10px; border-radius: 6px; display: inline-block; max-width: 100%; }
.mirage-yt-placeholder p { margin: 0 0 8px 0; color: var(--muted); font-size: 0.875rem; }
.mirage-yt-allow { background: var(--accent); color: #fff; border: none; padding: 6px 10px; border-radius: 4px; cursor: pointer; }
.mirage-yt-allow:hover { background: var(--accent-strong); }

/* vertical controls */
.mirage-controls { position: fixed; right: 12px; top: 12px; z-index: 1200; display:flex; flex-direction: column; gap:8px; align-items: flex-end; }
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

ul.categories { list-style: none; padding: 0; margin-top: 1.2rem; border-top: 1px solid rgba(0,0,0,0.04); padding-top: 8px; }
ul.categories li { display: inline; margin-right: 0.6rem; font-size: 0.8125rem; color: var(--muted); }

/* Search panel (right-side slide-in) */
.mirage-search-panel {
  position: fixed;
  right: 12px;
  top: 12px;
  width: 360px;
  max-width: calc(100% - 48px);
  height: calc(100% - 24px);
  background: var(--container-bg);
  box-shadow: 0 8px 30px rgba(11,18,32,0.12);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  z-index: 1400;
  padding: 12px;
  box-sizing: border-box;
  overflow: hidden;
}
.mirage-search-panel header { display:flex; align-items:center; gap:8px; margin-bottom: 8px; }
.mirage-search-panel input[type="search"] {
  flex: 1;
  padding: 8px;
  border-radius: 6px;
  border: 1px solid rgba(0,0,0,0.08);
  background: transparent;
  color: var(--text);
  font-size: 0.95rem;
  box-sizing: border-box;
}
.mirage-search-panel .mirage-search-close { background: transparent; border: none; color: var(--muted); cursor: pointer; font-size: 1rem; padding: 6px; }
.mirage-search-panel .mirage-search-results { overflow: auto; padding: 4px; margin-top: 6px; flex: 1; }
.mirage-search-result { padding: 8px; border-radius: 6px; margin-bottom: 6px; background: rgba(0,0,0,0.02); cursor: pointer; }
.mirage-search-result a { color: var(--accent); text-decoration: none; display: block; }
.mirage-search-result .muted { color: var(--muted); font-size: 0.9rem; margin-top: 4px; }

@media (max-width: 880px) {
  .mirage-container { margin: 16px auto; padding-left: 14px; padding-right: 14px; }
  .mirage-gallery-item { flex: 0 1 calc(50% - var(--gap)); max-width: calc(50% - var(--gap)); }
  .mirage-controls { right: 8px; top: 8px; }
  .mirage-btn { padding: 6px 6px; font-size: 0.8125rem; min-width: 40px; }
}
@media (max-width: 520px) {
  .mirage-container { margin: 12px; padding-left: 12px; padding-right: 12px; border-radius: 6px; }
  .mirage-gallery-item { flex: 0 1 100%; max-width: 100%; }
  .mirage-controls { right: 8px; top: 8px; }
  .mirage-btn { padding: 5px 6px; font-size: 0.8125rem; min-width: 36px; }
  .mirage-search-panel { right: 8px; top: 8px; width: calc(100% - 16px); height: calc(100% - 16px); padding: 10px; border-radius: 6px; }
}
"""

# --- JS (controls, search UI, youtube consent) ---
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

  function currentWikiIdentifier() {
    var parts = window.location.pathname.split('/');
    for (var i=0;i<parts.length;i++) {
      if (parts[i]) return parts[i];
    }
    return null;
  }

  var searchPanel = null;
  var searchInput = null;
  var searchResults = null;
  var searchDebounce = null;

  function closeSearchPanel() {
    if (searchPanel) {
      searchPanel.parentNode.removeChild(searchPanel);
      searchPanel = null;
      searchInput = null;
      searchResults = null;
    }
  }

  function openSearchPanel() {
    if (searchPanel) return;
    var wiki = currentWikiIdentifier() || '';
    searchPanel = document.createElement('div');
    searchPanel.className = 'mirage-search-panel';
    var header = document.createElement('header');
    var input = document.createElement('input');
    input.type = 'search';
    input.placeholder = 'Search article prefix...';
    input.autocomplete = 'off';
    input.autocapitalize = 'none';
    input.spellcheck = false;
    header.appendChild(input);
    var closeBtn = document.createElement('button');
    closeBtn.className = 'mirage-search-close';
    closeBtn.type = 'button';
    closeBtn.innerText = '✕';
    closeBtn.title = 'Close';
    closeBtn.addEventListener('click', closeSearchPanel);
    header.appendChild(closeBtn);
    searchPanel.appendChild(header);
    var results = document.createElement('div');
    results.className = 'mirage-search-results';
    searchPanel.appendChild(results);
    document.body.appendChild(searchPanel);
    searchInput = input;
    searchResults = results;
    setTimeout(function(){ input.focus(); }, 40);
    input.addEventListener('input', function (ev) {
      var q = (input.value || '').trim();
      if (searchDebounce) clearTimeout(searchDebounce);
      searchDebounce = setTimeout(function () { performSearch(wiki, q); }, 300);
    });
  }

  function performSearch(wiki, q) {
    if (!searchResults) return;
    searchResults.innerHTML = '<div style="padding:8px;color:var(--muted)">Searching…</div>';
    var url = '/api/search?wiki=' + encodeURIComponent(wiki) + '&q=' + encodeURIComponent(q);
    fetch(url, { credentials: 'same-origin' })
      .then(function (res) { return res.json(); })
      .then(function (data) { renderSearchResults(data.results || []); })
      .catch(function () { searchResults.innerHTML = '<div style="padding:8px;color:var(--muted)">Search failed.</div>'; });
  }

  function renderSearchResults(items) {
    if (!searchResults) return;
    if (!items || items.length === 0) {
      searchResults.innerHTML = '<div style="padding:8px;color:var(--muted)">No results.</div>';
      return;
    }
    var html = '';
    for (var i=0;i<items.length;i++) {
      var it = items[i];
      html += '<div class="mirage-search-result"><a href="' + it.href + '">' + escapeHtml(it.title) + '</a></div>';
    }
    searchResults.innerHTML = html;
    Array.from(searchResults.querySelectorAll('.mirage-search-result a')).forEach(function (el) {
      el.addEventListener('click', function (ev) { closeSearchPanel(); });
    });
  }

  function escapeHtml(s) {
    return (s + '').replace(/[&<>"']/g, function (m) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m];
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

    var searchBtn = document.createElement('button');
    searchBtn.className = 'mirage-btn';
    searchBtn.title = 'Search this wiki';
    searchBtn.textContent = 'Search';
    searchBtn.addEventListener('click', function () { openSearchPanel(); });

    updateLabel(ts || '1');
    container.appendChild(darkBtn);
    container.appendChild(incBtn);
    container.appendChild(decBtn);
    container.appendChild(searchBtn);
    container.appendChild(lbl);
    document.body.appendChild(container);
  }

  document.addEventListener('DOMContentLoaded', function () {
    buildControls();
    setupPlaceholders();
  });
})();
"""

CACHE_DIR = os.getenv("MIRAGE_CACHE_DIR", "./cache")
MAX_CACHE_BYTES = int(os.getenv("MIRAGE_CACHE_MAX", str(40 * 1024 * 1024)))  # 40MB default
CACHE_TTL = int(os.getenv("MIRAGE_CACHE_TTL", str(7 * 24 * 3600)))  # 7 days default
_META_FILENAME = "meta.json"
_MIRAGE_CACHE_KEY = os.getenv("MIRAGE_CACHE_KEY", "").strip()


try:
    from cryptography.fernet import Fernet, InvalidToken
    _FERNET_AVAILABLE = True
except Exception:
    Fernet = None
    InvalidToken = Exception
    _FERNET_AVAILABLE = False

FERNET = None
if _MIRAGE_CACHE_KEY:
    if not _FERNET_AVAILABLE:
        # cryptography not installed — cannot create Fernet; we'll fallback to gzip storage
        FERNET = None
    else:
        try:
            # Fernet expects a urlsafe_base64-encoded 32-byte key
            key_bytes = _MIRAGE_CACHE_KEY.encode() if isinstance(_MIRAGE_CACHE_KEY, str) else _MIRAGE_CACHE_KEY
            FERNET = Fernet(key_bytes)
        except Exception:
            # invalid key -> disable Fernet (fallback to gzip)
            FERNET = None
else:
    FERNET = None

# ---- file-cache helpers (encrypted when FERNET != None) ----
def _ensure_cache_dir():
    try:
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
        meta_path = _meta_path()
        if not os.path.exists(meta_path):
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
    except Exception:
        return

def _meta_path():
    return os.path.join(CACHE_DIR, _META_FILENAME)

def _load_meta():
    try:
        p = _meta_path()
        if not os.path.exists(p):
            return {}
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _save_meta(meta):
    try:
        p = _meta_path()
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(meta, f)
        os.replace(tmp, p)
    except Exception:
        pass

def _key_to_filename(key: str) -> str:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"{h}.bin"

def _prune_cache_if_needed(meta):
    try:
        total = sum(v.get("size", 0) for v in meta.values())
        if total <= MAX_CACHE_BYTES:
            return meta
        items = sorted(meta.items(), key=lambda kv: kv[1].get("atime", 0))
        for fname, info in items:
            fpath = os.path.join(CACHE_DIR, fname)
            try:
                if os.path.exists(fpath):
                    os.remove(fpath)
            except Exception:
                pass
            total -= info.get("size", 0)
            meta.pop(fname, None)
            if total <= MAX_CACHE_BYTES:
                break
        _save_meta(meta)
    except Exception:
        pass
    return meta

def cache_get(key: str):
    """
    Return cached HTML string if valid and not expired, otherwise None.
    Encrypted files are decrypted using FERNET when available. Fallback uses gzip.
    """
    try:
        _ensure_cache_dir()
        fname = _key_to_filename(key)
        fpath = os.path.join(CACHE_DIR, fname)
        if not os.path.exists(fpath):
            meta = _load_meta()
            if fname in meta:
                meta.pop(fname, None)
                _save_meta(meta)
            return None

        stat = os.stat(fpath)
        now = time.time()
        # TTL check (based on mtime)
        if (now - stat.st_mtime) > CACHE_TTL:
            try:
                os.remove(fpath)
            except Exception:
                pass
            meta = _load_meta()
            if fname in meta:
                meta.pop(fname, None)
                _save_meta(meta)
            return None

        # read bytes
        with open(fpath, "rb") as f:
            blob = f.read()

        if FERNET is not None:
            try:
                decrypted = FERNET.decrypt(blob)
                html = decrypted.decode("utf-8")
            except InvalidToken:
                # can't decrypt -> remove corrupted/unreadable cache entry
                try:
                    os.remove(fpath)
                except Exception:
                    pass
                meta = _load_meta()
                if fname in meta:
                    meta.pop(fname, None)
                    _save_meta(meta)
                return None
        else:
            # fallback: gzip-compressed storage
            try:
                html = gzip.decompress(blob).decode("utf-8")
            except Exception:
                # unreadable -> remove
                try:
                    os.remove(fpath)
                except Exception:
                    pass
                meta = _load_meta()
                if fname in meta:
                    meta.pop(fname, None)
                    _save_meta(meta)
                return None

        # update meta atime
        meta = _load_meta()
        entry = meta.get(fname, {})
        entry["atime"] = now
        entry["mtime"] = stat.st_mtime
        entry["size"] = stat.st_size
        entry["key"] = key
        meta[fname] = entry
        _save_meta(meta)
        return html
    except Exception:
        return None

def cache_set(key: str, html: str):
    """
    Save html under key. If FERNET is set, persist encrypted bytes; else gzip compress.
    Returns True on success.
    """
    try:
        _ensure_cache_dir()
        fname = _key_to_filename(key)
        fpath = os.path.join(CACHE_DIR, fname)
        tmp = fpath + ".tmp"

        if FERNET is not None:
            payload = FERNET.encrypt(html.encode("utf-8"))
            # write bytes
            with open(tmp, "wb") as f:
                f.write(payload)
        else:
            # fallback: gzip-compress text (not encrypted)
            blob = gzip.compress(html.encode("utf-8"))
            with open(tmp, "wb") as f:
                f.write(blob)

        os.replace(tmp, fpath)
        stat = os.stat(fpath)
        now = time.time()
        meta = _load_meta()
        meta[fname] = {
            "key": key,
            "size": stat.st_size,
            "mtime": stat.st_mtime,
            "atime": now
        }
        meta = _prune_cache_if_needed(meta)
        _save_meta(meta)
        return True
    except Exception:
        return False

def derive_remote_subdomain(wiki_param: str) -> str:
    # If wiki_param contains dot (custom host), remote subdomain is first label; else it's the wiki_param
    if '.' in wiki_param:
        return wiki_param.split('.')[0]
    return wiki_param

def detect_custom_host_from_soup(soup: BeautifulSoup):
    # inspect canonical and og:url meta tags for custom domain
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

# Rewrite links with special handling for categories and fragments
def rewrite_links_in_tag(tag, wiki_param, remote_sub, custom_host, base_url):
    base_parsed = urlparse(base_url)
    base_path = base_parsed.path or ""
    base_query = base_parsed.query or ""

    def host_segment():
        return custom_host if custom_host else remote_sub

    for a in tag.find_all("a", href=True):
        raw = (a["href"] or "").strip()
        if not raw:
            continue
        if raw.startswith("javascript:") or raw.startswith("mailto:"):
            continue
        # fragments: keep as-is
        if raw.startswith("#"):
            a["href"] = raw
            continue
        if raw.startswith("//"):
            a["href"] = "https:" + raw
            continue
        if raw.startswith("http://") or raw.startswith("https://"):
            parsed = urlparse(raw)
            host = parsed.netloc.lower()
            if host.endswith(".miraheze.org"):
                sub = host.split(".")[0]
                seg = host_segment() if (custom_host and sub == remote_sub) else sub
                # category path + query -> route to index.php for correct pagination
                if parsed.path.startswith("/wiki/Category:") and parsed.query:
                    title = parsed.path[len("/wiki/"):]
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
                a["target"] = "_blank"
            continue
        if raw.startswith("/"):
            parsed = urlparse(raw)
            if parsed.path.startswith("/wiki/Category:") and parsed.query:
                seg = host_segment()
                title = parsed.path[len("/wiki/"):]
                new = f"/{quote(seg, safe='')}/w/index.php?title={quote(title, safe='')}"
                if parsed.query:
                    new += "&" + parsed.query
                if parsed.fragment:
                    new += "#" + parsed.fragment
                a["href"] = new
                continue
            seg = host_segment()
            a["href"] = f"/{quote(seg, safe='')}{raw}"
            continue
        if raw.startswith("?"):
            # if base page is a category, rewrite to index.php?title=Category:...
            if base_path.startswith("/wiki/Category:") or ("title=Category:" in base_query):
                if base_path.startswith("/wiki/"):
                    title = base_path[len("/wiki/"):]
                else:
                    title = ""
                    for part in base_query.split("&"):
                        if part.startswith("title="):
                            title = part[len("title="):]
                            break
                seg = host_segment()
                if title:
                    a["href"] = f"/{quote(seg, safe='')}/w/index.php?title={quote(title, safe='')}{raw}"
                else:
                    a["href"] = f"/{quote(seg, safe='')}{base_path}{raw}"
                continue
            seg = host_segment()
            a["href"] = f"/{quote(seg, safe='')}{base_path}{raw}"
            continue
        # relative path without slash -> wiki page
        seg = host_segment()
        a["href"] = f"/{quote(seg, safe='')}/wiki/{quote(raw, safe='')}"

# Normalize image src attributes to use absolute links where appropriate
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

# Extract categories early (from raw soup) to avoid accidental removal
def find_categories_early(soup, wiki_param, remote_sub, custom_host):
    selectors = [".mw-catlinks", "#catlinks", ".mw-normal-catlinks", ".catlinks", "div#catlinks", "div.mw-catlinks"]
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

# Remove global unwanteds (scripts, style, cookie banners, vector class, headers/footers)
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
    selectors = ["#mw-head", "header", "nav", ".site-header", "#p-logo", ".portal", ".mw-portlet", ".sidebar", ".mw-sidebar", "#footer", ".mw-footer", ".site-footer", ".siteNotice", ".sitenotice", ".printfooter", "#catlinks", ".searchbox"]
    for sel in selectors:
        for el in list(soup.select(sel)):
            try:
                el.decompose()
            except Exception:
                pass

# Reformat templates and tables for responsive layout
def reformat_templates_and_tables(content_tag):
    template_selectors = [".infobox", ".portable-infobox", ".vertical-navbox", ".navbox", ".thumb", ".thumbinner", ".sidebar", ".metadata", ".mbox", ".ambox", ".hatnote", ".toc"]
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

# Convert gallery markup to inline responsive gallery
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

# Replace YouTube iframes with consent placeholders
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

# --- Core fetch and transform ---
def fetch_and_transform(wiki_param, path, mode='wiki', qs=''):
    """
    This version attempts to serve from the file cache first (HTML only).
    Cache key includes wiki_param|mode|path|qs so different pages/queries are separate.
    """
    # build canonical cache key
    cache_key = f"{wiki_param}|{mode}|{path}|{qs}"

    # Try cache first (only cache text/html pages we previously stored)
    cached = cache_get(cache_key)
    if cached is not None:
        # Return cached HTML response directly
        return Response(cached, content_type="text/html; charset=utf-8")

    # Not cached -> continue original flow to fetch + transform
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

    # detect custom host via canonical / og:url
    detected_host = detect_custom_host_from_soup(original)
    custom_host = None
    if detected_host and not detected_host.endswith('.miraheze.org'):
        custom_host = detected_host

    # redirect if custom_host detected and incoming wiki_param was raw subdomain (no dot)
    if custom_host and '.' not in wiki_param:
        out_path = path
        out_qs = qs
        location = f"/{custom_host}/{ 'wiki' if mode=='wiki' else 'w' }/{out_path}"
        if out_qs:
            location = location + "?" + out_qs
        return Response(status=302, headers={"Location": location})

    # extract categories early, then remove global bits
    categories = find_categories_early(original, wiki_param, remote_sub, custom_host)
    remove_unwanted_global(original)

    # find content
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

    # remove in-content undesired elements
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

    # build minimal doc
    doc = BeautifulSoup("<!doctype html><html><head></head><body></body></html>", "lxml")
    head = doc.head
    head.append(doc.new_tag("meta", attrs={"charset": "utf-8"}))
    head.append(doc.new_tag("meta", attrs={"name": "viewport", "content": "width=device-width, initial-scale=1"}))
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

    # rewrites and normalization
    rewrite_links_in_tag(content_only, wiki_param, remote_sub, custom_host, remote_url)
    normalize_images_in_tag(content_only, remote_sub, remote_url)

    # galleries -> youtube -> templates/tables
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

    # cache the generated HTML (best-effort; failures are non-fatal)
    try:
        cache_set(cache_key, final_html)
    except Exception:
        pass

    return Response(final_html, content_type="text/html; charset=utf-8")

# --- Routes ---

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

# API search endpoint: Special:AllPages/<prefix>
@app.route('/api/search')
def api_search():
    wiki = (request.args.get('wiki') or '').strip()
    q = (request.args.get('q') or '').strip()
    if not wiki or not q:
        return jsonify({"results": []})
    remote_sub = derive_remote_subdomain(wiki)
    try:
        fetch_path = quote(q, safe='')
    except Exception:
        fetch_path = q
    remote_url = f"https://{remote_sub}.miraheze.org/wiki/Special:AllPages/{fetch_path}"
    try:
        r = fetch_remote(remote_url)
    except Exception:
        return jsonify({"results": []})
    if r.status_code != 200:
        return jsonify({"results": []})
    soup = BeautifulSoup(r.text, "lxml")
    content = soup.find(id="mw-content-text") or soup.find(id="content") or soup
    results = []
    seen = set()
    for a in content.find_all("a", href=True):
        href = a["href"].strip()
        if not href.startswith("/wiki/"):
            continue
        title_path = href[len("/wiki/"):]
        title_path = title_path.split('#', 1)[0].rstrip('/')
        if not title_path:
            continue
        text = a.get_text(" ", strip=True) or title_path
        key = (title_path, text)
        if key in seen:
            continue
        seen.add(key)
        proxied_href = f"/{wiki}/wiki/{quote(title_path, safe='/')}"
        results.append({"title": text, "href": proxied_href})
        if len(results) >= 100:
            break
    return jsonify({"results": results})

# /go redirect (main page form fallback)
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
