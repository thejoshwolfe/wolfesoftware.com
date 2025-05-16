#!/usr/bin/env python3

import os, sys, subprocess
import re, io
import datetime, email.utils

from functools import lru_cache

files = [
    "hello-blog.md",
]

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.parse_args()

    rss_elements = []
    for file in files:
        compile_file(file, rss_elements)

    # Build full rss.xml document.
    with open("rss-template.xml") as f:
        base_rss = f.read()
    rss_content = (base_rss
        .replace("{{LAST_BUILD_DATE}}", email.utils.format_datetime(datetime.datetime.now(datetime.UTC), usegmt=True))
        .replace("{{ITEMS}}", "".join(rss_elements))
    )
    # Only update if something changed, other than that timestamp we just threw in there.
    with open("rss.xml") as f:
        previous_rss_content = f.read()
    def strip_last_build_date(rss_content):
        start = rss_content.index("<lastBuildDate>")
        end = rss_content.index("\n", start)
        stripped = rss_content[:start] + rss_content[end:]
        return stripped
    if strip_last_build_date(previous_rss_content) != strip_last_build_date(rss_content):
        with open("rss.xml", "w") as f:
            f.write(rss_content)


def compile_file(markdown_path, rss_elements):
    html_path = markdown_path.replace(".md", ".html")
    with open(markdown_path) as f:
        markdown_contents = f.read()

    # Parameters
    title = re.match(r'^# (.*)', markdown_contents).group(1)
    version_control = generate_version_control_html(markdown_path)
    html_body = markdown_to_html(markdown_contents)
    # Date is in RFC-something format: Sat, 07 Sep 2002 00:00:01 GMT
    cmd = ["git", "rev-list", "-n1", "--no-commit-header", "--pretty=tformat:%aD", "HEAD", "--", markdown_path]
    pub_date = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode("utf8").rstrip()
    if len(pub_date) == 0:
        # Not committed yet. Assume now.
        pub_date = email.utils.format_datetime(datetime.datetime.now(datetime.UTC), usegmt=True)

    # output html
    with open("base.html") as f:
        html_base = f.read()
    html = (html_base
        .replace("{{TITLE}}", title)
        .replace("{{BODY}}", html_body)
        .replace("{{VERSION_CONTROL}}", version_control)
    )
    with open(html_path, "w") as f:
        f.write(html)

    # output rss

    rss_elements.append("""\
      <item>
         <title>{TITLE}</title>
         <pubDate>{PUB_DATE}</pubDate>

         <link>https://wolfesoftware.com/blog/{HTML_PATH}</link>
         <guid>https://wolfesoftware.com/blog/{HTML_PATH}</guid>
         <description><![CDATA[{BODY}]]></description>
      </item>
""".format(
        TITLE=title,
        PUB_DATE=pub_date,
        HTML_PATH=html_path,
        BODY=escape_cdata(html_body),
    ))

def generate_version_control_html(path):
    # Dates are in YYYY-MM-DD format
    path_in_repo = os.path.relpath(path, get_repo_root())
    cmd = ["git", "rev-list", "--no-commit-header", "--pretty=tformat:%as", "HEAD", "--", path]
    dates = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode("utf8").split()
    if len(dates) == 0:
        # Not committed yet. Assume now.
        dates = [datetime.datetime.now().isoformat()[:10]]
    dates = sorted(set(dates))

    timestamp_blurb = escape_text(dates[0])
    if len(dates) > 1:
        history_url = "https://github.com/thejoshwolfe/wolfesoftware.com/commits/master/" + path_in_repo
        timestamp_blurb += ", updated <a href={}>{}</a>".format(
            escape_attribute(history_url),
            escape_text(dates[-1]),
        )

    source_url = "https://github.com/thejoshwolfe/wolfesoftware.com/blob/master/" + path_in_repo
    source_link = "<a href={}>src</a>".format(escape_attribute(source_url))

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
                out.write(escape_text(text))
                return
            out.write(escape_text(text[:match.span()[0]]))

            if match.group("url"):
                out.write("<a href={}>{}</a>".format(
                    escape_attribute(match.group()),
                    escape_text(match.group()),
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

attribute_substitutions = {
    # https://www.w3.org/TR/2012/WD-html-markup-20120329/syntax.html#syntax-attr-unquoted
    '"': "&quot;",
    "'": "&apos;",
    "=": "&#61;",
    ">": "&gt;",
    "<": "&lt;",
    "`": "&#96;",
    "&": "&amp;",
}
attribute_escape_re = re.compile(r'[{}]'.format(r''.join(attribute_substitutions.keys())))
def escape_attribute(text):
    return attribute_escape_re.sub((lambda m: attribute_substitutions[m.group()]), text)
text_substitutions = {
    ">": "&gt;",
    "<": "&lt;",
    "&": "&amp;",
}
text_escape_re = re.compile(r'[{}]'.format(r''.join(text_substitutions.keys())))
def escape_text(text):
    return text_escape_re.sub((lambda m: text_substitutions[m.group()]), text)

def escape_cdata(text):
    return text.replace("]]>", "]]]]><![CDATA[>")

if __name__ == "__main__":
    main()
