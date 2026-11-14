"""Ringkas log buildozer menjadi satu error annotation GitHub.

Annotation dibatasi ~4 KB, sedangkan log buildozer penuh baris perintah clang
yang sangat panjang. Skrip ini hanya mengambil baris yang relevan (error,
traceback, perintah yang gagal) lalu memotong tiap baris agar muat.
"""

import os
import re

LOG = "buildozer.log"
LIMIT = 3800
KEYWORDS = re.compile(
    r"(error|Error|ERROR|Traceback|Exception|failed|FAILED|"
    r"STDERR|STDOUT|BUILD FAILED|Command failed|not found|No such file)"
)


def main() -> None:
    if not os.path.exists(LOG):
        print("::error title=Buildozer gagal::buildozer.log tidak ditemukan")
        return

    with open(LOG, errors="replace") as handle:
        lines = [line.rstrip() for line in handle]

    interesting = [line for line in lines if KEYWORDS.search(line)]
    picked = interesting[-12:] + lines[-6:]
    # buang baris perintah kompiler yang panjangnya > 400 karakter
    picked = [line for line in picked if len(line) <= 400]

    out = []
    for line in picked:
        out.append(line[:200])
    text = "\n".join(out)[-LIMIT:]
    escaped = text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print("::error title=Buildozer gagal::" + escaped)


if __name__ == "__main__":
    main()
