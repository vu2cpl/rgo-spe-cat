RGO ONE -- Hamlib Backend
Joerg DJ4WD, 2026
=============================


DEUTSCH
=======

Inhalt dieses Archivs
---------------------

  rgo-one-hamlib.patch          Patch für einen frischen Hamlib-Quellbaum (Tag 4.7.1)
  hamlib-4.7.1/                 Geänderte Kern-Dateien (für manuelle Integration)
    configure.ac                 Build-System (RGO-Backend eingetragen)
    src/register.c               Backend-Registrierung
    include/hamlib/rig.h         API-Header (post_set_rts-Callback, delete_channel)
    src/rig.c                    PTT-Implementierung (post_set_rts-Aufruf)
    include/hamlib/riglist.h     Modell-IDs RGO ONE V6/V1-V5
  hamlib-4.7.1/rigs/rgo/       Quelldateien des Backends
    Makefile.am                  Build-Konfiguration
    rgo_one_v6.c                 Backend-Implementierung RGO ONE V6
    rgo_one_v1v5.c               Backend-Implementierung RGO ONE V1-V5
    README.de.md                 Dokumentation (Deutsch)
    README.en.md                 Dokumentation (Englisch)
  testscripte/
    test_rgo_one.py              Automatisiertes Test-Script
    run_rigctl.sh                Hilfs-Script für rigctl
    test_mw_debug.py             MW/MR-Untersuchung (Entwickler)
    set_rgo_on_defaults.py       Setzt den TRX auf einen definierten Zustand (sendet nie)
    test_rgo_channel.c           Direkter Backend-Test set/get/delete_channel (ohne rigctld)


Voraussetzungen (Build-Pakete)
-------------------------------

Zum Bauen wird ein vollstaendiger Autotools-Toolchain benoetigt:

  Debian/Ubuntu/Raspberry Pi OS:
    sudo apt install build-essential autoconf automake libtool pkg-config git

  Hinweis: Ein normaler Hamlib-Quellbaum baut standardmaessig ALLE Backends,
  nicht nur RGO ONE. Manche davon brauchen zusaetzliche Header, die fuer
  RGO ONE selbst nicht noetig sind (RGO ONE ist CDC-ACM/seriell, kein USB-Backend):
    sudo apt install libusb-1.0-0-dev libxml2-dev
  Fehlen diese, bricht "make" ggf. in einem anderen Backend ab
  (z.B. "fatal error: libusb.h: No such file or directory" in rigs/kit/).

  Falls schon einmal auf diesem Rechner gebaut wurde und seither ein
  System-/Distro-Upgrade stattfand (z.B. neue Debian-/Ubuntu-Version mit
  neuerem gcc): ein bereits vorhandenes Build-Verzeichnis NICHT wiederverwenden,
  sondern neu anlegen und frisch "configure" laufen lassen. Sonst koennen
  Linker-Fehler auftreten, weil im alten Build-Verzeichnis noch Pfade zur
  vorherigen (nicht mehr vorhandenen) Compiler-Version gecacht sind.


Variante 1: Patch anwenden (empfohlen)
---------------------------------------

Voraussetzung: Hamlib-Quellcode, Tag 4.7.1 ausgecheckt:

  git clone https://github.com/Hamlib/Hamlib.git
  cd Hamlib
  git checkout tags/4.7.1

Patch anwenden und bauen:

  patch -p1 < /pfad/zu/rgo-one-hamlib.patch
  autoreconf -fi
  mkdir ../hamlib-build && cd ../hamlib-build
  ../Hamlib/configure --prefix=/usr/local
  make -j$(nproc)
  sudo make install
  sudo ldconfig

Kontrolle:

  rigctl -l | grep -i rgo
  # Erwartete Ausgabe:
  # 43001  LZ2JR  RGO ONE V6     20261007.0  Stable  RIG_MODEL_RGOONE_V6
  # 43002  LZ2JR  RGO ONE V1-V5  20261007.0  Stable  RIG_MODEL_RGOONE_V1V5


Variante 2: Dateien manuell einfügen
--------------------------------------

Falls der Patch nicht sauber angewendet werden kann (z.B. bei einer anderen
Hamlib-Version oder unter Windows/MinGW ohne patch(1)), können die Quelldateien
aus diesem Archiv direkt in den Hamlib-Quellbaum kopiert werden:

  1. Verzeichnis rigs/rgo/ in den Hamlib-Quellbaum kopieren
  2. configure.ac             -> <hamlib>/configure.ac             (überschreiben)
  3. src/register.c           -> <hamlib>/src/register.c           (überschreiben)
  4. include/hamlib/rig.h     -> <hamlib>/include/hamlib/rig.h     (überschreiben)
  5. src/rig.c                -> <hamlib>/src/rig.c                (überschreiben)
  6. include/hamlib/riglist.h -> <hamlib>/include/hamlib/riglist.h (überschreiben)
  7. autoreconf -fi && ./configure && make

Hinweis: Schritte 2-6 ersetzen die originalen Hamlib-4.7.1-Dateien durch die
gepatchten Versionen. Bei einer anderen Hamlib-Version bitte den Patch manuell
prüfen (rgo-one-hamlib.patch).

Für Details siehe README.de.md im rigs/rgo/-Verzeichnis.


Testen
------

Das Test-Script setzt einen laufenden rigctld voraus oder startet ihn selbst:

  python3 testscripte/test_rgo_one.py --port 4532

Der Standardlauf (ohne Optionen) prueft nur die "normalen" CAT-Funktionen
ueber die Hamlib-API. Folgende Kategorien sind bewusst opt-in:

Optionen:
  --tune           Antennentuner-Test einschliessen (Sender aktiv!)
  --ptt            PTT-Test einschliessen (Sender aktiv!)
  --test-mem       MR/MW-Speicherkanal-Schreibtest einschliessen (standardmaessig
                    aus: kann den TRX im Memory-Modus haengen lassen, siehe
                    README.de.md im rigs/rgo/-Verzeichnis)
  --test-if-frame  Raw-CAT/IF-Frame-Test einschliessen (AI/FS/PB, standardmaessig
                    aus: keine Hamlib-API-Entsprechung, nur fuer Entwickler)
  --test-all-modes AM/FM/RTTY-Modustest einschliessen (standardmaessig aus:
                    laut Nutzerhandbuch in der 1.x-Firmware-Linie "not active"
                    und am Bedienpanel nicht waehlbar -- Fehlschlaege sind auf
                    solcher Hardware zu erwarten, kein Backend-Bug)

Siehe README.de.md für alle Optionen und das erwartete Testergebnis.


=============================


ENGLISH
=======

Contents of this archive
-------------------------

  rgo-one-hamlib.patch          Patch for a fresh Hamlib source tree (tag 4.7.1)
  hamlib-4.7.1/                 Modified core files (for manual integration)
    configure.ac                 Build system (RGO backend registered)
    src/register.c               Backend registration
    include/hamlib/rig.h         API header (post_set_rts callback, delete_channel)
    src/rig.c                    PTT implementation (post_set_rts call)
    include/hamlib/riglist.h     Model IDs RGO ONE V6/V1-V5
  hamlib-4.7.1/rigs/rgo/       Backend source files
    Makefile.am                  Build configuration
    rgo_one_v6.c                 Backend implementation RGO ONE V6
    rgo_one_v1v5.c               Backend implementation RGO ONE V1-V5
    README.de.md                 Documentation (German)
    README.en.md                 Documentation (English)
  testscripte/
    test_rgo_one.py              Automated test script
    run_rigctl.sh                Helper script for rigctl
    test_mw_debug.py             MW/MR investigation (developers)
    set_rgo_on_defaults.py       Puts the rig into a defined state (never transmits)
    test_rgo_channel.c           Direct backend test set/get/delete_channel (no rigctld)


Prerequisites (build packages)
-------------------------------

Building requires a full Autotools toolchain:

  Debian/Ubuntu/Raspberry Pi OS:
    sudo apt install build-essential autoconf automake libtool pkg-config git

  Note: A stock Hamlib source tree builds ALL backends by default, not just
  RGO ONE. Some of them need extra headers that RGO ONE itself does not need
  (RGO ONE is CDC-ACM/serial, not a USB backend):
    sudo apt install libusb-1.0-0-dev libxml2-dev
  Without these, "make" may fail in an unrelated backend
  (e.g. "fatal error: libusb.h: No such file or directory" in rigs/kit/).

  If you already built on this machine before and the system/distro has been
  upgraded since (e.g. a newer Debian/Ubuntu release with a newer gcc):
  do NOT reuse an existing build directory -- create a fresh one and run
  "configure" again. Otherwise you may hit linker errors because the old
  build directory still has cached paths pointing to the previous
  (no longer installed) compiler version.


Option 1: Apply the patch (recommended)
-----------------------------------------

Prerequisite: Hamlib source code, tag 4.7.1 checked out:

  git clone https://github.com/Hamlib/Hamlib.git
  cd Hamlib
  git checkout tags/4.7.1

Apply patch and build:

  patch -p1 < /path/to/rgo-one-hamlib.patch
  autoreconf -fi
  mkdir ../hamlib-build && cd ../hamlib-build
  ../Hamlib/configure --prefix=/usr/local
  make -j$(nproc)
  sudo make install
  sudo ldconfig

Verify:

  rigctl -l | grep -i rgo
  # Expected output:
  # 43001  LZ2JR  RGO ONE V6     20261007.0  Stable  RIG_MODEL_RGOONE_V6
  # 43002  LZ2JR  RGO ONE V1-V5  20261007.0  Stable  RIG_MODEL_RGOONE_V1V5


Option 2: Add files manually
------------------------------

If the patch does not apply cleanly (e.g. against a different Hamlib version,
or on Windows/MinGW without patch(1)), copy the files from this archive directly
into the Hamlib source tree:

  1. Copy the rigs/rgo/ directory into the Hamlib source tree
  2. configure.ac             -> <hamlib>/configure.ac             (overwrite)
  3. src/register.c           -> <hamlib>/src/register.c           (overwrite)
  4. include/hamlib/rig.h     -> <hamlib>/include/hamlib/rig.h     (overwrite)
  5. src/rig.c                -> <hamlib>/src/rig.c                (overwrite)
  6. include/hamlib/riglist.h -> <hamlib>/include/hamlib/riglist.h (overwrite)
  7. autoreconf -fi && ./configure && make

Note: Steps 2-6 replace the original Hamlib 4.7.1 files with the patched versions.
For a different Hamlib version, please review the patch manually (rgo-one-hamlib.patch).

See README.en.md in the rigs/rgo/ directory for details.


Testing
-------

The test script requires a running rigctld or will start one automatically:

  python3 testscripte/test_rgo_one.py --port 4532

The default run (no options) only tests the "normal" CAT functions via the
Hamlib API. The following categories are opt-in on purpose:

Options:
  --tune           include antenna tuner test (transmitter active!)
  --ptt            include PTT test (transmitter active!)
  --test-mem       include the MR/MW memory channel write test (disabled by
                     default: can leave the rig stuck in memory mode, see
                     README.en.md in the rigs/rgo/ directory)
  --test-if-frame  include the raw CAT / IF-frame test (AI/FS/PB, disabled by
                     default: no Hamlib API equivalent, developer use only)
  --test-all-modes include the AM/FM/RTTY mode test (disabled by default: the
                     user manual states these are "not active" in the 1.x
                     firmware line and they are not selectable on the front
                     panel -- failures are expected on such hardware, not a
                     backend bug)

See README.en.md for all options and the expected test result.
