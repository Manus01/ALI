import os
import re

def scan_file(filepath):
    issues = []
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        line_num = i + 1
        content = line.strip()
        
        # 1. Check for print statements (ignore comments)
        # Use regex to ensure it's a standalone print call, not part of a word like 'blueprint('
        if re.search(r'\bprint\(', content) and not content.startswith("#"):
            issues.append(f"Line {line_num}: Used 'print()' instead of logger.")

        # 2. Check for broad except without logging (simple heuristic)
        if "except:" in content or "except Exception:" in content:
            # Check next line for logger
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if "logger" not in next_line and "raise" not in next_line and "pass" not in next_line:
                     issues.append(f"Line {line_num}: Broad exception found. Ensure it is logged or re-raised.")
        
        # 3. Hardcoded Secrets (Heuristic for "AIza" or high entropy strings assignment)
        if "AIza" in content and "=" in content and "os.environ" not in content:
             issues.append(f"Line {line_num}: Possible Hardcoded Google Key detected.")

    return issues

def main():
    target_dir = os.path.join(os.getcwd(), 'app')
    print(f"[SCAN] Starting Static Analysis on {target_dir}...")
    
    total_issues = 0
    file_count = 0
    
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith(".py"):
                file_count += 1
                path = os.path.join(root, file)
                issues = scan_file(path)
                
                if issues:
                    print(f"\n[FILE] {file}:")
                    for issue in issues:
                        print(f"  [X] {issue}")
                    total_issues += len(issues)

    print(f"\nScan Complete. {total_issues} issues found in {file_count} files.")
    if total_issues > 0:
        exit(1)

if __name__ == "__main__":
    main()
