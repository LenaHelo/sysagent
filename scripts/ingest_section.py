import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sysagent.config import KERNEL_DOCS_PATH
from sysagent.rag.extractor import get_rst_files, extract_rst_text
from sysagent.rag.chunker import chunk_text
from sysagent.rag.embedder import get_embeddings
from sysagent.rag.store import upsert_chunks
from sysagent.rag.ingest import get_text_md5, load_manifest, save_manifest

def ingest_section(section_name: str):
    target_dir = KERNEL_DOCS_PATH / section_name
    
    if not target_dir.exists() or not target_dir.is_dir():
        print(f"Error: Directory {target_dir} not found.")
        print(f"Please make sure it exists inside {KERNEL_DOCS_PATH}")
        return
        
    print(f"Scanning section: {target_dir}")
    rst_files = get_rst_files(target_dir)
    print(f"Found {len(rst_files)} files.")
    
    manifest = load_manifest()
    
    for filepath in rst_files:
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
                print(f"Skipping {manifest_key} (unchanged)")
                continue
                
            print(f"Ingesting: {manifest_key}...")
            chunks = chunk_text(text)
            if not chunks: 
                continue
            
            embeddings = get_embeddings(chunks)
            upsert_chunks(source="kernel", topic=topic, chunks=chunks, embeddings=embeddings)
            
            manifest[manifest_key] = md5_hash
            save_manifest(manifest)
            
        except Exception as e:
            print(f"Error on {manifest_key}: {e}")
            
    print("\nSection ingestion complete!")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest_section.py <section_folder>")
        print("Example: python scripts/ingest_section.py admin-guide")
        sys.exit(1)
        
    ingest_section(sys.argv[1])
