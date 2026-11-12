# App para Mac (AudioLibro Libre.app)

Una aplicación que se arrastra a *Aplicaciones* y se abre con doble clic, **sin instalar Python, ffmpeg ni nada más**. Es para **Apple Silicon** (M1, M2, M3, M4).

> **Estado: escrita y verificada solo en parte.** Se desarrolló en Linux, donde **no se puede construir ni ejecutar una app de macOS**. Está probado (en Linux) el lanzador, la autoprueba, la receta de PyInstaller y el flujo completo del binario empaquetado; **no está probado** nada específico de macOS (compilar ffmpeg/espeak-ng, la firma, la ventana, el `.dmg`). La primera construcción en un Mac real casi seguro necesitará pequeños ajustes: por eso existe la autoprueba y el informe de abajo.

## Para quien la usa (el amigo con el Mac)

1. Descarga `AudioLibroLibre-X.Y.Z-arm64.dmg` de la sección **Releases** del repositorio y ábrelo.
2. Arrastra **AudioLibro Libre** a la carpeta **Aplicaciones**.
3. **La primera vez** macOS dirá que no puede comprobar que la app esté libre de software malicioso. Es normal: la app no está firmada con un certificado de pago (99 $/año). Para abrirla **una sola vez**:
   - *macOS 15 (Sequoia) o posterior*: abre la app, pulsa «Hecho» en el aviso, ve a **Ajustes del Sistema → Privacidad y seguridad**, baja hasta el mensaje sobre «AudioLibro Libre» y pulsa **«Abrir igualmente»**.
   - *macOS 14 o anterior*: clic derecho sobre la app → **Abrir** → **Abrir**.
   - Si dice que «está dañada»: abre *Terminal* y escribe `xattr -dr com.apple.quarantine "/Applications/AudioLibro Libre.app"`.
4. Se abre en su propia ventana. Sigue el **tutorial de 2 minutos**.

Tus **datos** (voces descargadas, proyectos y audio) están en `~/Library/Application Support/AudioLibroLibre`. Para desinstalar: arrastra la app a la Papelera y, si quieres, borra esa carpeta. Los proyectos se guardan solos: si cierras la ventana a mitad de una generación, al volver pulsa **Reanudar**.

## Para quien la construye (hace falta un Mac con Apple Silicon)

**Requisitos** (una sola vez):
- Herramientas de línea de comandos de Xcode: `xcode-select --install`.
- Homebrew (<https://brew.sh>): lo usa el script para instalar `autoconf automake libtool pkg-config`, necesarios para compilar espeak-ng.
- Python 3.10–3.13 para arm64 (`brew install python@3.12`).
- Internet y ~3 GB libres. La primera construcción tarda unos 20–30 minutos (compila ffmpeg y espeak-ng).

**Construir:**
```bash
git clone https://github.com/datamauriciovaldez/jabote_books.git
cd jabote_books
./tools/mac/build_app.sh
```
Resultado en `dist/mac/`: el `.dmg`, su `.sha256`, `selftest.txt` y la carpeta `sources/`.

**Fuentes fijadas y verificadas.** `packaging/source-hashes.txt` fija el SHA-256 de LAME 3.100, ffmpeg 6.1.1 y espeak-ng 1.52.0: son **las mismas fuentes que se compilaron y probaron en Linux** (ensayo, ver abajo), comprobadas contra los `.dsc` firmados de Ubuntu. Si una descarga no coincide, el script la borra y se detiene.

**Qué hace el script:**
1. Compila **LAME** y un **ffmpeg LGPL mínimo** (solo AAC, MP3, FLAC, `loudnorm`, mp4, concat; **sin** componentes GPL ni *nonfree*) y comprueba que el resultado no depende de bibliotecas externas.
2. Compila **espeak-ng** (GPL-3) estático con su carpeta de datos.
3. Empaqueta con **PyInstaller** y copia dentro de la `.app` ffmpeg, espeak-ng, sus datos y las licencias.
4. **Firma "ad hoc"** (gratis): Apple Silicon no ejecuta binarios sin ninguna firma.
5. Ejecuta la **autoprueba** de la app empaquetada y crea el `.dmg`.

### Cómo comprobar que funciona (y qué enviar si no)
```bash
open "build/mac/dist/AudioLibro Libre.app"                                  # debe abrirse la ventana
"build/mac/dist/AudioLibro Libre.app/Contents/MacOS/AudioLibroLibre" --self-test
```
La autoprueba imprime un informe como este (todo debe salir `OK`; «Ventana propia» puede ser un `aviso` si falta pywebview):
```
  [OK ] Recursos de la app: …
  [OK ] ffmpeg: ffmpeg version 6.1.1 · LGPL · …/Resources/bin/ffmpeg
  [OK ] ffmpeg: exportación real: FLAC normalizado, MP3 con portada y M4B con capítulos y portada generados
  [OK ] espeak-ng: …/Resources/bin/espeak-ng · «hola mundo» → ˈola mˈundo
RESULTADO: todo correcto
```
Si algo falla, **copia y pega**: la salida del script (últimas ~40 líneas), `build/mac/selftest.txt` y, si es un error de PyInstaller, `build/mac/pyinstaller.log`. Con eso se corrige sin necesidad de acceder a tu Mac.

**Prueba completa (a mano, ~5 min):** abre la app → «Probar con Don Quijote» → elige la voz recomendada (se descarga) → «Escuchar muestra» → generar → exportar → **descargar el ZIP y el M4B** (comprueba que las descargas funcionan dentro de la ventana) → ábrelo con *Libros* o *VLC* y mira los capítulos. Cierra la ventana en mitad de una generación, vuelve a abrir y pulsa **Reanudar**.

### Ensayo en Linux (lo que sí se ha comprobado)
`./tools/mac/rehearse_linux.sh` ejecuta **los mismos scripts** con `AUDIOLIBRO_REHEARSAL=1` y compila LAME, ffmpeg y espeak-ng desde las fuentes fijadas. Resultado verificado: ffmpeg **LGPL** autónomo con `libmp3lame`, AAC, FLAC, `loudnorm`, mp4 y concat; espeak-ng estático que encuentra su carpeta de datos con `ESPEAK_DATA_PATH`; y, metidos en el paquete de PyInstaller de Linux **con el PATH vacío**, la autoprueba en verde y el flujo completo (generar con Piper → exportar M4B con 2 capítulos y MP3 con etiquetas, −19,3 LUFS). El ensayo ya encontró y corrigió dos fallos de los scripts (una comprobación intermitente por `grep -q` + `pipefail` y la detección de `libtool`).

### Lo que NO está verificado (hay que mirarlo en el Mac)
| Punto | Plan B si falla |
|---|---|
| Que la ventana (`pywebview`) abra la app y permita **descargas** y **subir archivos** | El lanzador abre el navegador (`--browser`) |
| Que `espeak-ng` encuentre su carpeta de datos dentro de la `.app` (en Linux sí funciona con `ESPEAK_DATA_PATH`) | Ajustar la ruta en `app/desktop.py` |
| macOS mínimo (`LSMinimumSystemVersion` = 13.0): depende de las ruedas de `onnxruntime` | Ajustar en `packaging/audiolibro.spec` |
| Que el cierre de la ventana termine el proceso y no deje la app «colgada» en el Dock | Ver `app/desktop.py::run` |
| OCR de PDFs escaneados: **no incluido** en esta versión (Tesseract) | Mensaje claro; se puede añadir después |

## Licencias y obligaciones al redistribuir (importante)

El `.dmg` **redistribuye programas con licencia copyleft**: ffmpeg y LAME (LGPL) y espeak-ng (**GPL-3**). Por eso:
- Se compilan sin componentes GPL ni *nonfree* (ffmpeg) y se ejecutan como **programas independientes**, sin enlazarlos.
- **Cada release del `.dmg` debe publicar también, en la misma página, la carpeta `sources/`** (los tarballs exactos de ffmpeg, LAME y espeak-ng; el script los deja en `dist/mac/sources/`) y `ffmpeg-configure-flags.txt`. Es la forma de cumplir la GPL/LGPL.
- Dentro de la app están las licencias (`Contents/Resources/licenses/`) y `THIRD_PARTY_NOTICES.md`.
- **PyInstaller** (GPL-2 con excepción del *bootloader*) es solo una herramienta de construcción. **pywebview** es BSD-3 y **PyObjC** MIT.

Esto sustituye, solo para este instalador, la regla «no se redistribuye nada GPL» (ver `docs/DECISIONS.md`). La instalación con Docker o los scripts sigue sin redistribuir esos programas.

## Publicar una versión para Mac
1. Construye (`./tools/mac/build_app.sh`) y comprueba la autoprueba y la prueba completa.
2. En la *release* de GitHub (a mano, ver `docs/RELEASING.md`) adjunta: el `.dmg`, su `.sha256` y **todo el contenido de `dist/mac/sources/`**.
3. Indica en la descripción: «App sin firmar: la primera vez hay que abrirla desde Ajustes → Privacidad y seguridad».
