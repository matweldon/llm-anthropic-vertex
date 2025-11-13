
"""
Decompress gzip-compressed body strings in the YAML cassette files.

**Usage examples:**

```bash
# Single file
python script.py file.yaml

# All YAML files in current directory
python script.py '*.yaml'

# All YAML files recursively
python script.py '**/*.yaml'

# Multiple patterns
python script.py 'tests/**/*.yaml' 'fixtures/*.yaml'

# Specific directory
python script.py 'cassettes/*.yaml'
```

**Features:**
- ✅ Finds gzip-compressed body strings (marked with `!!binary`)
- ✅ Decompresses them and replaces with plain text
- ✅ Shows a unified diff for each file
- ✅ Interactive prompt (y/n/q) for each file
- ✅ Processes multiple files in one command
- ✅ Preserves YAML structure

**How it works:**
1. Loads each YAML file
2. Finds `response.body.string` fields with binary gzip data
3. Decompresses using gzip + base64 decoding
4. Shows a diff of the changes
5. Asks you to confirm (y/n/q) before saving
"""

import sys
import gzip
import base64
import glob
from pathlib import Path
import yaml


def decompress_gzip_string(compressed_data):
    """Decompress gzip-compressed data (base64 encoded binary)."""
    try:
        # Decompress gzip
        decompressed = gzip.decompress(compressed_data).decode('utf-8')
        return decompressed
    except Exception as e:
        print(f"Error decompressing: {e}")
        return None


def process_yaml_file(file_path):
    """Process a single YAML file and decompress gzip bodies."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Load YAML
    try:
        data = yaml.safe_load(content)
    except Exception as e:
        print(f"Error parsing YAML: {e}")
        return False
    
    modified = False
    
    # Process interactions
    if isinstance(data, dict) and 'interactions' in data:
        for interaction in data['interactions']:
            if 'response' in interaction and 'body' in interaction['response']:
                body = interaction['response']['body']
                
                # Check if this is gzip-compressed binary
                if isinstance(body, dict) and 'string' in body:
                    string_val = body['string']
                    print(string_val[:10])
                    
                    # Check if it looks like base64 binary (!!binary marker)
                    if isinstance(string_val, bytes): # and string_val.startswith('!!'):

                        # Try to decompress
                        decompressed = decompress_gzip_string(string_val.strip())
                        if decompressed:
                            body['string'] = decompressed
                            interaction['response']['headers'].pop('Content-Encoding') # Otherwise the receiver will try to decompress
                            modified = True
                            print(f"✓ Decompressed response body in {file_path}")
    
    if not modified:
        print(f"No gzip bodies found in {file_path}")
        return False
    
    # Generate new YAML
    new_content = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    # Show diff
    print(f"\n{'='*80}")
    print(f"File: {file_path}")
    print(f"{'='*80}\n")
    
    import difflib
    diff = difflib.unified_diff(
        original_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"{file_path} (original)",
        tofile=f"{file_path} (decompressed)",
        lineterm=''
    )
    
    diff_text = ''.join(diff)
    print(diff_text)
    
    # Ask user
    while True:
        response = input("\n[y]es / [n]o / [q]uit? ").strip().lower()
        if response in ['y', 'yes']:
            with open(file_path, 'w') as f:
                f.write(new_content)
            print(f"✓ Saved {file_path}")
            return True
        elif response in ['n', 'no']:
            print(f"✗ Skipped {file_path}")
            return False
        elif response in ['q', 'quit']:
            print("Exiting...")
            sys.exit(0)


def expand_glob_patterns(patterns):
    """Expand glob patterns and return list of unique file paths."""
    files = set()
    for pattern in patterns:
        expanded = glob.glob(pattern, recursive=True)
        if not expanded:
            print(f"⚠ No files matched: {pattern}")
        files.update(expanded)
    return sorted(files)


def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <pattern> [<pattern> ...]")
        print("Examples:")
        print("  python script.py file.yaml")
        print("  python script.py '*.yaml'")
        print("  python script.py 'tests/**/*.yaml'")
        print("  python script.py 'cassettes/*.yaml' 'fixtures/*.yaml'")
        sys.exit(1)
    
    file_paths = expand_glob_patterns(sys.argv[1:])
    
    if not file_paths:
        print("✗ No files found matching the provided patterns")
        sys.exit(1)
    
    print(f"Found {len(file_paths)} file(s) to process\n")
    
    processed = 0
    for file_path in file_paths:
        file_obj = Path(file_path)
        
        if not file_obj.exists():
            print(f"✗ File not found: {file_path}")
            continue
        
        if not file_obj.suffix in ['.yaml', '.yml']:
            print(f"⚠ Skipping {file_path} (not a .yaml/.yml file)")
            continue
        
        try:
            if process_yaml_file(file_obj):
                processed += 1
        except Exception as e:
            print(f"✗ Error processing {file_path}: {e}")
        
        print()
    
    print(f"\n{'='*80}")
    print(f"Summary: {processed} file(s) modified")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()


