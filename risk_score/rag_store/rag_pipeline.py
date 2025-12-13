"""
rag_pipeline.py

Extended RAG ingestion pipeline for SOP PDFs + project outputs (JSON datasets).

Folder layout expected:
rag_store/
    sop_pdfs/           # PDFs
    extracted_text/     # created per-page text JSON
    page_images/        # images for flowcharts
    embeddings/         # FAISS index & metadata
    project_outputs/    # JSON output folders: eda, op_efficiency, risk_score

Outputs:
- rag_store/embeddings/faiss_index.index
- rag_store/embeddings/metadata.json
"""

import os
import json
import pdfplumber
from pathlib import Path
from tqdm import tqdm
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pandas as pd

# ========== CONFIG ==========
BASE_DIR = Path(r"C:\Users\SAHARA\OneDrive\Desktop\uni\gemma\risk score\rag_store")
PDF_DIR = BASE_DIR / "sop_pdfs"
TEXT_DIR = BASE_DIR / "extracted_text"
PAGE_IMG_DIR = BASE_DIR / "page_images"
EMBED_DIR = BASE_DIR / "embeddings"
OUTPUT_DIRS = [
    BASE_DIR.parent / "eda" / "outputs",
    BASE_DIR.parent / "op_efficiency" / "outputs",
    BASE_DIR.parent / "risk_score" / "outputs"
]

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 400
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
BATCH_SIZE = 64

FAISS_INDEX_PATH = EMBED_DIR / "faiss_index.index"
METADATA_PATH = EMBED_DIR / "metadata.json"

# ============================

def ensure_dirs():
    for d in [PDF_DIR, TEXT_DIR, PAGE_IMG_DIR, EMBED_DIR]:
        d.mkdir(parents=True, exist_ok=True)

# ---------------- PDF Extraction ----------------
def extract_text_and_images_from_pdfs():
    docs = []
    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        doc_id = pdf_path.stem
        pages = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                    image_path = None
                    if len(text.strip()) < 150:
                        img_save_path = PAGE_IMG_DIR / f"{doc_id}_page_{i}.png"
                        try:
                            pil_image = page.to_image(resolution=150).original
                            pil_image.save(img_save_path)
                            image_path = str(img_save_path)
                        except Exception:
                            pass
                    pages.append({"page_num": i, "text": text, "image_path": image_path})
        except Exception as e:
            print(f"[WARN] Failed to open {pdf_path}: {e}")
            continue

        doc_json_path = TEXT_DIR / f"{doc_id}.json"
        with open(doc_json_path, "w", encoding="utf-8") as fh:
            json.dump({"doc_id": doc_id, "file_path": str(pdf_path), "pages": pages}, fh, ensure_ascii=False, indent=2)

        docs.append({"doc_id": doc_id, "file_path": str(pdf_path), "pages": pages})
    return docs

# ---------------- JSON Output Summaries ----------------
def summarize_json_dataset(json_path):
    try:
        df = pd.read_json(json_path)
    except Exception:
        return []

    summary_texts = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            top = df[col].nlargest(10).tolist()
            bottom = df[col].nsmallest(10).tolist()
            summary_texts.append(f"[NUMERIC] {col} - Top10: {top}, Bottom10: {bottom}")
        else:
            uniques = df[col].nunique()
            top_values = df[col].value_counts().head(10).to_dict()
            summary_texts.append(f"[CATEGORICAL] {col} - Unique count: {uniques}, Top10: {top_values}")
    # join all summaries as one text block
    return ["\n".join(summary_texts)]

def extract_text_from_json_outputs():
    chunks = []
    for folder in OUTPUT_DIRS:
        if not folder.exists():
            continue
        for json_file in folder.glob("*.json"):
            dataset_chunks = summarize_json_dataset(json_file)
            for i, chunk in enumerate(dataset_chunks):
                chunks.append({
                    "doc_id": json_file.stem,
                    "chunk_id": f"{json_file.stem}_c{i}",
                    "text": chunk,
                    "source": str(json_file)
                })
    return chunks

# ---------------- Chunking ----------------
def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        start = end - overlap if end - overlap > start else end
        if start >= len(text):
            break
    return chunks

def build_chunks_from_pdfs(docs):
    chunks = []
    for doc in docs:
        doc_id = doc["doc_id"]
        for page in doc["pages"]:
            text = page["text"] or ""
            page_chunks = chunk_text(text)
            for i, chunk in enumerate(page_chunks):
                chunks.append({
                    "doc_id": doc_id,
                    "chunk_id": f"{doc_id}_p{page['page_num']}_c{i}",
                    "text": chunk,
                    "image_path": page.get("image_path")
                })
    return chunks

# ---------------- Embedding ----------------
def compute_embeddings(chunks):
    model = SentenceTransformer(EMBED_MODEL_NAME)
    all_vectors = []
    for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Embedding batches"):
        batch_texts = [c["text"] for c in chunks[i:i+BATCH_SIZE]]
        emb = model.encode(batch_texts, convert_to_numpy=True, show_progress_bar=False)
        all_vectors.append(emb)
    if all_vectors:
        vectors = np.vstack(all_vectors)
    else:
        vectors = np.zeros((0, model.get_sentence_embedding_dimension()), dtype="float32")
    return vectors, model.get_sentence_embedding_dimension()

def build_faiss_index(vectors, dim):
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)
    return index

def save_faiss_and_metadata(index, chunks):
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"[OK] Saved FAISS index and metadata.")

# ---------------- Main ----------------
def main():
    print("=== RAG pipeline starting ===")
    ensure_dirs()

    print("Extracting PDFs...")
    pdf_docs = extract_text_and_images_from_pdfs()
    pdf_chunks = build_chunks_from_pdfs(pdf_docs)
    print(f"  PDF chunks: {len(pdf_chunks)}")

    print("Extracting JSON outputs...")
    json_chunks = extract_text_from_json_outputs()
    print(f"  JSON summary chunks: {len(json_chunks)}")

    all_chunks = pdf_chunks + json_chunks

    if not all_chunks:
        print("[WARN] No chunks created. Exiting.")
        return

    print("Computing embeddings...")
    vectors, dim = compute_embeddings(all_chunks)
    print(f"  Vectors shape: {vectors.shape}, dim={dim}")

    print("Building FAISS index...")
    index = build_faiss_index(vectors, dim)

    print("Saving FAISS index and metadata...")
    save_faiss_and_metadata(index, all_chunks)
    print("=== RAG pipeline complete ===")

if __name__ == "__main__":
    main()
