Hamlib with RGO One Patch
=========================
Build date: 20261009
Backend version: 20261007.0

IMPORTANT: This is a 64-bit build. It requires a 64-bit installation of
WSJT-X or JTDX. Do not use with 32-bit versions.

This build contains a patch for the RGO One Transceiver with the
following improvements over the standard Hamlib release:

  - Native RGO One V6 backend (model 43001, manufacturer "LZ2JR")
  - Native RGO One V1-V5 backend (model 43002, manufacturer "LZ2JR")
  - PTT via CAT works correctly (TX0/TX2 commands)
  - RTS PTT fix for Windows (V6 only, usbser.sys workaround)

REQUIREMENTS
------------
  - Windows 10 or 11, 64-bit
  - WSJT-X or JTDX installed (64-bit version)
  - RGO One connected via USB


INSTALLATION
------------

1. Create a backup of the existing DLL:

   Navigate to: C:\Program Files\WSJT-X\bin
   (For JTDX the path is: C:\Program Files\JTDX\bin)

   Depending on your installed WSJT-X / JTDX version, rename:
     libhamlib-4.dll  ->  libhamlib-4.dll.original
   or
     libhamlib-5.dll  ->  libhamlib-5.dll.original

   Both files are included in this archive; copy the one matching
   your existing file, or copy both.

2. Copy all *.dll files from this archive to:
     C:\Program Files\WSJT-X\bin

   Confirm overwriting any existing files when prompted.

3. In WSJT-X Settings > Radio:
   - RGO One V6:    Rig "RGO ONE V6"    (model 43001, manufacturer "LZ2JR")
   - RGO One V1-V5: Rig "RGO ONE V1-V5" (model 43002, manufacturer "LZ2JR")
   - PTT Method:    CAT  (or RTS)
   - Serial Port:   your COM port
   - Baud Rate:     115200

   See screenshots RGO-One-V6-WSJT-X.png and RGO-One-V1-V5-WSJT-X.png
   for the correct settings.

4. Click "Test CAT" to verify the connection.


UNINSTALLING / REVERTING
-------------------------

Rename the backup file from step 1 back to the original name:
  libhamlib-4.dll.original  ->  libhamlib-4.dll
or
  libhamlib-5.dll.original  ->  libhamlib-5.dll


NOTES
-----
  - libhamlib-4.dll and libhamlib-5.dll are identical builds included
    for compatibility with different WSJT-X / JTDX versions.
  - libwinpthread-1.dll must be present alongside libhamlib-4/5.dll.


73 de Joerg DJ4WD
