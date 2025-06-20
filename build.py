#!/usr/bin/env python3

import os, sys, subprocess
import re, io
import datetime, email.utils

from functools import lru_cache

def main():
    import argparse
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--just-build", action="store_true", help=
        "Don't touch s3cmd or the network. Just do the build locally.")
    group.add_argument("--publish", action="store_true", help=
        "Actually publish instead of just showing a diff. Removes the --dry-run argument from s3cmd sync.")
    args = parser.parse_args()

    assert os.path.samefile(".", get_repo_root()), "must be executed from the repo root"

    build_sidebar()
    build_blog()
    check_resume()

    if args.just_build: return
    do_publish(dry_run=not args.publish)

def check_resume():
    source_mtime = os.stat("resume/index.html").st_mtime
    try:
        generated_mtime = os.stat("resume/Josh_Wolfe_resume.pdf").st_mtime
    except FileNotFoundError:
        generated_mtime = float("-inf")
    if source_mtime > generated_mtime:
        sys.exit("ERROR: it looks like resume/Josh_Wolfe_resume.pdf needs to be re-rendered (from a browser).")

publish_roots = [
    "index.html",
    "resume/",
    "blog/",
    "site/",
]
def do_publish(dry_run):
    s3cmd = [
        "s3cmd", "sync",
        "--acl-public", "--no-preserve",
        "--add-header=Cache-Control: max-age=0, must-revalidate",
        # mime magic is buggy for css files. guess mime type based on file extension only.
        # See https://stackoverflow.com/questions/53708938/s3cmd-flagging-css-with-wrong-mime-type
        "--no-mime-magic", "--guess-mime-type",
    ]
    if dry_run:
        s3cmd.append("--dry-run")
    bucket = "s3://wolfesoftware.com/"

    for root in publish_roots:
        cmd = s3cmd + [root, bucket + root]
        subprocess.run(cmd, check=True)

files_with_sidebar = [
    "index.html", # authoritative
    "resume/index.html",
    "blog/index.html",
    "blog/base.html",
]
def build_sidebar():
    the_sidebar_contents = None
    for file in files_with_sidebar:
        with open(file) as f:
            contents = f.read()
        match = re.search(r'\n( +)<div id="sidebar".*?>(.*?)\n\1</div>', contents, re.DOTALL)
        if the_sidebar_contents == None:
            # Authoritative
            the_sidebar_contents = match.group(2)
        else:
            # Write to this file.
            new_contents = contents[:match.span(2)[0]] + the_sidebar_contents + contents[match.span(2)[1]:]
            if contents != new_contents:
                with open(file, "w") as f:
                    f.write(new_contents)


blog_files = [
    "blog/hello-blog.md",
]
files_with_blog_list = [
    "blog/index.html",
    "index.html",
]
def build_blog():
    index_elements = []
    rss_elements = []
    for file in blog_files:
        compile_file(file, index_elements, rss_elements)
    # The date in YYYY-MM-DD format comes before the title, so this will sort chronologically:
    index_elements.sort(reverse=True)

    # Insert the list of posts into various html documents.
    for index_path in files_with_blog_list:
        with open(index_path) as f:
            index_contents = f.read()
        match = re.search(r'\n( +)<ul id="post-list".*?>(.*?)\n\1</ul>', index_contents, re.DOTALL)
        start, end = match.span(2)
        new_contents = index_contents[:start] + "\n" + "\n".join(index_elements) + index_contents[end:]
        if new_contents != index_contents:
            with open(index_path, "w") as f:
                f.write(new_contents)

    # Build full rss.xml document.
    with open("blog/rss-template.xml") as f:
        base_rss = f.read()
    rss_content = (base_rss
        .replace("{{LAST_BUILD_DATE}}", email.utils.format_datetime(datetime.datetime.now(datetime.UTC), usegmt=True))
        .replace("{{ITEMS}}", "".join(rss_elements))
    )
    # Only update if something changed, other than that timestamp we just threw in there.
    with open("blog/rss.xml") as f:
        previous_rss_content = f.read()
    def strip_last_build_date(rss_content):
        start = rss_content.index("<lastBuildDate>")
        end = rss_content.index("\n", start)
        stripped = rss_content[:start] + rss_content[end:]
        return stripped
    if strip_last_build_date(previous_rss_content) != strip_last_build_date(rss_content):
        with open("blog/rss.xml", "w") as f:
            f.write(rss_content)


def compile_file(markdown_path, index_elements, rss_elements):
    html_path = markdown_path.replace(".md", ".html")
    assert html_path == escape_attribute(html_path), "need to add escaping for urls and stuff"
    with open(markdown_path) as f:
        markdown_contents = f.read()

    # Parameters
    title = re.match(r'^# (.*)', markdown_contents).group(1)
    assert title == escape_text(title)
    date_html, src_html = generate_version_control_html(markdown_path)
    html_body = markdown_to_html(markdown_contents)
    # Date is in RFC-something format: Sat, 07 Sep 2002 00:00:01 GMT
    cmd = ["git", "rev-list", "-n1", "--no-commit-header", "--pretty=tformat:%aD", "HEAD", "--", markdown_path]
    pub_date = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode("utf8").rstrip()
    if len(pub_date) == 0:
        # Not committed yet. Assume now.
        pub_date = email.utils.format_datetime(datetime.datetime.now(datetime.UTC), usegmt=True)

    # output html
    with open("blog/base.html") as f:
        html_base = f.read()
    html = (html_base
        .replace("{{TITLE}}", title)
        .replace("{{BODY}}", html_body)
        .replace("{{DATE}}", date_html)
        .replace("{{SRC}}", src_html)
    )
    with open(html_path, "w") as f:
        f.write(html)

    # output index
    index_elements.append('<li>{} - <a href=/{}>{}</a></li>'.format(date_html, html_path, title))

    # output rss
    rss_elements.append("""\
      <item>
         <title>{TITLE}</title>
         <pubDate>{PUB_DATE}</pubDate>

         <link>https://wolfesoftware.com/{HTML_PATH}</link>
         <guid>https://wolfesoftware.com/{HTML_PATH}</guid>
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
    cmd = ["git", "rev-list", "--no-commit-header", "--pretty=tformat:%as", "HEAD", "--", path]
    dates = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode("utf8").split()
    if len(dates) == 0:
        # Not committed yet. Assume now.
        dates = [datetime.datetime.now().isoformat()[:10]]
    dates = sorted(set(dates))

    timestamp_blurb = escape_text(dates[0])
    if len(dates) > 1:
        history_url = "https://github.com/thejoshwolfe/wolfesoftware.com/commits/master/" + path
        timestamp_blurb += ", updated <a href={}>{}</a>".format(
            escape_attribute(history_url),
            escape_text(dates[-1]),
        )

    source_url = "https://github.com/thejoshwolfe/wolfesoftware.com/blob/master/" + path
    source_link = "<a href={}>src</a>".format(escape_attribute(source_url))

    return timestamp_blurb, source_link


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
    def set_current_structural_tag_name(tag_name, attrs=None):
        nonlocal current_structural_tag_name
        if current_structural_tag_name == tag_name: return False
        if current_structural_tag_name != None:
            out.write("</{}>\n".format(current_structural_tag_name))
        current_structural_tag_name = tag_name
        if current_structural_tag_name != None:
            out.write("<" + current_structural_tag_name)
            if attrs != None:
                out.write(" " + attrs)
            out.write(">")
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
            hashes, text = structure.group().split(" ", 1)
            h_number = len(hashes)
            assert 1 <= h_number <= 4
            set_current_structural_tag_name("h{}".format(h_number), "class=markdown")
            out.write("<span class=markdown-annotation>{}</span> ".format(hashes))
        elif structure.group("other") != None:
            if not set_current_structural_tag_name("p", "class=markdown"):
                out.write("<br>\n")
            text = structure.group()
        else: assert False

        inline_style(text)
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


@lru_cache()
def get_repo_root():
    return subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, stdout=subprocess.PIPE).stdout.decode("utf8").rstrip()

if __name__ == "__main__":
    main()
