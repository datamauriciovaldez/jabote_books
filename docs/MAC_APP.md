# macOS application / Aplicación para macOS

**[English](#english) · [Español](#español)**

---

<a name="english"></a>
## English

A native application (`AudioLibro Libre.app`) that is dragged to *Applications* and opened with a double click, **without installing Python, ffmpeg or any other software**. It targets **Apple Silicon** (M1, M2, M3, M4).

> **Status: partially verified.** The project was developed on Linux, where a macOS application can be neither built nor run. The launcher, the self-test, the PyInstaller recipe and the complete workflow of the packaged binary have been verified on Linux. **Nothing macOS-specific has been tested**: compiling ffmpeg and espeak-ng, code signing, the native window and the `.dmg`. The first build on a Mac will very likely require small adjustments; the self-test and the report format described below exist for that purpose.

### For users

1. Download `AudioLibroLibre-X.Y.Z-arm64.dmg` from the **Releases** section of the repository and open it.
2. Drag **AudioLibro Libre** into the **Applications** folder.
3. **On first launch**, macOS reports that it cannot verify that the application is free of malicious software. This is expected: the application is not signed with a paid developer certificate (USD 99 per year). To open it **once**:
   - *macOS 15 (Sequoia) or later:* open the application, select "Done" in the warning, go to **System Settings > Privacy & Security**, scroll to the message about "AudioLibro Libre" and select **"Open Anyway"**.
   - *macOS 14 or earlier:* right-click the application, then choose **Open** and **Open** again.
   - If macOS reports that the application "is damaged": open *Terminal* and run `xattr -dr com.apple.quarantine "/Applications/AudioLibro Libre.app"`.
4. The application opens in its own window. Start with the **2-minute tutorial**.

User data (downloaded voices, projects and audio) is stored in `~/Library/Application Support/AudioLibroLibre`. To uninstall, move the application to the Trash and, optionally, delete that folder. Projects are saved automatically: if the window is closed during generation, select **Resume** when you return.

### For maintainers: building the application

Building requires a Mac with Apple Silicon.

**Prerequisites** (one time):
- Xcode command-line tools: `xcode-select --install`.
- Homebrew (<https://brew.sh>), which the script uses to install `autoconf automake libtool pkg-config`, needed to compile espeak-ng.
- Python 3.10 to 3.13 for arm64 (`brew install python@3.12`).
- An internet connection and about 3 GB of free disk space. The first build takes roughly 20 to 30 minutes because it compiles ffmpeg and espeak-ng.

**Build:**
```bash
git clone https://github.com/datamauriciovaldez/jabote_books.git
cd jabote_books
./tools/mac/build_app.sh
```
Output is written to `dist/mac/`: the `.dmg`, its `.sha256`, `selftest.txt` and the `sources/` folder.

**Pinned and verified sources.** `packaging/source-hashes.txt` pins the SHA-256 of LAME 3.100, ffmpeg 6.1.1 and espeak-ng 1.52.0. These are **the same sources that were compiled and tested on Linux** (see the rehearsal below) and were checked against the signed Ubuntu `.dsc` files. If a download does not match, the script deletes it and stops.

**What the script does:**
1. Compiles **LAME** and a **minimal LGPL ffmpeg** (only AAC, MP3, FLAC, `loudnorm`, mp4 and concat; **no** GPL or nonfree components) and checks that the result does not depend on external libraries.
2. Compiles a static build of **espeak-ng** (GPL-3) together with its data folder.
3. Packages everything with **PyInstaller** and copies ffmpeg, espeak-ng, its data and the licenses into the `.app`.
4. Applies an **ad hoc signature** (free of charge); Apple Silicon does not execute binaries that carry no signature at all.
5. Runs the **self-test** of the packaged application and creates the `.dmg`.

#### Verifying the build (and what to report if it fails)
```bash
open "build/mac/dist/AudioLibro Libre.app"                                  # the window should open
"build/mac/dist/AudioLibro Libre.app/Contents/MacOS/AudioLibroLibre" --self-test
```
The self-test prints a report such as the following. Every line must show `OK`; "Ventana propia" (native window) may be a warning if pywebview is missing:
```
  [OK ] Recursos de la app: …
  [OK ] ffmpeg: ffmpeg version 6.1.1 · LGPL · …/Resources/bin/ffmpeg
  [OK ] ffmpeg: exportación real: FLAC normalizado, MP3 con portada y M4B con capítulos y portada generados
  [OK ] espeak-ng: …/Resources/bin/espeak-ng · «hola mundo» → ˈola mˈundo
RESULTADO: todo correcto
```
If anything fails, provide: the last ~40 lines of the script output, `build/mac/selftest.txt` and, for a PyInstaller error, `build/mac/pyinstaller.log`. That information is sufficient to diagnose the problem without access to the machine.

**Complete manual check (about 5 minutes):** open the application, select "Try with Don Quixote", choose the recommended voice (it is downloaded), play the sample, generate, export, **download the ZIP and the M4B** (confirming that downloads work inside the window), open the M4B with *Books* or *VLC* and inspect the chapters. Close the window in the middle of a generation, reopen the application and select **Resume**.

#### Rehearsal on Linux (verified)
`./tools/mac/rehearse_linux.sh` runs **the same scripts** with `AUDIOLIBRO_REHEARSAL=1` and compiles LAME, ffmpeg and espeak-ng from the pinned sources. Verified results: a self-contained **LGPL** ffmpeg providing `libmp3lame`, AAC, FLAC, `loudnorm`, mp4 and concat; a static espeak-ng that locates its data folder through `ESPEAK_DATA_PATH`; and, with both placed in the Linux PyInstaller bundle **and an empty PATH**, a passing self-test and the complete workflow (generate with Piper, export an M4B with two chapters and MP3 files with tags, at -19.3 LUFS). The rehearsal already found and fixed two defects in the scripts: an intermittent check caused by `grep -q` combined with `pipefail`, and the detection of `libtool`.

#### Not yet verified (requires a Mac)
| Item | Fallback if it fails |
|---|---|
| The native window (`pywebview`) opens the application and supports **downloads** and **file uploads** | The launcher opens the browser instead (`--browser`) |
| `espeak-ng` finds its data folder inside the `.app` (this works on Linux through `ESPEAK_DATA_PATH`) | Adjust the path in `app/desktop.py` |
| Minimum macOS version (`LSMinimumSystemVersion` = 13.0), which depends on the `onnxruntime` wheels | Adjust it in `packaging/audiolibro.spec` |
| Closing the window terminates the process and does not leave the application running in the Dock | See `app/desktop.py::run` |
| OCR for scanned PDFs: **not included** in this version (Tesseract) | A clear message is shown; it can be added later |

### Licenses and redistribution obligations

The `.dmg` **redistributes copyleft-licensed programs**: ffmpeg and LAME (LGPL) and espeak-ng (**GPL-3**). Consequently:
- ffmpeg is compiled without GPL or nonfree components, and all three programs are executed as **independent programs** and never linked.
- **Every release of the `.dmg` must also publish, on the same page, the `sources/` folder** (the exact tarballs of ffmpeg, LAME and espeak-ng, which the script places in `dist/mac/sources/`) and `ffmpeg-configure-flags.txt`. This is how the GPL and LGPL obligations are met.
- The licenses (`Contents/Resources/licenses/`) and `THIRD_PARTY_NOTICES.md` are included inside the application.
- **PyInstaller** (GPL-2 with a bootloader exception) is only a build tool. **pywebview** is BSD-3 and **PyObjC** is MIT.

For this installer only, this replaces the rule that no GPL program is redistributed (see `docs/DECISIONS.md`). The Docker and script-based installations still do not redistribute those programs.

### Publishing a macOS release
1. Build (`./tools/mac/build_app.sh`) and verify the self-test and the complete manual check.
2. On the GitHub release (created manually; see `docs/RELEASING.md`), attach the `.dmg`, its `.sha256` and **the entire contents of `dist/mac/sources/`**.
3. State in the description: "Unsigned application: on first launch it must be opened from System Settings > Privacy & Security."

---

<a name="español"></a>
## Español

Una aplicación nativa (`AudioLibro Libre.app`) que se arrastra a *Aplicaciones* y se abre con doble clic, **sin instalar Python, ffmpeg ni ningún otro software**. Está dirigida a **Apple Silicon** (M1, M2, M3, M4).

> **Estado: verificada parcialmente.** El proyecto se desarrolló en Linux, donde una aplicación de macOS no puede construirse ni ejecutarse. En Linux se han verificado el lanzador, la autoprueba, la receta de PyInstaller y el flujo de trabajo completo del binario empaquetado. **No se ha probado nada específico de macOS**: la compilación de ffmpeg y espeak-ng, la firma, la ventana nativa y el `.dmg`. La primera construcción en un Mac requerirá muy probablemente pequeños ajustes; para ello existen la autoprueba y el formato de informe descritos a continuación.

### Para usuarios

1. Descargue `AudioLibroLibre-X.Y.Z-arm64.dmg` desde la sección **Releases** del repositorio y ábralo.
2. Arrastre **AudioLibro Libre** a la carpeta **Aplicaciones**.
3. **En el primer inicio**, macOS indica que no puede comprobar que la aplicación esté libre de software malicioso. Es lo esperado: la aplicación no está firmada con un certificado de desarrollador de pago (99 USD al año). Para abrirla **una sola vez**:
   - *macOS 15 (Sequoia) o posterior:* abra la aplicación, seleccione «Hecho» en el aviso, vaya a **Ajustes del Sistema > Privacidad y seguridad**, desplácese hasta el mensaje sobre «AudioLibro Libre» y seleccione **«Abrir igualmente»**.
   - *macOS 14 o anterior:* haga clic derecho sobre la aplicación y elija **Abrir** y, de nuevo, **Abrir**.
   - Si macOS indica que la aplicación «está dañada»: abra *Terminal* y ejecute `xattr -dr com.apple.quarantine "/Applications/AudioLibro Libre.app"`.
4. La aplicación se abre en su propia ventana. Comience con el **tutorial de 2 minutos**.

Los datos del usuario (voces descargadas, proyectos y audio) se almacenan en `~/Library/Application Support/AudioLibroLibre`. Para desinstalar, mueva la aplicación a la Papelera y, opcionalmente, elimine esa carpeta. Los proyectos se guardan automáticamente: si se cierra la ventana durante una generación, seleccione **Reanudar** al volver.

### Para mantenedores: construcción de la aplicación

La construcción requiere un Mac con Apple Silicon.

**Requisitos previos** (una sola vez):
- Herramientas de línea de comandos de Xcode: `xcode-select --install`.
- Homebrew (<https://brew.sh>), que el script utiliza para instalar `autoconf automake libtool pkg-config`, necesarios para compilar espeak-ng.
- Python 3.10 a 3.13 para arm64 (`brew install python@3.12`).
- Conexión a internet y unos 3 GB de espacio libre. La primera construcción tarda aproximadamente entre 20 y 30 minutos porque compila ffmpeg y espeak-ng.

**Construcción:**
```bash
git clone https://github.com/datamauriciovaldez/jabote_books.git
cd jabote_books
./tools/mac/build_app.sh
```
El resultado se escribe en `dist/mac/`: el `.dmg`, su `.sha256`, `selftest.txt` y la carpeta `sources/`.

**Fuentes fijadas y verificadas.** `packaging/source-hashes.txt` fija el SHA-256 de LAME 3.100, ffmpeg 6.1.1 y espeak-ng 1.52.0. Son **las mismas fuentes que se compilaron y probaron en Linux** (véase el ensayo más abajo) y se contrastaron con los archivos `.dsc` firmados de Ubuntu. Si una descarga no coincide, el script la elimina y se detiene.

**Qué hace el script:**
1. Compila **LAME** y un **ffmpeg LGPL mínimo** (solo AAC, MP3, FLAC, `loudnorm`, mp4 y concat; **sin** componentes GPL ni *nonfree*) y comprueba que el resultado no depende de bibliotecas externas.
2. Compila una versión estática de **espeak-ng** (GPL-3) junto con su carpeta de datos.
3. Empaqueta todo con **PyInstaller** y copia ffmpeg, espeak-ng, sus datos y las licencias dentro de la `.app`.
4. Aplica una **firma «ad hoc»** (gratuita); Apple Silicon no ejecuta binarios que carezcan por completo de firma.
5. Ejecuta la **autoprueba** de la aplicación empaquetada y crea el `.dmg`.

#### Verificación de la construcción (y qué informar si falla)
```bash
open "build/mac/dist/AudioLibro Libre.app"                                  # debe abrirse la ventana
"build/mac/dist/AudioLibro Libre.app/Contents/MacOS/AudioLibroLibre" --self-test
```
La autoprueba imprime un informe como el siguiente. Todas las líneas deben mostrar `OK`; «Ventana propia» puede ser un aviso si falta pywebview:
```
  [OK ] Recursos de la app: …
  [OK ] ffmpeg: ffmpeg version 6.1.1 · LGPL · …/Resources/bin/ffmpeg
  [OK ] ffmpeg: exportación real: FLAC normalizado, MP3 con portada y M4B con capítulos y portada generados
  [OK ] espeak-ng: …/Resources/bin/espeak-ng · «hola mundo» → ˈola mˈundo
RESULTADO: todo correcto
```
Si algo falla, facilite: las últimas ~40 líneas de la salida del script, `build/mac/selftest.txt` y, en caso de error de PyInstaller, `build/mac/pyinstaller.log`. Esa información basta para diagnosticar el problema sin acceso a la máquina.

**Comprobación manual completa (unos 5 minutos):** abra la aplicación, seleccione «Probar con Don Quijote», elija la voz recomendada (se descarga), reproduzca la muestra, genere, exporte, **descargue el ZIP y el M4B** (comprobando que las descargas funcionan dentro de la ventana), abra el M4B con *Libros* o *VLC* e inspeccione los capítulos. Cierre la ventana a mitad de una generación, vuelva a abrir la aplicación y seleccione **Reanudar**.

#### Ensayo en Linux (verificado)
`./tools/mac/rehearse_linux.sh` ejecuta **los mismos scripts** con `AUDIOLIBRO_REHEARSAL=1` y compila LAME, ffmpeg y espeak-ng a partir de las fuentes fijadas. Resultados verificados: un ffmpeg **LGPL** autónomo con `libmp3lame`, AAC, FLAC, `loudnorm`, mp4 y concat; un espeak-ng estático que localiza su carpeta de datos mediante `ESPEAK_DATA_PATH`; y, con ambos colocados en el paquete de PyInstaller de Linux **y el PATH vacío**, una autoprueba correcta y el flujo de trabajo completo (generar con Piper, exportar un M4B con dos capítulos y MP3 con etiquetas, a −19,3 LUFS). El ensayo ya detectó y corrigió dos defectos de los scripts: una comprobación intermitente causada por `grep -q` combinado con `pipefail` y la detección de `libtool`.

#### Pendiente de verificar (requiere un Mac)
| Elemento | Alternativa si falla |
|---|---|
| La ventana nativa (`pywebview`) abre la aplicación y admite **descargas** y **subida de archivos** | El lanzador abre el navegador (`--browser`) |
| `espeak-ng` encuentra su carpeta de datos dentro de la `.app` (en Linux funciona mediante `ESPEAK_DATA_PATH`) | Ajustar la ruta en `app/desktop.py` |
| Versión mínima de macOS (`LSMinimumSystemVersion` = 13.0), que depende de las ruedas de `onnxruntime` | Ajustarla en `packaging/audiolibro.spec` |
| Que al cerrar la ventana termine el proceso y no quede la aplicación activa en el Dock | Véase `app/desktop.py::run` |
| OCR de PDF escaneados: **no incluido** en esta versión (Tesseract) | Se muestra un mensaje claro; puede añadirse después |

### Licencias y obligaciones de redistribución

El `.dmg` **redistribuye programas con licencia copyleft**: ffmpeg y LAME (LGPL) y espeak-ng (**GPL-3**). Por tanto:
- ffmpeg se compila sin componentes GPL ni *nonfree*, y los tres programas se ejecutan como **programas independientes** y nunca se enlazan.
- **Cada versión del `.dmg` debe publicar también, en la misma página, la carpeta `sources/`** (los tarballs exactos de ffmpeg, LAME y espeak-ng, que el script deja en `dist/mac/sources/`) y `ffmpeg-configure-flags.txt`. Así se cumplen las obligaciones de la GPL y la LGPL.
- Las licencias (`Contents/Resources/licenses/`) y `THIRD_PARTY_NOTICES.md` se incluyen dentro de la aplicación.
- **PyInstaller** (GPL-2 con excepción del *bootloader*) es solo una herramienta de construcción. **pywebview** es BSD-3 y **PyObjC** es MIT.

Solo para este instalador, esto sustituye la regla de no redistribuir ningún programa GPL (véase `docs/DECISIONS.md`). Las instalaciones con Docker y con scripts siguen sin redistribuir esos programas.

### Publicación de una versión para macOS
1. Construya (`./tools/mac/build_app.sh`) y verifique la autoprueba y la comprobación manual completa.
2. En la versión de GitHub (creada manualmente; véase `docs/RELEASING.md`), adjunte el `.dmg`, su `.sha256` y **todo el contenido de `dist/mac/sources/`**.
3. Indique en la descripción: «Aplicación sin firmar: en el primer inicio debe abrirse desde Ajustes del Sistema > Privacidad y seguridad».
