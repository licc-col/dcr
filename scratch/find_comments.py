import glob
import os
import re

def main():
    html_dir = r"d:\ICC-2026\pasantía\cuervo\CD-ROM\html"
    files = glob.glob(os.path.join(html_dir, "*.htm"))
    
    comment_patterns = set()
    total_comments = 0
    
    for filepath in files:
        if re.search(r'_[ef]\.htm$', filepath, re.IGNORECASE) or os.path.basename(filepath).startswith('a-x'):
            continue
        try:
            with open(filepath, 'r', encoding='windows-1252', errors='ignore') as f:
                content = f.read()
        except Exception:
            continue
            
        comments = re.findall(r'<!--.*?-->', content, flags=re.DOTALL)
        for c in comments:
            total_comments += 1
            # Keep unique patterns by replacing content inside tags
            pattern = re.sub(r'<dicentry>.*?</dicentry>', '<dicentry>...</dicentry>', c)
            pattern = re.sub(r'<dicgrammar>.*?</dicgrammar>', '<dicgrammar>...</dicgrammar>', pattern)
            comment_patterns.add(pattern)
            
    print(f"Total comments found: {total_comments}")
    print("Unique comment patterns:")
    for p in sorted(comment_patterns):
        print(f"  {repr(p)}")

if __name__ == "__main__":
    main()
