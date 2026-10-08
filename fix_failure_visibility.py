import os

file_path = 'main.py'
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Target: locate the start of handle_failure
start_idx = -1
for i in range(len(lines)):
    if lines[i].strip() == "def handle_failure(self, error_msg: str):":
        start_idx = i
        break

if start_idx == -1:
    print("Error: Could not find handle_failure definition")
    exit(1)

# We want to insert overlay.show() right after the initial logger.info call
# Current lines around start_idx:
# start_idx: def handle_failure...
# start_idx+1: """Consistent failure..."""
# start_idx+2: logger.info(f"Handling failure: {error_msg}")
# <INSERT HERE>

insertion_point = start_idx + 3
lines.insert(insertion_point, "        overlay.show()\n")

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Modification successful")
