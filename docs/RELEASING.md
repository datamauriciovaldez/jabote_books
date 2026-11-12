# Releasing / Publicación de versiones

**[English](#english) · [Español](#español)**

---

<a name="english"></a>
## English

This project **does not use CI/CD** (no GitHub Actions, workflows, bots or paid services). Publishing a release is a manual, short and reproducible procedure carried out on the maintainer's computer.

### 1. Choose the version number

Follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH` (for example, `0.2.0`).

### 2. Update the version (all four locations must match)

| File | Change |
|---|---|
| `pyproject.toml` | `version = "X.Y.Z"` |
| `app/__init__.py` | `__version__ = "X.Y.Z"` |
| `docker-compose.yml` | `image: audiolibro-libre:X.Y.Z` |
| `CHANGELOG.md` | add a `## X.Y.Z` section describing the changes |

A test (`tests/test_project_files.py`) fails if they do not match.

### 3. Review licenses

- If a dependency, model or voice was added or updated, **verify its license at the official source** and update `tools/gen_licenses.py` if necessary.
- If the voice catalogs changed (requires internet access):
  ```bash
  python tools/audit_voices.py > app/tts/voices.json
  python tools/audit_kokoro.py > app/tts/kokoro_voices.json
  python tools/gen_licenses.py > LICENSES.md
  ```
  The audit tools refuse to include non-permissive licenses. Review the result with `git diff`.

### 4. Automated tests

```bash
./check.sh          # ruff + pytest (must finish without errors)
```

### 5. Manual verification (what the tests cannot observe)

Check each item and record in `CHANGELOG.md` anything that could not be verified.

- [ ] `python -m app`, **"Try with Don Quixote"**: generate, **listen** to the audio (is it intelligible? are there cuts?) and export.
- [ ] The M4B opens in a real player with its chapters (VLC, Apple Books, Audiobookshelf, and so on).
- [ ] Pause midway, close the application, reopen it and **resume**.
- [ ] An English voice and, if it changed, Kokoro.
- [ ] On a machine with Docker: `docker compose build && docker compose up -d`, open <http://localhost:8000>, generate and export, then `docker compose down`.
- [ ] `install.sh` in a clean folder (Linux and/or macOS) with `./install.sh --check`.
- [ ] `install.bat` on Windows (double click; with and without ffmpeg and espeak-ng installed).
- [ ] The Colab notebook, if it is offered as an alternative (see below).

### 6. Commit and tag

```bash
git add -A
git commit -m "Release X.Y.Z"
git tag -a vX.Y.Z -m "AudioLibro Libre X.Y.Z"
```

### 7. Package

```bash
./tools/make_release.sh
```
The script verifies that the git working tree is clean, runs `./check.sh` and creates in `dist/`:
`audiolibro-libre-X.Y.Z.zip` (the code exactly as committed; it does **not** include `data/`, `.venv` or uncommitted files) and its `.sha256` checksum.
Review the contents with `unzip -l dist/audiolibro-libre-X.Y.Z.zip | less`.

### 8. Publish (manually, from the web interface)

1. Push the branch and the tag: `git push origin main --tags`.
2. On GitHub, go to **Releases > Draft a new release** and select the tag `vX.Y.Z`.
3. Attach `audiolibro-libre-X.Y.Z.zip` and `audiolibro-libre-X.Y.Z.zip.sha256`.
4. Paste the `CHANGELOG.md` section as the description. **Include the "Test status" section of the README** if anything could not be verified.
5. Publish.

Colab users can paste the release ZIP address into the notebook (`RELEASE_URL`).

### 8 bis. (Optional) macOS application

When publishing the `.dmg` (see `docs/MAC_APP.md`), build it on a Mac with Apple Silicon (`./tools/mac/build_app.sh`) and attach to the same release the `.dmg`, its `.sha256` and **the entire `dist/mac/sources/` folder** (source code of ffmpeg, LAME and espeak-ng; required by their GPL/LGPL licenses). State in the description that the application is **unsigned** (first launch from System Settings > Privacy & Security).

### 9. (Optional) Published Docker image

This is not required: `docker compose up` builds the image locally. To publish it in a **free** registry (for example, a public Docker Hub repository), do so manually:
```bash
docker build -t YOUR_USER/audiolibro-libre:X.Y.Z .
docker push YOUR_USER/audiolibro-libre:X.Y.Z
```
Do not automate this with paid services.

### If something goes wrong

- Before publishing: delete the local tag (`git tag -d vX.Y.Z`) and repeat from step 2.
- After publishing: mark the release as a *pre-release* or delete it from the web interface, and publish `X.Y.(Z+1)` with the fix. Do not rewrite tags that have already been published.

---

<a name="español"></a>
## Español

Este proyecto **no utiliza CI/CD** (ni GitHub Actions, ni flujos de trabajo, ni bots, ni servicios de pago). Publicar una versión es un procedimiento manual, breve y reproducible que se realiza en el ordenador del mantenedor.

### 1. Elegir el número de versión

Siga el [versionado semántico](https://semver.org/lang/es/): `MAYOR.MENOR.PARCHE` (por ejemplo, `0.2.0`).

### 2. Actualizar la versión (los cuatro lugares deben coincidir)

| Archivo | Cambio |
|---|---|
| `pyproject.toml` | `version = "X.Y.Z"` |
| `app/__init__.py` | `__version__ = "X.Y.Z"` |
| `docker-compose.yml` | `image: audiolibro-libre:X.Y.Z` |
| `CHANGELOG.md` | añadir una sección `## X.Y.Z` con los cambios |

Una prueba (`tests/test_project_files.py`) falla si no coinciden.

### 3. Revisar las licencias

- Si se añadió o actualizó una dependencia, un modelo o una voz, **verifique su licencia en la fuente oficial** y actualice `tools/gen_licenses.py` si es necesario.
- Si cambiaron los catálogos de voces (requiere conexión a internet):
  ```bash
  python tools/audit_voices.py > app/tts/voices.json
  python tools/audit_kokoro.py > app/tts/kokoro_voices.json
  python tools/gen_licenses.py > LICENSES.md
  ```
  Las herramientas de auditoría se niegan a incluir licencias no permisivas. Revise el resultado con `git diff`.

### 4. Pruebas automáticas

```bash
./check.sh          # ruff + pytest (debe terminar sin errores)
```

### 5. Verificación manual (lo que las pruebas no pueden observar)

Marque cada punto y anote en `CHANGELOG.md` lo que no haya podido verificarse.

- [ ] `python -m app`, **«Probar con Don Quijote»**: generar, **escuchar** el audio (¿es inteligible? ¿hay cortes?) y exportar.
- [ ] El M4B se abre en un reproductor real con sus capítulos (VLC, Apple Books, Audiobookshelf, etc.).
- [ ] Pausar a mitad, cerrar la aplicación, volver a abrirla y **reanudar**.
- [ ] Una voz en inglés y, si cambió, Kokoro.
- [ ] En una máquina con Docker: `docker compose build && docker compose up -d`, abrir <http://localhost:8000>, generar y exportar, y luego `docker compose down`.
- [ ] `install.sh` en una carpeta limpia (Linux y/o macOS) con `./install.sh --check`.
- [ ] `install.bat` en Windows (doble clic; con y sin ffmpeg y espeak-ng instalados).
- [ ] El cuaderno de Colab, si se ofrece como alternativa (véase más abajo).

### 6. Commit y etiqueta

```bash
git add -A
git commit -m "Release X.Y.Z"
git tag -a vX.Y.Z -m "AudioLibro Libre X.Y.Z"
```

### 7. Empaquetado

```bash
./tools/make_release.sh
```
El script comprueba que el árbol de trabajo de git está limpio, ejecuta `./check.sh` y crea en `dist/`:
`audiolibro-libre-X.Y.Z.zip` (el código exactamente como está en el commit; **no** incluye `data/`, `.venv` ni archivos sin confirmar) y su suma de comprobación `.sha256`.
Revise el contenido con `unzip -l dist/audiolibro-libre-X.Y.Z.zip | less`.

### 8. Publicación (manual, desde la interfaz web)

1. Suba la rama y la etiqueta: `git push origin main --tags`.
2. En GitHub, vaya a **Releases > Draft a new release** y seleccione la etiqueta `vX.Y.Z`.
3. Adjunte `audiolibro-libre-X.Y.Z.zip` y `audiolibro-libre-X.Y.Z.zip.sha256`.
4. Pegue la sección de `CHANGELOG.md` como descripción. **Incluya la sección «Estado de las pruebas» del README** si algo no pudo verificarse.
5. Publique.

Quienes usen Colab pueden pegar la dirección del ZIP de la versión en el cuaderno (`RELEASE_URL`).

### 8 bis. (Opcional) Aplicación para macOS

Al publicar el `.dmg` (véase `docs/MAC_APP.md`), constrúyalo en un Mac con Apple Silicon (`./tools/mac/build_app.sh`) y adjunte a la misma versión el `.dmg`, su `.sha256` y **toda la carpeta `dist/mac/sources/`** (código fuente de ffmpeg, LAME y espeak-ng; obligatorio por sus licencias GPL/LGPL). Indique en la descripción que la aplicación **no está firmada** (primer inicio desde Ajustes del Sistema > Privacidad y seguridad).

### 9. (Opcional) Imagen de Docker publicada

No es necesario: `docker compose up` construye la imagen en local. Para publicarla en un registro **gratuito** (por ejemplo, un repositorio público de Docker Hub), hágalo manualmente:
```bash
docker build -t SU_USUARIO/audiolibro-libre:X.Y.Z .
docker push SU_USUARIO/audiolibro-libre:X.Y.Z
```
No automatice este paso con servicios de pago.

### Si algo sale mal

- Antes de publicar: elimine la etiqueta local (`git tag -d vX.Y.Z`) y repita desde el paso 2.
- Después de publicar: marque la versión como *pre-release* o elimínela desde la interfaz web, y publique `X.Y.(Z+1)` con la corrección. No reescriba etiquetas ya publicadas.
