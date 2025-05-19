#!/usr/bin/env python3

import sys, re

files_with_sidebar = [
    "index.html",
    "resume/index.html",
    "blog/index.html",
]

def main():
    import argparse
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    all_sidebar_contents = set()
    for file in files_with_sidebar:
        with open(file) as f:
            contents = f.read()
        sidebar_contents = re.search(r'\n    <div id="sidebar".*?>\n(.*?)\n    </div>', contents, re.DOTALL).group(1)
        all_sidebar_contents.add(sidebar_contents)

    if len(all_sidebar_contents) > 1:
        sys.exit("ERROR: sidebar doesn't match between these files:\n" + "\n".join(files_with_sidebar))

if __name__ == "__main__":
    main()
