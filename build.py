"""Genera el sitio estático a partir de src/.  Uso: python build.py"""
import html, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
RENDER = os.path.join(ROOT, "_build", "render")
IMG_OUT = os.path.join(ROOT, "assets", "img")

SES = {
    1: ("Calidad de SW, QC y SQA", "Importancia de la calidad, definiciones, QC vs SQA, técnicas y casos históricos de fallas."),
    2: ("Modelos de Calidad Total", "Evolución de la calidad, TQM, Deming, Baldrige, EFQM, Iberoamericano, PNC y Six Sigma."),
    3: ("Técnicas de Calidad de SW", "Técnicas estáticas y dinámicas, revisiones, herramientas (SonarQube, ESLint…) e ISO/IEC 25010."),
    4: ("SQAP e ISO/IEC 12207:2017", "Plan de aseguramiento IEEE 730, modelos de mejora del proceso y procesos de la 12207."),
    5: ("NTP-ISO/IEC 12207:2016", "Norma Técnica Peruana, obligatoriedad en el Estado y aplicación proceso-actividad-tarea."),
    6: ("SPICE (15504) y CMMI", "Madurez y capacidad del proceso: ISO/IEC 15504/33000, CMMI v1.3, V2.0, V3.0 y SCAMPI."),
    7: ("MoProSoft, MPS.BR y más", "Modelos para PYMEs: MoProSoft, MPS.BR, COMPETISOFT, IT Mark e ISO/IEC 29110."),
}
DECK_SHORT = {
    "semana-01-calidad-de-software": "s1",
    "semana-02-modelos-de-calidad-total": "s2-modelos",
    "semana-02-lectura-evolucion-de-la-gestion-de-la-calidad-y-sus-dimensio": "s2-lectura",
    "semana-03-tecnicas-de-calidad-de-software": "s3",
    "semana-04-introduccion-al-sqap": "s4-sqap",
    "semana-04-ejemplo-ejemplos-con-sqap": "s4-sqap-ej",
    "semana-04-iso-iec-12207-2017-procesos": "s4-12207",
    "semana-04-modelos-de-mejora-del-proceso-de-sw": "s4-mejora",
    "semana-04-ejemplo-caso-de-estudio-practico-iso-12207": "s4-caso",
    "semana-05-modelo-de-calidad-iso-12207": "s5-modelo",
    "semana-05-ntp-12207-2016-resumen-y-guia": "s5-ntp",
    "semana-05-profesora-practica-sesion-5": "s5-practica",
}
SKIP_ABBR = {"abbr", "a", "code", "h1", "h2", "h3", "h4", "summary", "th", "dt", "figcaption"}


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def write(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def slug(s):
    s = unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60] or "sec"


# ---------- siglas ----------
def load_siglas():
    merged, per = {}, {}
    for n in SES:
        p = os.path.join(SRC, "data", f"siglas-s{n}.json")
        per[n] = []
        if not os.path.exists(p):
            continue
        try:
            arr = json.loads(read(p))
        except Exception as e:
            print(f"! siglas-s{n}.json invalido: {e}")
            continue
        for it in arr:
            s = str(it.get("sigla", "")).strip()
            if not s:
                continue
            per[n].append(it)
            m = merged.setdefault(s, {"sigla": s, "en": it.get("en", "") or "", "es": it.get("es", "") or "", "ses": set()})
            m["ses"].add(n)
            if not m["en"] and it.get("en"):
                m["en"] = it["en"]
            if not m["es"] and it.get("es"):
                m["es"] = it["es"]
    return merged, per


def abbr_title(m):
    en, es = m["en"].strip(), m["es"].strip()
    if en and es and en.lower() != es.lower():
        return f"{en} – {es}"
    return en or es


def make_abbr_regex(merged):
    keys = [k for k in merged if len(k) >= 2 and sum(c.isupper() or c.isdigit() for c in k) >= 2 and abbr_title(merged[k])]
    keys.sort(key=len, reverse=True)
    if not keys:
        return None, {}
    esc_map = {html.escape(k, quote=False): k for k in keys}
    pat = "|".join(re.escape(k) for k in esc_map)
    rx = re.compile(r"(?<![A-Za-z0-9ÁÉÍÓÚÑáéíóúñ/._-])(" + pat + r")(?![A-Za-z0-9ÁÉÍÓÚÑáéíóúñ_-])")
    return rx, esc_map


def add_abbr(src, rx, esc_map, merged):
    if rx is None:
        return src
    parts = re.split(r"(<[^>]+>)", src)
    stack, seen, out = [], set(), []
    for part in parts:
        if part.startswith("<"):
            m = re.match(r"<\s*(/)?\s*([a-zA-Z0-9]+)", part)
            if m:
                tag = m.group(2).lower()
                if m.group(1):
                    if tag in stack:
                        while stack and stack.pop() != tag:
                            pass
                elif not part.endswith("/>") and tag not in ("img", "br", "hr"):
                    stack.append(tag)
                    if tag == "section":
                        seen = set()
            out.append(part)
            continue
        if not part.strip() or any(t in SKIP_ABBR for t in stack):
            out.append(part)
            continue

        def rep(mo):
            k = esc_map.get(mo.group(1))
            if not k or k in seen:
                return mo.group(1)
            seen.add(k)
            return f'<abbr title="{html.escape(abbr_title(merged[k]))}">{mo.group(1)}</abbr>'

        out.append(rx.sub(rep, part))
    return "".join(out)


# ---------- imágenes ----------
_img_done = {}


def convert_img(ref):
    """@img/<mazo>/pNN.png -> assets/img/<corto>/pNN.webp ; devuelve (ruta, w, h) o None"""
    if ref in _img_done:
        return _img_done[ref]
    deck, fname = ref[5:].split("/", 1)
    src = os.path.join(RENDER, deck, fname)
    if not os.path.exists(src):
        print(f"! imagen inexistente {ref}")
        _img_done[ref] = None
        return None
    short = DECK_SHORT.get(deck, slug(deck)[:20])
    out_rel = f"assets/img/{short}/{os.path.splitext(fname)[0]}.webp"
    out = os.path.join(ROOT, *out_rel.split("/"))
    from PIL import Image
    im = Image.open(src).convert("RGB")
    if im.width > 1000:
        im = im.resize((1000, round(im.height * 1000 / im.width)), Image.LANCZOS)
    if not os.path.exists(out) or os.path.getmtime(out) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        im.save(out, "WEBP", quality=72, method=6)
    _img_done[ref] = (out_rel, im.width, im.height)
    return _img_done[ref]


def fix_imgs(src):
    def rep(m):
        tag = m.group(0)
        sm = re.search(r'src="(@img/[^"]+)"', tag)
        if not sm:
            return tag
        r = convert_img(sm.group(1))
        if not r:
            return ""
        path, w, h = r
        tag = tag.replace(sm.group(0), f'src="{path}" width="{w}" height="{h}" loading="lazy" decoding="async"')
        return f'<a href="{path}" target="_blank" rel="noopener">{tag}</a>'
    return re.sub(r"<img\b[^>]*>", rep, src)


# ---------- layout ----------
def nav(active):
    items = [("index.html", "Inicio")] + [(f"s{n}-teoria.html", f"S{n}") for n in SES] + [("normas.html", "Normas"), ("siglas.html", "Siglas"), ("examen.html", "Examen")]
    return "".join(f'<a href="{h}"{" class=on" if h == active else ""}>{t}</a>' for h, t in items)


def page(title, body, active, toc=None, desc=""):
    toc_html = ""
    if toc:
        lis = "".join(f'<li><a href="#{i}">{html.escape(t)}</a></li>' for i, t in toc)
        toc_html = f'<aside class="toc"><details open><summary>Índice</summary><ol>{lis}</ol></details></aside>'
    wrap = "wrap" if toc else "wrap full"
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · Repaso Calidad de SW</title>
<meta name="description" content="{html.escape(desc or title)}">
<link rel="stylesheet" href="assets/css/style.css"></head>
<body>
<header class="top"><a class="brand" href="index.html">Repaso Parcial · Calidad de SW</a><nav class="menu">{nav(active)}</nav></header>
<div class="{wrap}">{toc_html}<main>
{body}
</main></div>
<footer>Calidad de Software 20W0703 · FISI-UNMSM 2026-II · Repaso de estudio (Semanas 1–7) basado en el material de clase y entregables.</footer>
<script src="assets/js/app.js" defer></script>
</body></html>
"""


def build_toc(src):
    toc, used = [], set()

    def rep(m):
        attrs, inner = m.group(1), m.group(2)
        im = re.search(r'id="([^"]+)"', attrs)
        sid = im.group(1) if im else slug(strip_tags(inner))
        while sid in used:
            sid += "-2"
        used.add(sid)
        toc.append((sid, strip_tags(inner)))
        if im:
            return m.group(0)
        return f'<h2 id="{sid}"{attrs}>{inner}</h2>'

    # h2 dentro de section con id: usamos el id de la section
    def sec_rep(m):
        sid, rest = m.group(1), m.group(2)
        h = re.match(r"(\s*<h2)([^>]*)>(.*?)</h2>", rest, re.S)
        if h:
            used.add(sid)
            toc.append((sid, strip_tags(h.group(3))))
        return m.group(0)

    if re.search(r'<section[^>]*id="[^"]+"[^>]*>\s*<h2', src):
        for m in re.finditer(r'<section[^>]*id="([^"]+)"[^>]*>(\s*<h2[^>]*>.*?</h2>)', src, re.S):
            sec_rep(m)
        # h2 sueltos fuera de section con id
        return src, toc
    src = re.sub(r"<h2([^>]*)>(.*?)</h2>", rep, src, flags=re.S)
    return src, toc


def siglas_section(items, merged):
    if not items:
        return ""
    seen, rows = set(), []
    for it in sorted(items, key=lambda x: str(x.get("sigla", "")).lower()):
        s = str(it.get("sigla", "")).strip()
        if s in seen:
            continue
        seen.add(s)
        rows.append(f"<tr><td><b>{html.escape(s)}</b></td><td>{html.escape(it.get('en', '') or '—')}</td><td>{html.escape(it.get('es', '') or '—')}</td></tr>")
    return f'<section id="siglas"><h2>Siglas de la sesión ({len(rows)})</h2><div class="tabla"><table><thead><tr><th>Sigla</th><th>Inglés</th><th>Español</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>\n'


def tabs(n, kind):
    t = "on" if kind == "teoria" else ""
    p = "on" if kind == "practica" else ""
    return f'<div class="tabs"><a class="{t}" href="s{n}-teoria.html">📖 Teoría S{n}</a><a class="{p}" href="s{n}-practica.html">🧩 Práctica S{n}</a><a href="examen.html?s={n}">📝 Examen S{n}</a></div>'


def prevnext(n, kind):
    a = f'<a href="s{n-1}-{kind}.html">← S{n-1} · {SES[n-1][0]}</a>' if n > 1 else "<span></span>"
    b = f'<a href="s{n+1}-{kind}.html">S{n+1} · {SES[n+1][0]} →</a>' if n < 7 else '<a href="examen.html">Ir al examen →</a>'
    return f'<div class="pn">{a}{b}</div>'


STATS = {}


def build_fragment(path, rx, esc_map, merged, extra_before_glos=""):
    if not os.path.exists(path):
        return None
    src = read(path).replace("<!--FIN-->", "")
    src = fix_imgs(src)
    if extra_before_glos:
        if '<section id="glosario"' in src:
            src = src.replace('<section id="glosario"', extra_before_glos + '<section id="glosario"', 1)
        else:
            src += extra_before_glos
    src = add_abbr(src, rx, esc_map, merged)
    src, toc = build_toc(src)
    return src, toc


def main():
    merged, per = load_siglas()
    rx, esc_map = make_abbr_regex(merged)
    for n in SES:
        for kind in ("teoria", "practica"):
            path = os.path.join(SRC, kind, f"s{n}.html")
            extra = siglas_section(per.get(n, []), merged) if kind == "teoria" else ""
            r = build_fragment(path, rx, esc_map, merged, extra)
            name = f"s{n}-{kind}.html"
            label = "Teoría" if kind == "teoria" else "Práctica"
            if r is None:
                body = tabs(n, kind) + f"<h1>Sesión {n} · {label}</h1><p class='lead'>Contenido en preparación.</p>" + prevnext(n, kind)
                write(os.path.join(ROOT, name), page(f"S{n} {label}", body, f"s{n}-teoria.html"))
                print(f"- {name}: sin fuente")
                continue
            src, toc = r
            STATS[(n, kind)] = {
                "conceptos": src.count('class="concepto"'),
                "casos": len(re.findall(r'class="caso"', src)),
                "figuras": src.count("<figure"),
                "glos": len(re.findall(r"<dt>", src)),
            }
            body = tabs(n, kind) + src + prevnext(n, kind)
            write(os.path.join(ROOT, name), page(f"S{n} {label} · {SES[n][0]}", body, f"s{n}-teoria.html", toc, SES[n][1]))
            print(f"+ {name}: {STATS[(n, kind)]} toc={len(toc)}")

    # normas
    r = build_fragment(os.path.join(SRC, "normas.html"), rx, esc_map, merged)
    if r:
        src, toc = r
        write(os.path.join(ROOT, "normas.html"), page("Normas y modelos de calidad", src, "normas.html", toc, "Fichas de todas las normas y modelos de calidad del sílabo."))
        print(f"+ normas.html toc={len(toc)}")

    # siglas
    rows = []
    for k in sorted(merged, key=lambda x: x.lower()):
        m = merged[k]
        ses = " ".join(f'<a href="s{s}-teoria.html#siglas">S{s}</a>' for s in sorted(m["ses"]))
        rows.append(f"<tr><td><b>{html.escape(k)}</b></td><td>{html.escape(m['en'] or '—')}</td><td>{html.escape(m['es'] or '—')}</td><td>{ses}</td></tr>")
    body = f"""<h1>Diccionario de siglas</h1>
<p class="lead">Todas las siglas usadas en el repaso (<span id="nfilt">{len(rows)}</span> de {len(rows)}). En las páginas de teoría, toca o pasa el cursor sobre una sigla subrayada para ver su significado.</p>
<p><input id="filtro" type="search" placeholder="Buscar sigla o significado… ej. SQA, madurez, IEEE"></p>
<div class="tabla"><table id="siglas-tabla"><thead><tr><th>Sigla</th><th>Inglés</th><th>Español</th><th>Sesión</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"""
    write(os.path.join(ROOT, "siglas.html"), page("Siglas", body, "siglas.html", None, "Diccionario de siglas del curso Calidad de Software."))
    print(f"+ siglas.html: {len(rows)} siglas")

    # banco
    banco = {"mcq": [], "fill": [], "casos": []}
    for n in SES:
        p = os.path.join(SRC, "data", f"banco-s{n}.json")
        if not os.path.exists(p):
            print(f"- banco-s{n}.json no existe")
            continue
        try:
            d = json.loads(read(p))
        except Exception as e:
            print(f"! banco-s{n}.json invalido: {e}")
            continue
        for q in d.get("mcq", []):
            if len(q.get("o", [])) == 4 and q.get("a") in (0, 1, 2, 3):
                q.setdefault("s", n)
                banco["mcq"].append(q)
        for q in d.get("fill", []):
            q.setdefault("s", n)
            banco["fill"].append(q)
        for q in d.get("casos", []):
            q.setdefault("s", [n])
            banco["casos"].append(q)
    write(os.path.join(ROOT, "assets", "js", "banco.js"), "window.BANCO=" + json.dumps(banco, ensure_ascii=False, separators=(",", ":")) + ";\n")
    print(f"+ banco.js: mcq={len(banco['mcq'])} fill={len(banco['fill'])} casos={len(banco['casos'])}")

    # examen
    body = f"""<h1>Simulacro de examen parcial</h1>
<p class="lead">Arma tu examen: elige las sesiones, cuántas preguntas teóricas (opción múltiple y para completar) y cuántos casos prácticos quieres resolver. Las opciones se barajan en cada intento.</p>
<p class="fuente" id="stats"></p>
<div class="cfg">
 <div><label>Sesiones</label><div class="chk" id="ses"></div></div>
 <div><label for="nm">Preguntas de opción múltiple</label><select id="nm"><option>0</option><option selected>5</option><option>10</option><option>15</option><option>20</option><option>30</option><option value="all">Todas</option></select></div>
 <div><label for="nf">Preguntas para completar</label><select id="nf"><option>0</option><option>3</option><option selected>5</option><option>10</option><option>15</option><option value="all">Todas</option></select></div>
 <div><label for="nc">Casos prácticos a resolver</label><select id="nc"><option>0</option><option selected>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option value="all">Todos</option></select></div>
 <div><label><input type="checkbox" id="nuevas" checked> Priorizar preguntas no vistas</label><button class="btn sec" id="reiniciar" type="button">Borrar historial</button></div>
 <div><button class="btn" id="generar" type="button">Generar examen</button></div>
</div>
<div id="examen" class="hide"></div>
<div class="score hide" id="barra"><button class="btn" id="calificar" type="button">Calificar</button><span>⏱ <span id="reloj">0:00</span></span><span id="res"></span></div>
<script src="assets/js/banco.js"></script><script src="assets/js/examen.js"></script>"""
    write(os.path.join(ROOT, "examen.html"), page("Examen", body, "examen.html", None, "Simulacro configurable del examen parcial."))
    print("+ examen.html")

    # index
    cards = []
    for n, (t, d) in SES.items():
        st = STATS.get((n, "teoria"), {})
        sp = STATS.get((n, "practica"), {})
        meta = f"{st.get('conceptos', 0)} conceptos · {sp.get('casos', 0)} casos · {st.get('glos', 0)} términos"
        cards.append(f'<div class="card"><span class="tag">Semana {n}</span><h3>{t}</h3><p>{d}</p><p class="fuente">{meta}</p><div class="lnk"><a class="btn" href="s{n}-teoria.html">Teoría</a><a class="btn sec" href="s{n}-practica.html">Práctica</a><a class="btn sec" href="examen.html?s={n}">Examen</a></div></div>')
    body = f"""<h1>Repaso Parcial · Calidad de Software</h1>
<p class="lead">Material de estudio de las Semanas 1 a 7 del sílabo (Unidades 1 y 2) para el examen parcial de la Semana 8. Cada sesión tiene <b>teoría</b> (concepto + ejemplo inmediato, normas, trampas de examen, siglas y glosario) y <b>práctica</b> (primero el caso a analizar y luego soluciones alternativas).</p>
<div class="clave"><h4>Cómo estudiar</h4><ul>
<li>Lee la <b>Teoría</b> de cada sesión: las cajas azules son conceptos, las verdes ejemplos, las amarillas normas y las rojas trampas de examen.</li>
<li>Resuelve la <b>Práctica</b> sin abrir la solución; luego compárala: en calidad no hay solución única.</li>
<li>Repasa las <a href="normas.html">Normas</a> (énfasis del sílabo) y el <a href="siglas.html">diccionario de siglas</a>.</li>
<li>Termina con el <a href="examen.html">Simulacro</a>: tú eliges cuántas preguntas y cuántos casos.</li></ul></div>
<h2 id="sesiones">Sesiones</h2>
<div class="grid">{''.join(cards)}</div>
<h2 id="extra">Herramientas de repaso</h2>
<div class="grid">
<div class="card"><h3>📘 Normas y modelos</h3><p>Fichas comparativas: ISO 9001, ISO 9126/25010, IEEE 730, ISO/IEC 12207, NTP 12207, SPICE, CMMI, MoProSoft, MPS.BR, COMPETISOFT, IT Mark, ISO/IEC 29110.</p><div class="lnk"><a class="btn" href="normas.html">Abrir</a></div></div>
<div class="card"><h3>🔤 Siglas</h3><p>{len(rows)} siglas con su significado en inglés y español, con buscador.</p><div class="lnk"><a class="btn" href="siglas.html">Abrir</a></div></div>
<div class="card"><h3>📝 Simulacro</h3><p>{len(banco['mcq'])} preguntas de opción múltiple, {len(banco['fill'])} para completar y {len(banco['casos'])} casos de desarrollo.</p><div class="lnk"><a class="btn" href="examen.html">Empezar</a></div></div>
</div>"""
    write(os.path.join(ROOT, "index.html"), page("Inicio", body, "index.html", None, "Repaso completo para el examen parcial de Calidad de Software (UNMSM)."))
    print("+ index.html")


if __name__ == "__main__":
    main()
