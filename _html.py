"""Minimal HTML tree + CSS selector engine. Zero dependencies."""
import re
from html.parser import HTMLParser

_VOID = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "_raw")

    def __init__(self, tag="", attrs=()):
        self.tag = tag.lower() if tag else ""
        self.attrs = {k.lower(): (v if v is not None else "") for k, v in attrs}
        self.children = []
        self.parent = None
        self._raw = None  # raw text for <script>/<style>

    def get(self, attr, default=None):
        return self.attrs.get(attr, default)

    def get_text(self, strip=False):
        if self._raw is not None:
            t = self._raw
        else:
            parts = []
            for c in self.children:
                if isinstance(c, str):
                    parts.append(c)
                elif isinstance(c, Node):
                    parts.append(c.get_text())
            t = "".join(parts)
        return t.strip() if strip else t

    def find(self, tag, **kw):
        """Find first descendant with given tag and matching attributes."""
        tag = tag.lower()
        def _walk(node):
            for child in node.children:
                if not isinstance(child, Node):
                    continue
                if child.tag == tag and all(child.attrs.get(k) == v for k, v in kw.items()):
                    return child
                found = _walk(child)
                if found:
                    return found
            return None
        return _walk(self)

    def select(self, selector):
        out = []
        for s in _split_commas(selector):
            _css_select(self, s.strip(), out)
        seen, deduped = set(), []
        for n in out:
            if id(n) not in seen:
                seen.add(id(n))
                deduped.append(n)
        return deduped

    def select_one(self, selector):
        r = self.select(selector)
        return r[0] if r else None

    def __repr__(self):
        attrs = " ".join(f'{k}="{v}"' for k, v in list(self.attrs.items())[:2])
        return f"<{self.tag} {attrs}>"


# ── CSS selector engine ──────────────────────────────────────────────────────

def _split_commas(s):
    parts, depth, cur = [], 0, []
    for ch in s:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur).strip())
    return [p for p in parts if p]


_RE_TAG   = re.compile(r"^([a-z][a-z0-9-]*)", re.I)
_RE_ID    = re.compile(r"#([a-z][a-z0-9_-]*)", re.I)
_RE_CLASS = re.compile(r"\.([a-z][a-z0-9_-]*)", re.I)
_RE_ATTR  = re.compile(r"\[([a-z][a-z0-9_-]*)(?:([*^$~]?=)['\"]?([^'\"]*)['\"]?)?\]", re.I)


def _parse_part(s):
    tag_m = _RE_TAG.match(s)
    tag   = tag_m.group(1).lower() if tag_m else None
    id_m  = _RE_ID.search(s)
    id_   = id_m.group(1) if id_m else None
    classes = [m.group(1).lower() for m in _RE_CLASS.finditer(s)]
    attrs   = [
        (m.group(1).lower(), m.group(2) or "", m.group(3) or "")
        for m in _RE_ATTR.finditer(s)
    ]
    return tag, id_, classes, attrs


def _matches(node, part):
    if not isinstance(node, Node) or not node.tag:
        return False
    tag, id_, classes, attrs = _parse_part(part)
    if tag and node.tag != tag:
        return False
    if id_ and node.attrs.get("id") != id_:
        return False
    node_cls = set(node.attrs.get("class", "").split())
    if not all(c in node_cls for c in classes):
        return False
    for name, op, val in attrs:
        av = node.attrs.get(name)
        if av is None:
            return False
        if   op == "*=" and val not in av:           return False
        elif op == "^=" and not av.startswith(val):  return False
        elif op == "$=" and not av.endswith(val):    return False
        elif op == "=" and av != val:                return False
        elif op == "~=" and val not in av.split():   return False
    return True


def _find_all(root, part):
    results = []
    def walk(node):
        for child in node.children:
            if isinstance(child, Node):
                if _matches(child, part):
                    results.append(child)
                walk(child)
    walk(root)
    return results


def _css_select(root, selector, out):
    """Append all descendants of root matching selector (descendant combinator)."""
    parts = selector.split()
    if not parts:
        return
    candidates = _find_all(root, parts[0])
    for part in parts[1:]:
        next_cands = []
        for cand in candidates:
            next_cands.extend(_find_all(cand, part))
        candidates = next_cands
    out.extend(candidates)


# ── HTML tree builder ────────────────────────────────────────────────────────

class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("_root")
        self._stack = [self.root]
        self._raw_node = None

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        node.parent = self._stack[-1]
        self._stack[-1].children.append(node)
        if tag.lower() not in _VOID:
            self._stack.append(node)
        if tag.lower() in ("script", "style"):
            self._raw_node = node

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self._raw_node and self._raw_node.tag == tag:
            self._raw_node = None
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i].tag == tag:
                self._stack = self._stack[:i]
                return

    def handle_data(self, data):
        if self._raw_node is not None:
            self._raw_node._raw = (self._raw_node._raw or "") + data
        elif self._stack:
            self._stack[-1].children.append(data)


def parse(html):
    b = _Builder()
    b.feed(html)
    return b.root
