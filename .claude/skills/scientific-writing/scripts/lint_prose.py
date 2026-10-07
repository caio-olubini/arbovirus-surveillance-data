#!/usr/bin/env python3
"""Lexical checker for the scientific-writing skill.

Usage:
    python3 lint_prose.py DRAFT_FILE [--allow word1,word2] [--json]
    cat draft.md | python3 lint_prose.py - [--allow ...]

Exit code 1 if any hard fail is found, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from dataclasses import dataclass, asdict

ABBREVIATIONS = [
    "e.g.", "i.e.", "et al.", "Fig.", "Figs.", "Eq.", "Eqs.", "Ref.", "Refs.",
    "vs.", "approx.", "ca.", "cf.", "No.", "Vol.", "Suppl.", "Sect.", "Dr.",
    "doi:",
]

ANNOUNCEMENT = [
    r"in this (section|paper|study|article|work|chapter),? we (will )?(describe|present|discuss|outline|introduce|show|explore)",
    r"this (section|chapter) (describes|presents|discusses|outlines|introduces)",
    r"\bwe (now )?turn (now )?to\b",
    r"\blet us\b",
    r"\bit is (worth|important to) (noting|note|mention|mentioning|emphasi[sz]e|emphasi[sz]ing)\b",
    r"\bit should be (noted|emphasi[sz]ed|mentioned)\b",
    r"\bit is (crucial|essential|important) to (note|recogni[sz]e|understand|highlight)\b",
    r"\bas (mentioned|noted|discussed|stated|described) (above|earlier|previously|before)\b",
    r"^(importantly|notably|interestingly|crucially|significantly|remarkably),",
    r"\bthe following (section|paragraph)s? (will )?(describe|present|discuss)",
    r"\bbelow,? we (describe|present|outline)\b",
    r"\bwhat follows\b",
]

STOCK_LLM = [
    r"\bdelv(e|es|ed|ing)\b", r"\btapestry\b", r"\brealm\b", r"\btestament to\b",
    r"\bunderscor(e|es|ed|ing)\b", r"\bshed(s|ding)? (new )?light\b",
    r"\bpav(e|es|ed|ing) the way\b", r"\bnavigat(e|es|ing) the (complex|landscape|challenges)",
    r"\bintricate\b", r"\bmultifaceted\b", r"\bholistic\b", r"\bsynerg(y|ies|istic)\b",
    r"\bharness(es|ed|ing)?\b", r"\bunlock(s|ed|ing)?\b", r"\bembark(s|ed|ing)?\b",
    r"\belevat(e|es|ed|ing)\b", r"\bfoster(s|ed|ing)?\b",
    r"\bplays? an? (crucial|key|pivotal|vital|central|important|significant) role\b",
    r"\bin the (realm|landscape|era|world) of\b", r"\bever-(evolving|changing|growing)\b",
    r"\bin today'?s\b", r"\bit is clear that\b", r"\bat the heart of\b",
    r"\b(a )?double-edged sword\b", r"\bgame[- ]chang(er|ing)\b", r"\bparadigm shift\b",
    r"\bbridg(e|es|ing) the gap\b", r"\bhighlight(s|ed|ing)? the (importance|need|potential)\b",
    r"\brich (insights?|understanding)\b", r"\bvaluable insights?\b", r"\bkey insights?\b",
    r"\bnuanced\b", r"\blandscape\b",
]

INTENSIFIERS = [
    "robust", "robustly", "novel", "comprehensive", "comprehensively", "groundbreaking",
    "unprecedented", "cutting-edge", "state-of-the-art", "crucial", "pivotal",
    "paramount", "vital", "seamless", "seamlessly", "revolutionary", "remarkable",
    "remarkably", "invaluable", "significant", "significantly", "powerful",
    "innovative", "transformative", "rigorous", "rigorously", "extensive",
]

HEDGES = [
    "may", "might", "could", "possibly", "potentially", "perhaps", "probably",
    "likely", "seem", "seems", "seemingly", "appear", "appears", "apparently",
    "suggest", "suggests", "somewhat", "arguably", "presumably", "conceivably",
    "plausibly", "tend", "tends",
]

TEMPLATE_TRANSITIONS = ["furthermore", "moreover", "additionally", "in addition", "what is more", "besides"]
CLOSING_TEMPLATES = [
    r"\bin conclusion\b", r"\bin summary\b", r"\bto summari[sz]e\b", r"\bto sum up\b",
    r"\ball in all\b", r"\bultimately,", r"\btaken together,", r"\boverall,",
]


@dataclass
class Finding:
    level: str
    rule: str
    text: str
    paragraph: int


def protect_abbrev(text: str) -> str:
    for abbr in ABBREVIATIONS:
        text = text.replace(abbr, abbr.replace(".", "\u2024"))
    return text


def split_paragraphs(text: str) -> list[str]:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    return [p for p in paras if not re.match(r"^#{1,6}\s", p)]


def split_sentences(paragraph: str) -> list[str]:
    protected = protect_abbrev(paragraph.replace("\n", " "))
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'\u2018\u201c])", protected)
    return [p.replace("\u2024", ".").strip() for p in parts if p.strip()]


def words(s: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", s)


def snippet(s: str, start: int, end: int, pad: int = 40) -> str:
    a, b = max(0, start - pad), min(len(s), end + pad)
    return ("…" if a else "") + s[a:b].strip() + ("…" if b < len(s) else "")


def lint(text: str, allow: set[str]) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    paragraphs = split_paragraphs(text)
    all_sentences: list[str] = []
    total_words = sum(len(words(p)) for p in paragraphs)
    transition_budget = max(1, total_words // 400)
    transition_hits = 0
    para_sentence_counts = []
    openers = []

    for pi, para in enumerate(paragraphs, start=1):
        is_list = bool(re.match(r"^\s*([-*\u2022]|\d+[.)])\s+", para, flags=re.M))
        if is_list:
            findings.append(Finding("soft", "S6 bullets where prose is expected", para.splitlines()[0][:80], pi))

        for m in re.finditer(r"\u2014|\s--\s|(?<=[A-Za-z])\s-\s(?=[A-Za-z])|(?<!\d)\u2013(?!\d)", para):
            findings.append(Finding("hard", "H1 dash used as punctuation", snippet(para, m.start(), m.end()), pi))

        sentences = split_sentences(para)
        para_sentence_counts.append(len(sentences))
        all_sentences.extend(sentences)
        para_transitions = 0

        for si, sent in enumerate(sentences):
            low = sent.lower()
            for pat in ANNOUNCEMENT:
                for m in re.finditer(pat, low, flags=re.M):
                    findings.append(Finding("hard", "H2 announcement / meta-commentary", snippet(sent, m.start(), m.end()), pi))
            for pat in STOCK_LLM:
                for m in re.finditer(pat, low):
                    if m.group(0).strip() in allow:
                        continue
                    findings.append(Finding("hard", "H6 stock LLM phrasing", snippet(sent, m.start(), m.end()), pi))

            toks = [w.lower() for w in words(sent)]
            hedge_hits = [t for i, t in enumerate(toks) if t in HEDGES
                          and not (t == "could" and i + 1 < len(toks) and toks[i + 1] == "not")]
            if len(hedge_hits) >= 2:
                findings.append(Finding("hard", f"H4 stacked hedging ({', '.join(hedge_hits)})", sent[:120], pi))

            for t in TEMPLATE_TRANSITIONS:
                if re.match(rf"^{t}\b", low):
                    transition_hits += 1
                    para_transitions += 1
            for pat in CLOSING_TEMPLATES:
                if re.search(pat, low):
                    findings.append(Finding("hard", "H5 template closing transition", sent[:120], pi))

            statistical = bool(re.search(r"statistic|p\s*[<=>≤]|confidence interval|\bci\b", low))
            for t in toks:
                if t in {"significant", "significantly"} and statistical:
                    continue
                if t in INTENSIFIERS and t not in allow:
                    findings.append(Finding("hard", f"H7 unsupported intensifier '{t}'", sent[:120], pi))

            if re.search(r"\bnot (only|just|merely)\b.*\bbut( also)?\b", low) or re.search(r"\bisn'?t (just|only|merely)\b", low):
                findings.append(Finding("soft", "S8 antithesis template (not only X but Y)", sent[:120], pi))
            if sent.rstrip().endswith("?"):
                findings.append(Finding("soft", "S8 rhetorical question", sent[:120], pi))
            if si == 0 and toks:
                openers.append(toks[0])

        if para_transitions >= 2:
            findings.append(Finding("hard", "H5 two template transitions in one paragraph", para[:80], pi))

        triads = re.findall(r"\b[\w-]+(?: [\w-]+){0,3}, [\w-]+(?: [\w-]+){0,3},? (?:and|or) [\w-]+", para)
        if len(triads) >= 2:
            findings.append(Finding("soft", f"S3 {len(triads)} three-item lists in one paragraph", "; ".join(t[:40] for t in triads), pi))

        if len(sentences) >= 3:
            last = sentences[-1].lower()
            if re.match(r"^(this|these|together|thus|hence|in short|in doing so|by doing so)\b", last):
                findings.append(Finding("soft", "S8 paragraph ends on a wrap-up sentence", sentences[-1][:120], pi))

    if transition_hits > transition_budget:
        findings.append(Finding("hard", f"H5 {transition_hits} sentence-initial template transitions (budget {transition_budget} for {total_words} words)", "", 0))

    lengths = [len(words(s)) for s in all_sentences if words(s)]
    stats: dict = {"words": total_words, "paragraphs": len(paragraphs), "sentences": len(lengths)}
    if len(lengths) >= 2:
        mean = statistics.mean(lengths)
        sd = statistics.pstdev(lengths)
        cv = sd / mean if mean else 0.0
        stats.update({"mean_sentence_len": round(mean, 1), "sd_sentence_len": round(sd, 1),
                      "cv_sentence_len": round(cv, 2), "shortest": min(lengths), "longest": max(lengths)})
        if len(lengths) >= 6 and cv < 0.35:
            findings.append(Finding("soft", f"S8 monotone sentence length (CV {cv:.2f} < 0.35)", "", 0))
        if len(lengths) >= 8 and min(lengths) > 12:
            findings.append(Finding("soft", "S8 no short sentence (all > 12 words)", "", 0))
    if len(para_sentence_counts) >= 3 and len(set(para_sentence_counts)) == 1:
        findings.append(Finding("soft", f"S8 every paragraph has {para_sentence_counts[0]} sentences", "", 0))
    repeated = {w for w in openers if openers.count(w) >= 3 and w not in {"the", "a", "an"}}
    for w in sorted(repeated):
        findings.append(Finding("soft", f"S8 '{w}' opens {openers.count(w)} paragraphs", "", 0))

    return findings, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="draft file, or - for stdin")
    ap.add_argument("--allow", default="", help="comma-separated terms justified by the brief")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    text = sys.stdin.read() if args.path == "-" else open(args.path, encoding="utf-8").read()
    allow = {a.strip().lower() for a in args.allow.split(",") if a.strip()}
    findings, stats = lint(text, allow)
    hard = [f for f in findings if f.level == "hard"]
    soft = [f for f in findings if f.level == "soft"]

    if args.json:
        print(json.dumps({"stats": stats, "hard": [asdict(f) for f in hard], "soft": [asdict(f) for f in soft]}, ensure_ascii=False, indent=2))
    else:
        print("stats:", ", ".join(f"{k}={v}" for k, v in stats.items()))
        print(f"hard fails: {len(hard)}")
        for f in hard:
            print(f"  [P{f.paragraph}] {f.rule}: {f.text}")
        print(f"soft flags: {len(soft)}")
        for f in soft:
            print(f"  [P{f.paragraph}] {f.rule}: {f.text}")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
