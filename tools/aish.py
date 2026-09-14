#!/usr/bin/env python3
"""Aish v1: validate documents, measure real token cost, audit abbreviations.

  aish.py check FILE...        validate structure
  aish.py measure AISH ENGLISH compare token cost of two files
  aish.py lex WORD...          report which words cost >1 token
  aish.py demo                 self-check

Token counts use tiktoken when installed, else a chars/4 estimate (flagged).
"""
import sys

SIGILS = set(".!+-?>*~@")

try:
    import tiktoken
    _enc = tiktoken.get_encoding("o200k_base")
    def ntok(s): return len(_enc.encode(s))
    EXACT = True
except ImportError:  # ponytail: estimate is fine for ratios, exact needs tiktoken
    def ntok(s): return max(1, round(len(s) / 4))
    EXACT = False


def check(text):
    """Return list of (lineno, message). Empty list = valid."""
    errs = []
    lines = text.splitlines()
    if not lines or not lines[0].startswith("#a1"):
        errs.append((1, "missing '#a1' header"))
    for i, raw in enumerate(lines[1:], start=2):
        if not raw.strip():
            continue
        body = raw.lstrip(" ")
        indent = len(raw) - len(body)
        # optional 'n|' label
        if "|" in body[:4] and body.split("|", 1)[0].strip().isdigit():
            body = body.split("|", 1)[1].lstrip(" ")
        if not body:
            errs.append((i, "label with no claim"))
            continue
        if body[0] not in SIGILS:
            errs.append((i, f"line must start with a sigil {sorted(SIGILS)}, got {body[0]!r}"))
        elif len(body) < 2 or body[1] != " ":
            errs.append((i, "sigil must be followed by a space"))
        if body.count('"') % 2:
            errs.append((i, "unterminated verbatim quote"))
        if raw.startswith("\t"):
            errs.append((i, "tab indent; use spaces"))
        del indent
    return errs


def measure(aish_text, english_text):
    a, e = ntok(aish_text), ntok(english_text)
    saved = (1 - a / e) * 100 if e else 0.0
    return a, e, saved


def lex(words):
    """Words costing >1 token are the only ones where abbreviating pays."""
    return sorted(((w, ntok(w)) for w in words), key=lambda x: -x[1])


def demo():
    good = '#a1 demo\n. src/a.py:12 = entry\n3| ! parse -> crash\n > fix [3]\n* never drop "NUL byte"\n'
    assert check(good) == [], check(good)
    assert check("no header\n")[0][1].startswith("missing")
    assert any("sigil" in m for _, m in check("#a1\nplain prose line\n"))
    assert any("space" in m for _, m in check("#a1\n.nospace\n"))
    assert any("verbatim" in m for _, m in check('#a1\n. broken "quote\n'))
    assert any("tab" in m for _, m in check("#a1\n\t. tabbed\n"))
    assert check("#a1\n\n. blank lines ok\n") == []
    a, e, pct = measure("a b", "a b c d")
    assert a < e and pct > 0
    assert lex(["zz", "idempotent"])[0][1] >= 1
    print("ok (exact tokens)" if EXACT else "ok (estimated tokens; pip install tiktoken)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if cmd == "demo":
        demo()
    elif cmd == "check":
        bad = 0
        for p in sys.argv[2:]:
            errs = check(open(p, encoding="utf-8").read())
            for ln, m in errs:
                print(f"{p}:{ln}: {m}")
            bad += len(errs)
        print(f"{'FAIL' if bad else 'OK'}: {bad} problem(s)")
        sys.exit(1 if bad else 0)
    elif cmd == "measure":
        ap, ep = sys.argv[2], sys.argv[3]
        a, e, pct = measure(open(ap, encoding="utf-8").read(), open(ep, encoding="utf-8").read())
        note = "" if EXACT else "  (estimated; pip install tiktoken for exact)"
        print(f"{ap}: {a} tok\n{ep}: {e} tok\nsaved: {pct:.0f}%{note}")
    elif cmd == "lex":
        for w, n in lex(sys.argv[2:]):
            print(f"{n}  {w}{'   <- abbreviating pays' if n > 1 else ''}")
    else:
        print(__doc__)
        sys.exit(2)
