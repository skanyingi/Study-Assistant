# PDF text extraction, cleaning, chunking, and empty/scanned-PDF detection.
import re

from pypdf import PdfReader

# Below this many characters of cleaned text, we assume the PDF is empty or
# scanned (image-only, no extractable text layer).
MIN_TEXT_CHARS = 50

# Default chunk size in characters. Keeps each chunk comfortably within the
# Gemini free-tier context window while leaving room for prompt + response.
DEFAULT_CHUNK_CHARS = 8000


def extract_text(pdf_file) -> str:
    """Extract raw text from every page of a PDF.

    pdf_file can be a file path (str) or a file-like object, e.g. the object
    Streamlit's st.file_uploader gives us.
    """
    reader = PdfReader(pdf_file)
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages_text)


def clean_text(text: str) -> str:
    """Normalize whitespace so the text is readable and consistent."""
    # Strip private-use-area characters (U+E000-U+F8FF): these are usually
    # leftover bullet/icon glyphs from custom PDF fonts, not real text.
    text = re.sub(r"[\ue000-\uf8ff]", "", text)
    # Collapse runs of spaces/tabs into one space.
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse 3+ newlines down to a double newline (paragraph break).
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_empty_or_scanned(text: str) -> bool:
    """Heuristic check: very little extractable text usually means the PDF
    is empty or made of scanned images with no text layer."""
    return len(text) < MIN_TEXT_CHARS


def chunk_text(text: str, max_chars: int = DEFAULT_CHUNK_CHARS) -> list[str]:
    """Split text into chunks no longer than max_chars, breaking on
    paragraph boundaries where possible so we don't cut mid-sentence."""
    if len(text) <= max_chars:
        return [text] if text else []

    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        # +2 accounts for the "\n\n" we'd rejoin with.
        if current and len(current) + len(para) + 2 > max_chars:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para

        # A single paragraph longer than max_chars on its own: hard-split it.
        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            current = current[max_chars:]

    if current:
        chunks.append(current)

    return chunks


if __name__ == "__main__":
    # Quick manual test against the sample lecture PDF in the project root.
    sample_pdf = "Lectures 5 &6- Topics Cloud Storage, Cloud Databases and Security.pdf"

    raw = extract_text(sample_pdf)
    cleaned = clean_text(raw)

    print(f"Raw extracted characters: {len(raw)}")
    print(f"Cleaned characters: {len(cleaned)}")
    print(f"Empty or scanned?: {is_empty_or_scanned(cleaned)}")

    chunks = chunk_text(cleaned)
    print(f"Number of chunks: {len(chunks)}")
    print("--- Preview of first chunk (first 500 chars) ---")
    preview = chunks[0][:500] if chunks else "(no chunks)"
    print(preview.encode("ascii", errors="replace").decode("ascii"))
