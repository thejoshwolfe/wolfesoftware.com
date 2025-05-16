#!/usr/bin/env python3

import os, sys, subprocess
import re, io
import datetime
from functools import lru_cache

files = [
    "hello-blog.md",
]

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.parse_args()

    for file in files:
        compile_file(file)

def compile_file(markdown_path):
    with open(markdown_path) as f:
        markdown_contents = f.read()

    # Parameters
    title = re.match(r'^# (.*)', markdown_contents).group(1)
    version_control = generate_version_control_html(markdown_path)
    html_body = markdown_to_html(markdown_contents)

    # output
    with open("base.html") as f:
        html_base = f.read()
    html = (html_base
        .replace("{{TITLE}}", title)
        .replace("{{BODY}}", html_body)
        .replace("{{VERSION_CONTROL}}", version_control)
    )
    with open(markdown_path.replace(".md", ".html"), "w") as f:
        f.write(html)

def generate_version_control_html(path):
    # Dates are in YYYY-MM-DD format
    path_in_repo = os.path.relpath(path, get_repo_root())
    cmd = ["git", "rev-list", "--no-commit-header", "--pretty=tformat:%as", "HEAD", "--", path]
    dates = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode("utf8").split()
    if len(dates) == 0:
        # Not committed yet. Assume now.
        dates = [datetime.datetime.now().isoformat()[:10]]
    dates = sorted(set(dates))

    timestamp_blurb = escape(dates[0])
    if len(dates) > 1:
        history_url = "https://github.com/thejoshwolfe/wolfesoftware.com/commits/master/" + path_in_repo
        timestamp_blurb += ", updated <a href={}>{}</a>".format(
            escape(history_url),
            escape(dates[-1]),
        )

    source_url = "https://github.com/thejoshwolfe/wolfesoftware.com/blob/master/" + path_in_repo
    source_link = "<a href={}>src</a>".format(escape(source_url))

    return "({}) - {}".format(timestamp_blurb, source_link)


@lru_cache()
def get_repo_root():
    return subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, stdout=subprocess.PIPE).stdout.decode("utf8").rstrip()

structural_re = re.compile(
    r'(?P<heading>^#+ .*?$)|'
    r'(?P<other>^.*?$)'
    , re.MULTILINE
)

inline_re = re.compile(
    r'(?P<url>https://\S+)'
)

def markdown_to_html(contents):
    out = io.StringIO()

    current_structural_tag_name = None
    def set_current_structural_tag_name(tag_name):
        nonlocal current_structural_tag_name
        if current_structural_tag_name == tag_name: return False
        if current_structural_tag_name != None:
            out.write("</{}>\n".format(current_structural_tag_name))
        current_structural_tag_name = tag_name
        if current_structural_tag_name != None:
            out.write("<{}>".format(current_structural_tag_name))
        return True

    def inline_style(text):
        while True:
            match = inline_re.search(text)
            if match == None:
                out.write(escape(text))
                return
            out.write(escape(text[:match.span()[0]]))

            if match.group("url"):
                out.write("<a href={}>{}</a>".format(
                    escape(match.group()),
                    escape(match.group()),
                ))
            else: assert False

            text = text[match.span()[1]:]

    for structure in structural_re.finditer(contents):
        if structure.group("heading") != None:
            h_number = len(structure.group().split(" ", 1)[0])
            assert 1 <= h_number <= 4
            set_current_structural_tag_name("h{}".format(h_number))
        elif structure.group("other") != None:
            if not set_current_structural_tag_name("p"):
                out.write("<br>\n")
        else: assert False

        inline_style(structure.group())
    set_current_structural_tag_name(None)

    return out.getvalue()

substitutions = {
    # https://www.w3.org/TR/2012/WD-html-markup-20120329/syntax.html#syntax-attr-unquoted
    '"': "&quot;",
    "'": "&apos;",
    "=": "&#61;",
    ">": "&gt;",
    "<": "&lt;",
    "`": "&#96;",
    "&": "&amp;",
}
escape_re = re.compile(r'[{}]'.format(r''.join(substitutions.keys())))
def escape(text):
    return escape_re.sub((lambda m: substitutions[m.group()]), text)

if __name__ == "__main__":
    main()
