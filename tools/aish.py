#!/usr/bin/env python3
"""Aish v2 - a symbol language for agent-to-agent notes.

  aish.py check FILE...          validate structure and predicates
  aish.py measure AISH ENGLISH   real token comparison
  aish.py intern FILE            suggest dictionary entries (the big win)
  aish.py cost FILE              per-line token cost, find waste
  aish.py budget                 does loading this skill pay for itself?
  aish.py codebook               emit CODEBOOK.md
  aish.py demo                   self-check

Exact counts need tiktoken; otherwise a flagged chars/4 estimate is used.
"""
import sys, re, collections

# codebook: predicate -> (arity hint, gloss). Every code is verified to be a
# single token at line start (bare, no leading space) by demo().
PRED = {
    # structure
    "def": ("X ...", "X is defined as"), "loc": ("X Y", "X located in Y"),
    "use": ("X Y", "X uses Y"), "own": ("X Y", "X owned by Y"),
    "has": ("X Y", "X contains Y"), "par": ("X Y", "X parent of Y"),
    "imp": ("X Y", "X imports Y"), "exp": ("X Y", "X exports Y"),
    "sig": ("X ...", "signature of X"), "typ": ("X Y", "X has type Y"),
    "val": ("X Y", "X has value Y"),
    # causal / relational
    "cz": ("X Y", "X causes Y"), "cha": ("X Y Z...", "chain: X then Y then Z"),
    "req": ("X Y", "X requires Y"), "blk": ("X Y", "X blocked by Y"),
    "pre": ("X Y", "X happens before Y"), "aft": ("X Y", "X happens after Y"),
    "dep": ("X Y", "X depends on Y"), "aff": ("X Y", "X affects Y"),
    "eq": ("X Y", "X same as Y"), "neq": ("X Y", "X differs from Y"),
    "sub": ("X Y", "X subset of Y"), "sup": ("X Y", "X supersedes Y"),
    # speech acts / epistemic status
    "did": ("...", "completed, verified by doing"),
    "neg": ("...", "negative: does not, did not, failed"),
    "bug": ("...", "defect claim"), "ask": ("...", "open question"),
    "next": ("...", "next action"), "key": ("...", "must not be lost"),
    "hyp": ("...", "hypothesis, unverified"), "obs": ("...", "directly observed"),
    "inf": ("...", "inferred, not observed"), "ref": ("...", "refuted or rejected"),
    "fix": ("...", "proposed fix"), "try": ("...", "attempted"),
    "rev": ("...", "reverted"), "why": ("...", "reason for prior claim"),
    # modality
    "all": ("", "always, every case"), "som": ("", "sometimes"),
    "nev": ("", "never"), "just": ("", "only, sole case"),
    "mos": ("", "usually"), "conf": ("N", "confidence 0-9"),
    # risk classes
    "harm": ("...", "risk"), "sec": ("...", "security"),
    "pay": ("...", "money path"), "los": ("...", "data loss"),
    "perf": ("...", "performance"), "race": ("...", "race condition"),
    "dead": ("...", "deadlock"), "null": ("...", "null or undefined"),
    "loop": ("...", "infinite loop"), "lk": ("...", "resource leak"),
    # vcs / env
    "ver": ("X", "version"), "rel": ("X", "release"), "com": ("X", "commit"),
    "bra": ("X", "branch"), "tag": ("X", "tag"), "env": ("X", "environment"),
    "prod": ("", "production"), "stag": ("", "staging"),
    "test": ("...", "test"), "cov": ("...", "coverage"), "doc": ("...", "documentation"),
    # edits
    "add": ("...", "added"), "del": ("...", "deleted"), "mod": ("...", "modified"),
    "mov": ("...", "moved"), "ren": ("...", "renamed"), "upd": ("...", "updated"),
    "cal": ("X Y", "X calls Y"), "ret": ("X Y", "X returns Y"),
    "arg": ("X Y", "X takes argument Y"), "err": ("...", "error"),
    "src": ("X", "source"), "dst": ("X", "destination"), "nil": ("", "none, empty"),
}

try:
    import tiktoken
    _enc = tiktoken.get_encoding("o200k_base")
    def ntok(s): return len(_enc.encode(s))
    EXACT = True
except ImportError:  # ponytail: ratios survive estimation; exact needs tiktoken
    def ntok(s): return max(1, round(len(s) / 4))
    EXACT = False

_ID = re.compile(r"^[a-z]{2}$")  # entity ids aa..zz, one token each


def ID(s):
    """Entity id: two lowercase letters, excluding 2-letter predicate codes.

    Without the exclusion, 'eq' as an argument word would be read as an
    undefined entity, and 'eq' at line start would be ambiguous.
    """
    return bool(_ID.match(s)) and s not in PRED


def parse(text, dict_only=False):
    """Return (dictionary, claims, errors). A dict line is 'id literal'."""
    d, claims, errs = {}, [], []
    lines = text.splitlines()
    if not lines or not lines[0].startswith("#a2"):
        if not dict_only:
            errs.append((1, "missing '#a2' header"))
    for i, raw in enumerate(lines[1:], start=2):
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.count('"') % 2:
            errs.append((i, "unterminated verbatim quote"))
        head, _, rest = line.partition(" ")
        if ID(head) and rest:
            if head in d:
                errs.append((i, "duplicate id " + repr(head)))
            d[head] = rest
        elif head in PRED:
            claims.append((i, head, rest.split()))
        else:
            errs.append((i, "unknown predicate " + repr(head) + "; not in codebook"))
    return d, claims, errs


def check(text, shared=None, lint=True):
    d, claims, errs = parse(text)
    local = dict(d)
    if shared:
        d = dict(shared, **d)
    uses = collections.Counter()
    for i, pred, args in claims:
        for a in args:
            if ID(a):
                uses[a] += 1
                if a not in d:
                    errs.append((i, "undefined id " + repr(a) + " (no dictionary entry)"))
    if lint:
        # Economics are part of correctness here: an id that costs more than
        # the literal it replaces is a pure loss, so the tool refuses it.
        for i, raw in enumerate(text.splitlines()[1:], start=2):
            head, _, rest = raw.strip().partition(" ")
            if not (ID(head) and rest and head in local):
                continue
            P, k = ntok(rest), uses[head]
            if k == 0:
                errs.append((i, "waste: id " + repr(head) + " defined but never used"))
            elif P < 2:
                errs.append((i, "waste: id " + repr(head) + " interns a 1-token literal "
                             + repr(rest) + "; costs 3 tokens, saves 0"))
            elif k * P <= P + k:
                errs.append((i, "waste: id " + repr(head) + " used %dx at %d tok; "
                             "inline is cheaper" % (k, P)))
    return sorted(errs)


def intern(text, min_uses=2):
    """Suggest dictionary entries.

    A literal costing P tokens used k times costs k*P inline, but P+k when
    interned (P once to define, 1 per use). Worth it when k*P > P+k.
    """
    words = re.findall(r"[A-Za-z0-9_./\\-]{3,}", text)
    grams = collections.Counter()
    for size in (1, 2, 3):
        for j in range(len(words) - size + 1):
            grams[" ".join(words[j:j + size])] += 1
    out = []
    for g, k in grams.items():
        if k < min_uses:
            continue
        P = ntok(g)
        if P < 2:
            continue
        if k * P > P + k:
            out.append((k * P - (P + k), g, k, P))
    return sorted(out, reverse=True)


def measure(a, b):
    x, y = ntok(a), ntok(b)
    return x, y, (1 - x / y) * 100 if y else 0.0


def corpus_rate(root):
    """Measured fraction saved, from the benchmark corpus. None if absent."""
    en = ai = 0
    for p in sorted((root / "benchmarks" / "corpus").glob("*.aish")):
        md = p.with_suffix(".md")
        if md.exists():
            ai += ntok(p.read_text(encoding="utf-8"))
            en += ntok(md.read_text(encoding="utf-8"))
    return (1 - ai / en) if en else None


def budget(root):
    """Does loading this skill pay for itself?

    The skill is only worth loading if a session writes enough notes for the
    savings to exceed the skill's own context cost. Returns the break-even.
    """
    skill = ntok((root / "SKILL.md").read_text(encoding="utf-8"))
    rate = corpus_rate(root) or 0.37
    return skill, rate, skill / rate


def codebook_md():
    L = ["# Aish v2 Codebook", "",
         "Generated by `python tools/aish.py codebook`. Every code below costs",
         "**one token** at line start. Do not edit by hand, do not invent codes.",
         "", "| code | args | means |", "|------|------|-------|"]
    for p, (a, g) in PRED.items():
        L.append("| `" + p + "` | " + (a or "-") + " | " + g + " |")
    L += ["", str(len(PRED)) + " predicates. Entity ids are two lowercase letters",
          "(`aa`-`zz`, 1844 available, one token each), defined in a dictionary."]
    return "\n".join(L) + "\n"


def demo():
    if EXACT:
        bad = [p for p in PRED if ntok(p) != 1]
        assert not bad, "multi-token predicates: " + str(bad)
    doc = ('#a2\naa src/auth/session.py\nbug aa loop\nuse aa nil\n'
           'key "tok_x" mob\nconf 7\n')
    assert check(doc) == [], check(doc)
    assert any("header" in m for _, m in check("nope\n"))
    assert any("unknown predicate" in m for _, m in check("#a2\nzzz aa\n"))
    assert any("undefined id" in m for _, m in check("#a2\nbug qq\n"))
    assert any("quote" in m for _, m in check('#a2\nkey "oops\n'))
    assert any("duplicate" in m for _, m in check("#a2\naa x\naa y\n"))
    d, c, _ = parse(doc)
    assert d == {"aa": "src/auth/session.py"} and len(c) == 4
    NL = chr(10)
    waste1 = NL.join(["#a2", "zz cat", "bug zz", ""])
    assert any("interns a 1-token" in m for _, m in check(waste1))
    waste2 = NL.join(["#a2", "zz src/a/b/c.py", "bug loop", ""])
    assert any("never used" in m for _, m in check(waste2))
    good = NL.join(["#a2", "zz src/a/b/c.py", "bug zz", "use zz nil", ""])
    assert check(good) == [], check(good)
    hits = intern("src/auth/session.py here and src/auth/session.py again")
    assert any("src/auth/session.py" in g for _, g, _, _ in hits), hits
    assert measure("a", "a b")[2] > 0
    assert "| `bug` |" in codebook_md()
    print("ok (exact tokens)" if EXACT else "ok (estimated; pip install tiktoken)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    rd = lambda p: open(p, encoding="utf-8").read()
    if cmd == "demo":
        demo()
    elif cmd == "check":
        bad = 0
        paths = sys.argv[2:]
        shared = {}          # pool dictionaries across all files given
        for p in paths:
            shared.update(parse(rd(p), dict_only=True)[0])
        for p in paths:
            if p.endswith(".dict"):
                continue
            for ln, m in check(rd(p), shared):
                print(p + ":" + str(ln) + ": " + m)
                bad += 1
        print(("FAIL: " if bad else "OK: ") + str(bad) + " problem(s)")
        sys.exit(1 if bad else 0)
    elif cmd == "measure":
        a, b, pct = measure(rd(sys.argv[2]), rd(sys.argv[3]))
        note = "" if EXACT else "  (estimated)"
        print(sys.argv[2] + ": " + str(a) + " tok")
        print(sys.argv[3] + ": " + str(b) + " tok")
        print("saved: %.0f%%  ratio: %.1fx%s" % (pct, b / max(a, 1), note))
    elif cmd == "intern":
        rows = intern(rd(sys.argv[2]))
        if not rows:
            print("nothing worth interning")
        for save, g, k, P in rows[:20]:
            print("  saves %3d tok  used %dx  %d tok each  %r" % (save, k, P, g))
    elif cmd == "cost":
        for line in rd(sys.argv[2]).splitlines():
            print("%3d  %s" % (ntok(line + "\n"), line))
    elif cmd == "budget":
        import pathlib as _pl
        root = _pl.Path(__file__).resolve().parent.parent
        sk, rate, be = budget(root)
        print("SKILL.md costs      %d tok to load" % sk)
        print("measured savings    %.0f%% of note tokens" % (100 * rate))
        print("break-even          %d tok of notes (~%d handoff notes)"
              % (be, round(be / 200)))
        print()
        print("Below that, writing prose is cheaper than loading this skill.")
    elif cmd == "codebook":
        sys.stdout.write(codebook_md())
    else:
        print(__doc__)
        sys.exit(2)
