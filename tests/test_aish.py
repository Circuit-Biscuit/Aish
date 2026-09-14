#!/usr/bin/env python3
"""Aish test suite. Runs standalone: python tests/test_aish.py

No framework. Every test is a function named test_*; failures raise
AssertionError with a readable message. pytest also collects these if present.
"""
import sys, pathlib, random

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import aish  # noqa: E402

NL = chr(10)


def doc(*lines):
    return NL.join(("#a2",) + lines) + NL


# --------------------------------------------------------------- codebook ---

def test_every_predicate_is_one_token():
    """The whole design rests on this. If a tokenizer change breaks it, the
    codebook silently starts costing double and nobody notices."""
    if not aish.EXACT:
        return
    bad = {p: aish.ntok(p) for p in aish.PRED if aish.ntok(p) != 1}
    assert not bad, "multi-token predicates: " + str(bad)


def test_predicates_are_one_token_at_line_start_not_just_inline():
    """Predicates sit after a newline, so they never get a leading space.
    ' cau' is 1 token but 'cau' is 2 - measuring the wrong one hides a cost."""
    if not aish.EXACT:
        return
    for p in aish.PRED:
        assert aish.ntok(NL + p) == aish.ntok(NL) + 1, p + " costs extra at line start"


def test_two_letter_predicates_are_excluded_from_entity_ids():
    """Otherwise 'eq' as an argument reads as an undefined entity."""
    for p in aish.PRED:
        if len(p) == 2:
            assert not aish.ID(p), p + " must not be usable as an entity id"
    assert aish.ID("zz") and aish.ID("aa")
    assert not aish.ID("a") and not aish.ID("abc") and not aish.ID("A1")


def test_codebook_doc_matches_code():
    """CODEBOOK.md is generated; drift means agents disagree about predicates."""
    on_disk = (ROOT / "CODEBOOK.md").read_text(encoding="utf-8")
    assert on_disk == aish.codebook_md(), "CODEBOOK.md stale: regenerate it"


def test_no_duplicate_predicate_meanings():
    glosses = [g for _, g in aish.PRED.values()]
    assert len(glosses) == len(set(glosses)), "two predicates mean the same thing"


# -------------------------------------------------------------- validator ---

def test_accepts_a_wellformed_document():
    d = doc("zz src/auth/session.py", "bug zz loop", "use zz nil", 'key "x" mob')
    assert aish.check(d) == [], aish.check(d)


def test_rejects_missing_header():
    assert any("header" in m for _, m in aish.check("bug loop" + NL))


def test_rejects_unknown_predicate():
    assert any("unknown predicate" in m for _, m in aish.check(doc("zzz aa")))


def test_rejects_undefined_entity():
    assert any("undefined id" in m for _, m in aish.check(doc("bug qq")))


def test_rejects_unterminated_verbatim():
    assert any("quote" in m for _, m in aish.check(doc('key "oops')))


def test_rejects_duplicate_definition():
    assert any("duplicate" in m for _, m in aish.check(doc("zz a/b/c.py", "zz d/e/f.py")))


def test_comments_and_blank_lines_ignored():
    assert aish.check(doc("// note", "", "nil")) == []


def test_shared_dictionary_resolves_ids():
    """A document may reference ids defined in a separate .dict file."""
    shared = {"aa": "packages/x/y/z.ts"}
    d = doc("bug aa loop", "use aa nil")
    assert any("undefined" in m for _, m in aish.check(d)), "should fail without dict"
    assert aish.check(d, shared=shared) == [], aish.check(d, shared=shared)


# ------------------------------------------------------- lint / economics ---

def test_lint_rejects_interning_a_single_token_word():
    """Defining an id costs ~3 tokens and saves 0 if the literal is 1 token."""
    assert any("interns a 1-token" in m for _, m in aish.check(doc("zz cat", "bug zz")))


def test_lint_rejects_unused_definition():
    assert any("never used" in m for _, m in aish.check(doc("zz a/b/c/d.py", "bug loop")))


def test_lint_rejects_unprofitable_interning():
    """One use of a 2-token literal: inline is cheaper."""
    msgs = [m for _, m in aish.check(doc("zz alpha beta gamma", "bug zz"))]
    assert any("inline is cheaper" in m for m in msgs), msgs


def test_lint_accepts_profitable_interning():
    d = doc("zz packages/a/b/c/d.ts", "bug zz", "use zz nil", "own zz nil")
    assert aish.check(d) == [], aish.check(d)


def test_lint_matches_the_stated_economics_formula():
    """Property test: the lint's verdict must equal k*P > P+k for real inputs."""
    random.seed(7)
    lits = ["packages/a/b/c.ts", "alpha beta", "services/x/y/z/w.go",
            "duplicate charge", "retry wrapper thing", "a/b.py"]
    for lit in lits:
        P = aish.ntok(lit)
        for k in range(1, 6):
            uses = NL.join("use zz nil" for _ in range(k))
            d = doc("zz " + lit, uses)
            wasteful = any("waste" in m for _, m in aish.check(d))
            profitable = k * P > P + k
            assert wasteful != profitable, (
                "lint disagrees with formula for %r used %dx (P=%d)" % (lit, k, P))


def test_intern_only_suggests_profitable_entries():
    for save, g, k, P in aish.intern((ROOT / "benchmarks" / "corpus" /
                                      "session-log.md").read_text(encoding="utf-8")):
        assert k * P > P + k, "unprofitable suggestion: " + repr(g)
        assert save == k * P - (P + k)


def test_intern_finds_a_repeated_path():
    t = "see services/a/b/c.go and services/a/b/c.go again"
    assert any("services/a/b/c.go" in g for _, g, _, _ in aish.intern(t))


# ----------------------------------------------------------------- corpus ---

def _corpus():
    return sorted((ROOT / "benchmarks" / "corpus").glob("*.aish"))


def test_corpus_is_nonempty():
    assert len(_corpus()) >= 6, "corpus shrank"


def test_every_corpus_document_validates_and_is_lint_clean():
    for p in _corpus():
        errs = aish.check(p.read_text(encoding="utf-8"))
        assert errs == [], p.name + ": " + str(errs[:3])


def test_every_corpus_document_has_an_english_twin():
    for p in _corpus():
        assert p.with_suffix(".md").exists(), "no English baseline for " + p.name


def test_examples_validate_against_shared_dictionary():
    ex = ROOT / "examples"
    shared, _, errs = aish.parse((ex / "payments.dict").read_text(encoding="utf-8"),
                                 dict_only=True)
    assert errs == [], errs
    got = aish.check((ex / "payments.aish").read_text(encoding="utf-8"), shared=shared)
    assert got == [], got


def test_aish_is_denser_than_english_on_every_corpus_document():
    """The core claim. If any document regresses below parity, say so loudly."""
    for p in _corpus():
        a = aish.ntok(p.read_text(encoding="utf-8"))
        e = aish.ntok(p.with_suffix(".md").read_text(encoding="utf-8"))
        assert e > a, p.name + " is not denser than its English twin"


def test_verbatim_strings_survive_untouched():
    """Identifiers must be reproduced exactly; corrupting one to save a token
    is a bug, so any quoted string in an Aish doc must appear in the English."""
    for p in _corpus():
        ai = p.read_text(encoding="utf-8")
        en = p.with_suffix(".md").read_text(encoding="utf-8")
        for chunk in ai.split('"')[1::2]:
            assert chunk in en, p.name + ": verbatim " + repr(chunk) + " not in source"



# --------------------------------------------------------------- economics ---

def test_skill_file_stays_within_its_token_budget():
    """The skill must cost less than it saves. If SKILL.md grows, the
    break-even rises and agents that load it start losing tokens. 500 is the
    cap; the decision rule in SKILL.md is stated against it."""
    n = aish.ntok((ROOT / "SKILL.md").read_text(encoding="utf-8"))
    assert n <= 500, "SKILL.md is %d tokens; over budget, break-even rises" % n


def test_skill_threshold_is_not_optimistic():
    """SKILL.md tells agents to use Aish above some note volume. That number
    must be at or above the measured break-even, never below it."""
    import re as _re
    sk, rate, be = aish.budget(ROOT)
    txt = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    m = _re.search(r"\*\*>(\d+) tokens\*\*", txt)
    assert m, "SKILL.md no longer states a threshold"
    assert int(m.group(1)) >= be, (
        "SKILL.md claims %s tokens but break-even is %.0f" % (m.group(1), be))


def test_budget_uses_the_measured_corpus_rate():
    rate = aish.corpus_rate(ROOT)
    assert rate is not None and 0.2 < rate < 0.6, rate
    sk, r2, be = aish.budget(ROOT)
    assert r2 == rate and abs(be - sk / rate) < 1e-6


def test_core_predicates_in_skill_are_real():
    """SKILL.md lists a core subset inline so agents need not load CODEBOOK.md.
    Every one must exist, or agents emit unreadable documents."""
    txt = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    block = txt.split("## Predicates")[1].split(chr(10), 1)[1].split("Full 77")[0]
    words = [w for w in block.replace("|", " ").split() if w.isalpha()]
    unknown = [w for w in words if w not in aish.PRED and w != "conf"]
    assert not unknown, "SKILL.md lists non-existent predicates: " + str(unknown)


def test_core_predicates_cover_most_real_usage():
    """The inline core is only worth it if it covers most actual use."""
    import collections as _c
    txt = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    block = txt.split("## Predicates")[1].split(chr(10), 1)[1].split("Full 77")[0]
    core = {w for w in block.replace("|", " ").split() if w in aish.PRED}
    used = _c.Counter()
    for p in _corpus():
        for _, pred, _ in aish.parse(p.read_text(encoding="utf-8"))[1]:
            used[pred] += 1
    covered = sum(k for p, k in used.items() if p in core)
    total = sum(used.values())
    assert covered / total >= 0.85, (
        "core covers only %.0f%% of corpus predicate uses" % (100 * covered / total))


# ------------------------------------------------------------------ runner ---

def main():
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print("  pass  " + name)
        except AssertionError as ex:
            failed.append((name, ex))
            print("  FAIL  " + name + ": " + str(ex))
    print()
    mode = "exact tokens" if aish.EXACT else "ESTIMATED tokens (pip install tiktoken)"
    print("%d/%d passed  (%s)" % (len(tests) - len(failed), len(tests), mode))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
