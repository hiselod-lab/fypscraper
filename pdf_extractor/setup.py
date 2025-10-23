from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pdf-extractor",
    version="1.0.0",
    description="Layout-preserving PDF extraction to structured JSON",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="PDF Extractor Team",
    url="https://github.com/hiselod-lab/pdf_extractor",
    packages=find_packages(),
    install_requires=[
        "PyMuPDF>=1.23.0",
        "pdfplumber>=0.10.0",
        "pytesseract>=0.3.10",
        "Pillow>=9.0.0",
        "langdetect>=1.0.9",
    ],
    entry_points={
        "console_scripts": [
            "pdf-extractor=pdf_extractor.__main__:main",
        ],
    },
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Text Processing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
