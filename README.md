# Repaso Parcial · Calidad de Software (UNMSM · FISI · 2026-II)

Sitio estático de estudio para el examen parcial (Semanas 1–7 del sílabo):

- **Teoría por sesión** (`sN-teoria.html`): concepto + ejemplo inmediato, normas, trampas de examen, imágenes de las diapositivas, siglas y glosario al final.
- **Práctica por sesión** (`sN-practica.html`): primero el caso a analizar, luego problemas identificados y soluciones alternativas (casos de clase, entregables semanales y casos nuevos de alta complejidad).
- **Normas** (`normas.html`): fichas y comparativas de todas las normas/modelos del sílabo.
- **Siglas** (`siglas.html`): diccionario con buscador.
- **Simulacro** (`examen.html`): eliges sesiones, nº de preguntas de opción múltiple, nº para completar y nº de casos; califica y explica cada respuesta.

Sin frameworks ni dependencias: HTML + un CSS + JS mínimo. Funciona en móvil y PC.

## Publicar en GitHub Pages

```bash
git init
git add .
git commit -m "Repaso parcial Calidad de Software"
git branch -M main
git remote add origin https://github.com/<tu-usuario>/repaso-calidad-software.git
git push -u origin main
```

Luego en GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / `(root)` → Save**.
La URL queda como `https://<tu-usuario>.github.io/repaso-calidad-software/`.

## Regenerar el sitio

El contenido fuente está en `src/` (fragmentos HTML y JSON). Tras editarlo:

```bash
python build.py
```

Requiere Python 3 y Pillow (`pip install pillow`) solo si se agregan imágenes nuevas desde `_build/render/` (carpeta local, no se sube al repo).

## Ver en local

```bash
python -m http.server 8765
```

y abrir `http://127.0.0.1:8765/`.
