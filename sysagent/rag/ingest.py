import os
import json
import hashlib
from sysagent.config import MANIFEST_PATH, MAN_SECTIONS
from sysagent.rag.extractor import get_man_pages_in_section, extract_man_text
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
    
    print("\n[Ingestion Complete]")
    print(f"Processed / Updated : {total_processed}")
    print(f"Skipped (unchanged) : {total_skipped}")
    print(f"Errors encountered  : {total_errors}")

if __name__ == "__main__":
    ingest_all()
