import os
import json
import hashlib
from sysagent.config import MANIFEST_PATH, MAN_SECTIONS, KERNEL_DOCS_PATH
from sysagent.rag.extractor import (
    get_man_pages_in_section, 
    extract_man_text,
    get_rst_files,
    extract_rst_text
)
from sysagent.rag.chunker import chunk_text
from sysagent.rag.embedder import get_embeddings
from sysagent.rag.store import upsert_chunks

def get_text_md5(text: str) -> str:
    """Computes the MD5 hash of a given string."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def load_manifest() -> dict[str, str]:
    """Loads the ingestion manifest from disk, returning an empty dict if missing."""
    if not MANIFEST_PATH.exists():
        return {}
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_manifest(manifest: dict[str, str]) -> None:
    """Saves the ingestion manifest safely to disk."""
    os.makedirs(MANIFEST_PATH.parent, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4)

def ingest_all():
    """
    Main orchestration loop. Iterates through configured manual sections,
    extracts pages, checks hashes, builds chunks, requests embeddings, 
    and saves to vector DB.
    """
    print(f"Starting RAG Ingestion Pipeline...")
    
    manifest = load_manifest()
    total_processed = 0
    total_skipped = 0
    total_errors = 0

    for section in MAN_SECTIONS:
        source_name = f"man{section}"
        try:
            pages = get_man_pages_in_section(section)
        except Exception as e:
            print(f"Failed to scan section {section}: {e}")
            continue

        print(f"Found {len(pages)} pages in section {source_name}")

        for topic in pages:
            # We track keys using the generic "source/topic" format (e.g. "man1/ls")
            manifest_key = f"{source_name}/{topic}"
            
            try:
                # 1. Extraction
                text = extract_man_text(topic, section)
                if not text or not text.strip():
                    total_errors += 1
                    continue
                    
                # 2. Hash Check
                # Idempotency lock - do not incur OpenAI costs if it's already ingested
                md5_hash = get_text_md5(text)
                if manifest.get(manifest_key) == md5_hash:
                    total_skipped += 1
                    continue
                
                print(f"Ingesting: {manifest_key}...")
                
                # 3. Chunking
                chunks = chunk_text(text)
                if not chunks:
                    continue
                
                # 4. Embedding
                embeddings = get_embeddings(chunks)
                
                # 5. Storing
                upsert_chunks(
                    source=source_name,
                    topic=topic,
                    chunks=chunks,
                    embeddings=embeddings
                )
                
                # Save the new hash to protect from future redundant runs
                manifest[manifest_key] = md5_hash
                total_processed += 1
                
                # Optimistically save per-item in case of a crash or rate limit mid-loop
                save_manifest(manifest)

            except Exception as e:
                print(f"Error processing {manifest_key}: {e}")
                total_errors += 1
      
    # --- Kernel Documentation Ingestion Pass ---
    if not KERNEL_DOCS_PATH or not KERNEL_DOCS_PATH.exists():
        print("\n[WARNING] Kernel Documentation not found. Skipping kernel ingestion phase.")
        print("To enable deep kernel diagnostics, you must download the raw .rst source files.")
        print("You can do this safely without downloading the whole kernel by running:")
        print("  git clone --depth 1 --filter=blob:none --sparse https://github.com/torvalds/linux.git kernel-source")
        print("  cd kernel-source && git sparse-checkout set Documentation")
        print("Then, set KERNEL_DOCS_PATH=/absolute/path/to/kernel-source/Documentation in your .env file.")
    else:
        print(f"\nScanning Kernel Documentation at {KERNEL_DOCS_PATH}")
        rst_files = get_rst_files(KERNEL_DOCS_PATH)
        print(f"Found {len(rst_files)} .rst files.")
        
        for filepath in rst_files:
            # Create a unique, readable key like "kernel/admin-guide/mm/concepts"
            try:
                rel_path = filepath.relative_to(KERNEL_DOCS_PATH)
                topic = str(rel_path.with_suffix(''))
            except ValueError:
                topic = filepath.stem
                
            manifest_key = f"kernel/{topic}"
            
            try:
                text = extract_rst_text(filepath)
                if not text or not text.strip():
                    continue
                    
                md5_hash = get_text_md5(text)
                if manifest.get(manifest_key) == md5_hash:
                    total_skipped += 1
                    continue
                
                print(f"Ingesting: {manifest_key}...")
                
                chunks = chunk_text(text)
                if not chunks:
                    continue
                
                embeddings = get_embeddings(chunks)
                
                upsert_chunks(
                    source="kernel",
                    topic=topic,
                    chunks=chunks,
                    embeddings=embeddings
                )
                
                manifest[manifest_key] = md5_hash
                total_processed += 1
                save_manifest(manifest)
                
            except Exception as e:
                print(f"Error processing {manifest_key}: {e}")
                total_errors += 1
    
    print("\n[Ingestion Complete]")
    print(f"Processed / Updated : {total_processed}")
    print(f"Skipped (unchanged) : {total_skipped}")
    print(f"Errors encountered  : {total_errors}")

if __name__ == "__main__":
    ingest_all()
