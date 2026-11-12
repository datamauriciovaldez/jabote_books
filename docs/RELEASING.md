# Cómo publicar una versión (a mano)

Este proyecto **no usa CI/CD** (ni GitHub Actions, ni workflows, ni bots, ni servicios de pago). Publicar una versión es un proceso manual, corto y reproducible en tu ordenador.

## 1. Elige el número de versión

[SemVer](https://semver.org/lang/es/): `MAYOR.MENOR.PARCHE` (p. ej. `0.2.0`).

## 2. Actualiza la versión (los 4 sitios deben coincidir)

| Archivo | Qué cambiar |
|---|---|
| `pyproject.toml` | `version = "X.Y.Z"` |
| `app/__init__.py` | `__version__ = "X.Y.Z"` |
| `docker-compose.yml` | `image: audiolibro-libre:X.Y.Z` |
| `CHANGELOG.md` | añade una sección `## X.Y.Z` con los cambios |

Una prueba (`tests/test_project_files.py`) falla si no coinciden.

## 3. Revisa licencias

- ¿Has añadido o actualizado una dependencia, un modelo o una voz? **Verifica su licencia en la fuente oficial** y actualiza `tools/gen_licenses.py` si hace falta.
- Si cambiaron los catálogos de voces (necesita internet):
  ```bash
  python tools/audit_voices.py > app/tts/voices.json
  python tools/audit_kokoro.py > app/tts/kokoro_voices.json
  python tools/gen_licenses.py > LICENSES.md
  ```
  Las herramientas de auditoría se niegan a incluir licencias no permisivas. Revisa el resultado con `git diff`.

## 4. Pruebas automáticas

```bash
./check.sh          # ruff + pytest (debe terminar sin errores)
```

## 5. Comprobación manual (lo que las pruebas no ven)

Marca cada punto; anota en `CHANGELOG.md` lo que no hayas podido comprobar.

- [ ] `python -m app`, **«Probar con Don Quijote»**: generar, **escuchar** el audio (¿se entiende? ¿hay cortes?) y exportar.
- [ ] El M4B se abre en un reproductor real con sus capítulos (VLC, Apple Books, Audiobookshelf…).
- [ ] Pausar a mitad, cerrar la aplicación, volver a abrirla y **reanudar**.
- [ ] Una voz en inglés y, si cambió, Kokoro.
- [ ] En una máquina con Docker: `docker compose build && docker compose up -d`, abrir <http://localhost:8000>, generar y exportar; `docker compose down`.
- [ ] `install.sh` en una carpeta limpia (Linux y/o Mac) con `./install.sh --check`.
- [ ] `install.bat` en Windows (doble clic; con y sin ffmpeg/espeak-ng instalados).
- [ ] Notebook de Colab, si lo usas como alternativa (ver más abajo).

## 6. Commit y etiqueta

```bash
git add -A
git commit -m "Release X.Y.Z"
git tag -a vX.Y.Z -m "AudioLibro Libre X.Y.Z"
```

## 7. Empaquetar

```bash
./tools/make_release.sh
```
Comprueba que el árbol de git está limpio, ejecuta `./check.sh` y crea en `dist/`:
`audiolibro-libre-X.Y.Z.zip` (el código tal como está en el commit; **no** incluye `data/`, `.venv` ni nada sin commitear) y su suma de comprobación `.sha256`.
Revisa el contenido: `unzip -l dist/audiolibro-libre-X.Y.Z.zip | less`.

## 8. Publicar (a mano, desde la web)

1. Sube la rama y la etiqueta: `git push origin main --tags`.
2. En GitHub: **Releases → Draft a new release**, elige la etiqueta `vX.Y.Z`.
3. Adjunta `audiolibro-libre-X.Y.Z.zip` y `audiolibro-libre-X.Y.Z.zip.sha256`.
4. Pega la sección de `CHANGELOG.md` como descripción. **Incluye la sección «Estado de las pruebas» del README** si algo no se pudo comprobar.
5. Publica.

Quien use Colab puede pegar la dirección del ZIP de la release en el notebook (`RELEASE_URL`).

## 8 bis. (Opcional) App para Mac

Si publicas el `.dmg` (ver `docs/MAC_APP.md`), construye en un Mac con Apple Silicon (`./tools/mac/build_app.sh`) y adjunta a la misma release: el `.dmg`, su `.sha256` y **todo `dist/mac/sources/`** (código fuente de ffmpeg, LAME y espeak-ng: es obligatorio por su licencia GPL/LGPL). Indica en la descripción que la app **no está firmada** (primer arranque desde Ajustes → Privacidad y seguridad).

## 9. (Opcional) Imagen Docker publicada

No hace falta: `docker compose up` construye la imagen en local. Si quieres publicarla en un registro **gratuito** (p. ej. Docker Hub, repositorio público), hazlo a mano:
```bash
docker build -t TU_USUARIO/audiolibro-libre:X.Y.Z .
docker push TU_USUARIO/audiolibro-libre:X.Y.Z
```
No automatices esto con servicios de pago.

## Si algo sale mal

- Antes de publicar: borra la etiqueta local (`git tag -d vX.Y.Z`) y repite desde el paso 2.
- Ya publicado: marca la release como *pre-release* o bórrala desde la web, y publica `X.Y.(Z+1)` con la corrección. No reescribas etiquetas ya publicadas.
