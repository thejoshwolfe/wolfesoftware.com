#!/usr/bin/env python3

import os, sys, subprocess
import re
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

    build_html()
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

def build_html():
    definitions = load_authoritative_definitions("index.html")
    propagate_definitions(definitions, "blog/base.html")
    definitions["post-list"] = generate_post_list()

    propagate_definitions(definitions, "blog/index.html")
    propagate_definitions(definitions, "resume/index.html")
    propagate_definitions(definitions, "index.html")

def load_authoritative_definitions(path):
    with open(path) as f:
        contents = f.read()

    definitions = {}
    for name, body in re.findall(r'<!--BEGIN_AUTHORITATIVE "(.*?)" \{\{-->(.*?)<!--\}\} END_AUTHORITATIVE-->', contents, flags=re.DOTALL):
        definitions[name] = body

    return definitions

def propagate_definitions(definitions, path):
    with open(path) as f:
        contents = f.read()
    original_contents = contents

    for match in reversed(list(re.finditer(r'<!--BEGIN_GENERATED "(.*?)" \{\{-->(.*?)<!--\}\} END_GENERATED-->', contents, flags=re.DOTALL))):
        body = definitions[match.group(1)]
        contents = contents[:match.span(2)[0]] + body + contents[match.span(2)[1]:]

    if original_contents != contents:
        with open(path, "w") as f:
            f.write(contents)

def generate_post_list():
    index_elements = []
    rss_elements = []

    compile_blog_file("blog/hello-blog.md", index_elements, rss_elements)

    # The date in YYYY-MM-DD format comes before the title, so this will sort chronologically:
    index_elements.sort(reverse=True)
    post_list_html = "\n" + "\n".join(index_elements) + "\n"

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

    return post_list_html


def compile_blog_file(markdown_path, index_elements, rss_elements, *, do_internal_links=False, toc_levels=0):
    html_path = markdown_path.replace(".md", ".html")
    assert html_path == escape_attribute(html_path), "need to add escaping for urls and stuff"
    with open(markdown_path) as f:
        markdown_contents = f.read()

    # Parameters
    title = re.match(r'^# (.*)', markdown_contents).group(1)
    assert title == escape_text(title)
    date_html, src_html = generate_version_control_html(markdown_path)
    body_html = markdown_to_html(markdown_contents, do_internal_links=do_internal_links, toc_levels=toc_levels)
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
        .replace("{{BODY}}", body_html)
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
        BODY=escape_cdata(body_html),
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

def markdown_to_html(*args, **kwargs):
    import importlib.util
    spec = importlib.util.spec_from_file_location("markdown_asdf", os.path.join(os.path.dirname(os.path.abspath(__file__)), "deps/markdown-looks-good/markdown_looks_good.py"))
    markdown_looks_good = importlib.util.module_from_spec(spec)
    sys.modules["markdown_looks_good"] = markdown_looks_good
    spec.loader.exec_module(markdown_looks_good)
    return markdown_looks_good.markdown_to_html(*args, **kwargs)

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
