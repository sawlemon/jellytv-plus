#!/usr/bin/env python3
"""Scope jellytv-plus.css so the theme never applies in Jellyfin's TV layout.

Jellyfin puts the class `layout-tv` on the <html> element on TVs (the Samsung
Tizen app always has it). This script rewrites every selector so it only
matches when <html> does NOT have that class. Python 3 standard library only.

Rules for each selector in a selector list:
  * contains `.layout-tv` (outside `:not(.layout-tv)`)  -> removed. A rule with
    no selectors left is dropped, and so is an @media/@supports block that
    becomes empty. Comments sitting directly above a dropped rule go with it.
  * already contains `:not(.layout-tv)`                  -> left alone.
  * `:root`                                              -> `html:not(.layout-tv)`
  * starts with `html`                                   -> `:not(.layout-tv)` is
    added right after the html compound (before the first space or combinator).
  * starts with `.layout-desktop` / `.layout-mobile`     -> merged onto <html>:
    `html.layout-desktop:not(.layout-tv) .x` (these classes live on <html>
    itself, so a descendant space would never match).
  * starts with a bare pseudo-element (`::selection`)    -> two selectors:
    `html:not(.layout-tv)::selection` and `html:not(.layout-tv) ::selection`.
  * anything else                                        -> prefixed with
    `html:not(.layout-tv) `.

@import, @keyframes, @font-face and other non-conditional at-rules are copied
as they are. @media and @supports are walked recursively. Constructs the
tokenizer cannot handle safely (nested CSS, @layer, @container, @scope,
@starting-style, comments inside selectors) stop the script with an error and
nothing is written.

Running the script twice gives the same file (idempotent).

Usage:
  python3 scripts/scope_css.py jellytv-plus.css            # rewrite in place
  python3 scripts/scope_css.py in.css -o out.css           # write elsewhere
  python3 scripts/scope_css.py jellytv-plus.css --check    # exit 1 if it would change
"""
import argparse
import pathlib
import re
import sys

NOT_TV = ":not(.layout-tv)"
HTML_SCOPE = "html" + NOT_TV
TV_CLASS_RE = re.compile(r"\.layout-tv(?![\w-])")
ROOT_RE = re.compile(r":root(?![\w-])")
HTML_RE = re.compile(r"html(?![\w-])")
LAYOUT_RE = re.compile(r"\.layout-(?:desktop|mobile)(?![\w-])")
AT_NAME_RE = re.compile(r"@([\w-]+)")

# At-rules whose block contains ordinary rules, so we recurse into them.
RECURSE_AT = {"media", "supports"}
# At-rules we refuse to guess about.
UNSUPPORTED_AT = {"layer", "container", "scope", "starting-style", "document", "-moz-document"}


class Unsupported(Exception):
    """The CSS uses something this small tokenizer does not handle safely."""


# ---------------------------------------------------------------- tokenizer --

def skip_string(t, i):
    quote = t[i]
    i += 1
    while i < len(t):
        c = t[i]
        if c == "\\":
            i += 2
            continue
        if c == quote:
            return i + 1
        if c == "\n":
            raise Unsupported("unterminated string near offset %d" % i)
        i += 1
    raise Unsupported("unterminated string at end of file")


def skip_comment(t, i):
    end = t.find("*/", i + 2)
    if end < 0:
        raise Unsupported("unterminated comment at offset %d" % i)
    return end + 2


def scan_prelude(t, i, stops):
    """Return the index of the first stop char at bracket depth 0.

    Skips strings and escapes. A comment inside a prelude (selector or at-rule
    header) is not supported.
    """
    depth = 0
    n = len(t)
    while i < n:
        c = t[i]
        if c == "/" and t.startswith("/*", i):
            raise Unsupported("comment inside a selector/at-rule header at offset %d" % i)
        if c in "\"'":
            i = skip_string(t, i)
            continue
        if c == "\\":
            i += 2
            continue
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif depth <= 0 and c in stops:
            return i
        i += 1
    raise Unsupported("unexpected end of file while reading a header")


def scan_body(t, i):
    """t[i] == '{'. Return the index just after the matching '}'. Nested blocks are rejected."""
    n = len(t)
    j = i + 1
    while j < n:
        c = t[j]
        if c == "/" and t.startswith("/*", j):
            j = skip_comment(t, j)
        elif c in "\"'":
            j = skip_string(t, j)
        elif c == "\\":
            j += 2
        elif c == "{":
            raise Unsupported("nested block (CSS nesting) at offset %d" % j)
        elif c == "}":
            return j + 1
        else:
            j += 1
    raise Unsupported("unterminated block starting at offset %d" % i)


def skip_raw_block(t, i):
    """t[i] == '{'. Like scan_body but allows nested braces (used for @keyframes etc.)."""
    n = len(t)
    depth = 0
    j = i
    while j < n:
        c = t[j]
        if c == "/" and t.startswith("/*", j):
            j = skip_comment(t, j)
            continue
        if c in "\"'":
            j = skip_string(t, j)
            continue
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise Unsupported("unterminated block starting at offset %d" % i)


# Node shapes:
#   ("ws", text) ("comment", text) ("stmt", text) ("raw", text)
#   ("rule", prelude, ws_before_brace, body, indent)
#   ("block", header, children, tail)      # @media / @supports
#   ("dropped",)                            # only exists between passes

def parse(t, i, in_block):
    nodes = []
    n = len(t)
    while True:
        if i >= n:
            if in_block:
                raise Unsupported("missing closing brace at end of file")
            return nodes, i
        c = t[i]
        if t.startswith("/*", i):
            j = skip_comment(t, i)
            nodes.append(("comment", t[i:j]))
            i = j
        elif c.isspace():
            j = i
            while j < n and t[j].isspace():
                j += 1
            nodes.append(("ws", t[i:j]))
            i = j
        elif c == "}":
            if not in_block:
                raise Unsupported("unbalanced closing brace at offset %d" % i)
            return nodes, i
        elif c == "@":
            m = AT_NAME_RE.match(t, i)
            if not m:
                raise Unsupported("odd at-rule at offset %d" % i)
            name = m.group(1).lower()
            if name in UNSUPPORTED_AT:
                raise Unsupported("@%s is not supported (offset %d)" % (name, i))
            stop = scan_prelude(t, i, "{;")
            if t[stop] == ";":
                nodes.append(("stmt", t[i:stop + 1]))
                i = stop + 1
            elif name in RECURSE_AT:
                children, j = parse(t, stop + 1, True)
                nodes.append(("block", t[i:stop + 1], children, "}"))
                i = j + 1
            else:
                j = skip_raw_block(t, stop)
                nodes.append(("raw", t[i:j]))
                i = j
        else:
            stop = scan_prelude(t, i, "{;}")
            if t[stop] != "{":
                raise Unsupported("declaration or stray text outside a rule at offset %d" % i)
            raw_prelude = t[i:stop]
            prelude = raw_prelude.rstrip()
            ws = raw_prelude[len(prelude):]
            end = scan_body(t, stop)
            line_start = t.rfind("\n", 0, i) + 1
            seg = t[line_start:i]
            indent = seg if seg.strip() == "" else ""
            nodes.append(("rule", prelude, ws, t[stop:end], indent))
            i = end


def render(nodes):
    out = []
    for node in nodes:
        kind = node[0]
        if kind in ("ws", "comment", "stmt", "raw"):
            out.append(node[1])
        elif kind == "rule":
            out.append(node[1] + node[2] + node[3])
        elif kind == "block":
            out.append(node[1] + render(node[2]) + node[3])
        else:
            raise AssertionError(kind)
    return "".join(out)


# --------------------------------------------------------- selector scoping --

def split_selector_list(prelude):
    parts = []
    depth = 0
    start = 0
    i = 0
    while i < len(prelude):
        c = prelude[i]
        if c in "\"'":
            i = skip_string(prelude, i)
            continue
        if c == "\\":
            i += 2
            continue
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(prelude[start:i].strip())
            start = i + 1
        i += 1
    parts.append(prelude[start:].strip())
    if any(p == "" for p in parts):
        raise Unsupported("empty selector in list: %r" % prelude)
    return parts


def html_compound_end(part):
    """Index where the leading `html...` compound selector ends."""
    depth = 0
    i = 0
    while i < len(part):
        c = part[i]
        if c in "\"'":
            i = skip_string(part, i)
            continue
        if c == "\\":
            i += 2
            continue
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif depth == 0 and (c.isspace() or c in ">+~"):
            break
        elif depth == 0 and part.startswith("::", i):
            break
        i += 1
    return i


def is_tv_part(part):
    return bool(TV_CLASS_RE.search(part.replace(NOT_TV, "")))


def scope_part(part):
    """Return None (drop), or a list of replacement selectors."""
    if is_tv_part(part):
        return None
    if NOT_TV in part:
        return [part]
    if ROOT_RE.match(part):
        return [HTML_SCOPE + part[len(":root"):]]
    if HTML_RE.match(part):
        end = html_compound_end(part)
        return [part[:end] + NOT_TV + part[end:]]
    m = LAYOUT_RE.match(part)
    if m:
        # Jellyfin puts layout-desktop / layout-mobile on <html> itself, so they
        # must join the html compound; a descendant space would never match.
        return ["html" + m.group(0) + NOT_TV + part[m.end():]]
    if part.startswith("::"):
        return [HTML_SCOPE + part, HTML_SCOPE + " " + part]
    return [HTML_SCOPE + " " + part]


class Stats:
    def __init__(self):
        self.rules_seen = 0
        self.rules_dropped = 0
        self.rules_rewritten = 0
        self.blocks_dropped = 0
        self.dropped_selectors = []


def scope_rule(node, stats):
    _, prelude, ws, body, indent = node
    stats.rules_seen += 1
    parts = split_selector_list(prelude)
    new_parts = []
    for p in parts:
        res = scope_part(p)
        if res is None:
            stats.dropped_selectors.append(p)
        else:
            new_parts.extend(res)
    if not new_parts:
        stats.rules_dropped += 1
        return ("dropped",)
    if new_parts == parts:
        return node  # already scoped: keep the original formatting byte for byte
    stats.rules_rewritten += 1
    return ("rule", (",\n" + indent).join(new_parts), ws, body, indent)


# ------------------------------------------------------------ dropping nodes --

def own_line(nodes, k):
    return k == 0 or (nodes[k - 1][0] == "ws" and "\n" in nodes[k - 1][1])


def remove_dropped(nodes):
    """Delete ("dropped",) markers, the comments attached above them, and extra blank space."""
    i = 0
    while i < len(nodes):
        if nodes[i][0] != "dropped":
            i += 1
            continue
        start = i
        while True:
            j = start - 1
            if j >= 0 and nodes[j][0] == "ws" and nodes[j][1].count("\n") <= 1:
                k = j - 1
            else:
                k = j
            if k >= 0 and nodes[k][0] == "comment" and own_line(nodes, k):
                start = k
                continue
            break
        del nodes[start:i + 1]
        prev_ws = start - 1 >= 0 and nodes[start - 1][0] == "ws"
        next_ws = start < len(nodes) and nodes[start][0] == "ws"
        if prev_ws and next_ws:
            if nodes[start - 1][1].count("\n") > nodes[start][1].count("\n"):
                del nodes[start]
            else:
                del nodes[start - 1]
        elif next_ws and start == 0:
            del nodes[start]
        i = max(start - 1, 0)
    return nodes


def has_content(nodes):
    return any(n[0] in ("rule", "block", "stmt", "raw") for n in nodes)


def transform(nodes, stats):
    out = []
    for node in nodes:
        kind = node[0]
        if kind == "rule":
            out.append(scope_rule(node, stats))
        elif kind == "block":
            had_content = has_content(node[2])
            children = transform(node[2], stats)
            if had_content and not has_content(children):
                stats.blocks_dropped += 1
                out.append(("dropped",))
            else:
                out.append(("block", node[1], children, node[3]))
        else:
            out.append(node)
    return remove_dropped(out)


def scope_css(text):
    nodes, _ = parse(text, 0, False)
    stats = Stats()
    result = render(transform(nodes, stats))
    # Safety net: a second pass over our own output must change nothing.
    again = render(transform(parse(result, 0, False)[0], Stats()))
    if again != result:
        raise Unsupported("internal error: output is not stable under a second run")
    return result, stats


# ----------------------------------------------------------------------- CLI --

def main(argv=None):
    ap = argparse.ArgumentParser(description="Make a Jellyfin theme stylesheet skip the TV layout.")
    ap.add_argument("css", type=pathlib.Path, help="stylesheet to scope")
    ap.add_argument("-o", "--output", type=pathlib.Path, help="write here instead of changing the input file")
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if the file would change")
    args = ap.parse_args(argv)

    try:
        src = args.css.read_bytes().decode("utf-8")
        out, stats = scope_css(src)
    except Unsupported as e:
        print("error: %s\nnothing was written." % e, file=sys.stderr)
        return 2

    for sel in stats.dropped_selectors:
        print("dropped TV selector: " + sel, file=sys.stderr)
    print(
        "rules: %d seen, %d dropped, %d rewritten; TV selectors removed: %d; empty @media/@supports dropped: %d"
        % (stats.rules_seen, stats.rules_dropped, stats.rules_rewritten,
           len(stats.dropped_selectors), stats.blocks_dropped),
        file=sys.stderr,
    )

    if args.check:
        changed = out != src
        print("would change" if changed else "already scoped", file=sys.stderr)
        return 1 if changed else 0

    target = args.output or args.css
    if args.output is None and out == src:
        print("%s is already scoped; left as is." % target, file=sys.stderr)
        return 0
    target.write_bytes(out.encode("utf-8"))
    print("wrote " + str(target), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
