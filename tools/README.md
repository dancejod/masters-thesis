# tools

External command-line tools.

## ExifTool (Windows package)

`exiftool.exe` together with `exiftool_files/` is the Windows ExifTool package assembled by Oliver Betz. It is used by the calibration notebooks to copy image metadata (XMP/GPS tags) onto the processed thermal frames so they remain georeferenced for mosaicking. The package bundles three components, each under its own license:

- **ExifTool** by Phil Harvey: <https://exiftool.org/> free software, released under the same terms as Perl itself (the GNU General Public License or the Artistic License).
- **Strawberry Perl**: <https://strawberryperl.com/> under the Perl licensing terms (Artistic License / GPL).
- **Tiny launcher** by Oliver Betz: <https://oliverbetz.de/pages/Artikel/ExifTool-for-Windows> released under the CC0 1.0 public domain dedication.

The files are redistributed unmodified. See `exiftool_files/readme_windows.txt` for the packager's note. No warranty is provided for the bundled package.
