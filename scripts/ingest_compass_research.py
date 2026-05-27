#!/usr/bin/env python3
"""
Ingest all Compass research artifacts into SOV3 memory.
Scans /Users/nicholas/Downloads/compass_artifact_*.md, extracts first 500 chars
of each as a research memory episode.
"""
import glob, json, time, requests, os, re

SOV3_URL = os.environ.get("SOV3_URL", "http://localhost:3101")

def record_memory(content, tags):
    try:
        r = requests.post(f"{SOV3_URL}/mcp", json={
            "jsonrpc": "2.0", "id": int(time.time() * 1000),
            "method": "tools/call",
            "params": {"name": "record_memory", "arguments": {
                "content": content[:800],
                "source_agent": "compass_ingester",
                "memory_type": "insight",
                "tags": ["compass", "research"] + tags,
                "care_weight": 0.5
            }}
        }, timeout=10)
        return r.status_code == 200
    except:
        return False

def extract_title(text):
    """Extract first heading from markdown."""
    match = re.search(r'^#\s+(.+)', text, re.MULTILINE)
    return match.group(1).strip() if match else "Untitled research"

def main():
    files = sorted(glob.glob("/Users/nicholas/Downloads/compass_artifact_*.md"))
    print(f"Found {len(files)} Compass research files")

    ingested = 0
    skipped = 0

    for f in files:
        try:
            content = open(f).read()
            title = extract_title(content)
            # Extract first meaningful paragraph (skip metadata)
            lines = [l.strip() for l in content.split('\n') if l.strip() and not l.startswith('#') and len(l.strip()) > 30]
            summary = ' '.join(lines[:3])[:500] if lines else content[:500]

            memory_content = f"Compass Research: {title}. {summary}"

            # Tag based on content
            tags = []
            lower = content.lower()[:2000]
            if 'quantum' in lower: tags.append('quantum')
            if 'voice' in lower or 'speech' in lower: tags.append('voice')
            if 'robot' in lower or 'kinect' in lower: tags.append('robotics')
            if 'meok' in lower: tags.append('meok')
            if 'sovereign' in lower or 'sov3' in lower: tags.append('sovereign')
            if 'jarvis' in lower: tags.append('jarvis')
            if 'funding' in lower or 'innovate' in lower: tags.append('funding')
            if 'security' in lower or 'threat' in lower: tags.append('security')

            if record_memory(memory_content, tags):
                ingested += 1
                print(f"  ✅ {ingested}/{len(files)} — {title[:60]}")
            else:
                skipped += 1
                print(f"  ❌ Failed: {title[:60]}")

            time.sleep(0.2)  # Rate limit

        except Exception as e:
            skipped += 1
            print(f"  ❌ Error: {e}")

    print(f"\nDone: {ingested} ingested, {skipped} skipped out of {len(files)} files")

if __name__ == "__main__":
    main()
