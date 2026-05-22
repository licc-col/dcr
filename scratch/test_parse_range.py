import glob
import os
import re
import time
from mass_convert import parse_html_to_json

def main():
    html_dir = r'd:\ICC-2026\pasantía\cuervo\CD-ROM\html'
    files = glob.glob(os.path.join(html_dir, '*.htm'))
    valid_files = [f for f in files if not re.search(r'_[ef]\.htm$', f, re.IGNORECASE) and not os.path.basename(f).startswith('a-x')]
    
    print(f"Total valid files: {len(valid_files)}")
    
    # We test files in the range 1495 to 1550
    test_range = valid_files[1495:1550]
    
    for idx, filepath in enumerate(test_range):
        global_idx = 1495 + idx
        filename = os.path.basename(filepath)
        print(f"Testing {global_idx}: {filename} ... ", end="", flush=True)
        
        start_time = time.time()
        try:
            parsed = parse_html_to_json(filepath)
            duration = time.time() - start_time
            print(f"Success ({duration:.4f}s)")
        except Exception as e:
            print(f"FAILED with exception: {e}")

if __name__ == "__main__":
    main()
