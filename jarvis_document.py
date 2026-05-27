#!/usr/bin/env python3
"""
JARVIS Document Processor - Advanced RAG
Parse PDFs, docs, and extract knowledge
"""

import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional


class DocumentProcessor:
    """Process documents for RAG"""

    SUPPORTED_FORMATS = [".txt", ".md", ".pdf", ".docx", ".html", ".csv", ".json"]

    def __init__(
        self, storage_dir: str = "/Users/nicholas/clawd/sovereign-temple-live/documents"
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Try to import libraries
        self.pypdf_available = False
        self.docx_available = False

        try:
            from pypdf import PdfReader

            self.pypdf_available = True
        except:
            pass

        try:
            import docx

            self.docx_available = True
        except:
            pass

    def extract_text(self, file_path: str) -> str:
        """Extract text from any supported file"""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".txt" or ext == ".md":
            return self._read_text(path)
        elif ext == ".pdf":
            return self._read_pdf(path)
        elif ext == ".docx":
            return self._read_docx(path)
        elif ext == ".html":
            return self._read_html(path)
        elif ext == ".csv":
            return self._read_csv(path)
        elif ext == ".json":
            return self._read_json(path)

        return f"Unsupported format: {ext}"

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except:
            return path.read_text()

    def _read_pdf(self, path: Path) -> str:
        if not self.pypdf_available:
            return "Install pypdf: pip install pypdf"

        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            return f"PDF read error: {e}"

    def _read_docx(self, path: Path) -> str:
        if not self.docx_available:
            return "Install python-docx: pip install python-docx"

        try:
            import docx

            doc = docx.Document(str(path))
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except Exception as e:
            return f"DOCX read error: {e}"

    def _read_html(self, path: Path) -> str:
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(path.read_text(), "html.parser")
            return soup.get_text(separator="\n")
        except:
            return path.read_text()

    def _read_csv(self, path: Path) -> str:
        try:
            import csv

            text = ""
            with open(path) as f:
                reader = csv.reader(f)
                for row in reader:
                    text += " | ".join(row) + "\n"
            return text
        except Exception as e:
            return f"CSV read error: {e}"

    def _read_json(self, path: Path) -> str:
        try:
            data = json.loads(path.read_text())
            return json.dumps(data, indent=2)
        except:
            return path.read_text()

    def chunk_text(
        self, text: str, chunk_size: int = 1000, overlap: int = 100
    ) -> List[str]:
        """Split text into chunks"""
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < text_len:
                for punct in [". ", "! ", "? ", "\n"]:
                    last_punct = chunk.rfind(punct)
                    if last_punct > chunk_size // 2:
                        end = start + last_punct + 1
                        chunk = text[start:end]
                        break

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    def process_document(self, file_path: str, metadata: Dict = None) -> Dict:
        """Process document and return chunks"""
        text = self.extract_text(file_path)

        if text.startswith("Error") or text.startswith("Install"):
            return {"error": text}

        chunks = self.chunk_text(text)

        return {
            "filename": Path(file_path).name,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "total_chars": len(text),
            "metadata": metadata or {},
        }


# Global processor
doc_processor = DocumentProcessor()


def process_document(file_path: str, metadata: Dict = None) -> Dict:
    return doc_processor.process_document(file_path, metadata)


def extract_text(file_path: str) -> str:
    return doc_processor.extract_text(file_path)


if __name__ == "__main__":
    print("Document Processor ready")
    print(f"  pypdf: {doc_processor.pypdf_available}")
    print(f"  docx: {doc_processor.docx_available}")
