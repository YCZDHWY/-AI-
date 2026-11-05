"""Render a DOCX to per-page PNGs using local Word + Poppler for visual QA."""
import os
import shutil
import subprocess
import sys
import tempfile


def docx_to_pdf(docx_path, out_dir):
    pdf_path = os.path.join(out_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "to_pdf.ps1")
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
         "-File", script, "-DocxPath", os.path.abspath(docx_path), "-PdfPath", os.path.abspath(pdf_path)],
        check=True,
    )
    return pdf_path


def pdf_to_pngs(pdf_path, out_dir):
    exe = shutil.which("pdftoppm")
    if not exe:
        exe = r"C:\Users\20747\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe"
    prefix = os.path.join(out_dir, "page")
    subprocess.run([exe, "-r", "130", "-png", pdf_path, prefix], check=True)
    return sorted(p for p in os.listdir(out_dir) if p.startswith("page") and p.endswith(".png"))


def main():
    docx_path = sys.argv[1]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pdf = docx_to_pdf(docx_path, tmp)
        pages = pdf_to_pngs(pdf, out_dir)
    for p in pages:
        print(os.path.join(out_dir, p))


if __name__ == "__main__":
    main()
