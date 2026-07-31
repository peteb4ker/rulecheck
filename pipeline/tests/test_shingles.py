from rulecheck_pipeline import shingles

N = shingles.SHINGLE_TOKENS


def words(n: int) -> str:
    """n distinct words.

    Built from the constant rather than written out. Four tests here spelled
    out twelve words each, so raising the window turned them into assertions
    about the empty set instead of failing honestly.
    """
    return " ".join(f"w{i}" for i in range(n))


def test_identical_text_fingerprints_identically():
    a = "the active pokemon is asleep and cannot attack or retreat this turn"
    assert shingles.fingerprints(a) == shingles.fingerprints(a)


def test_case_and_punctuation_are_ignored_like_the_tokenizer():
    a = "The Active Pokemon is Asleep, and cannot attack or retreat this turn."
    b = "the active pokemon is asleep and cannot attack or retreat this turn"
    assert shingles.fingerprints(a) == shingles.fingerprints(b)


def test_a_shared_run_the_length_of_the_window_is_detected():
    shared = words(N)
    assert shingles.fingerprints(f"start {shared} end") & \
        shingles.fingerprints(f"different opening {shared} different close")


def test_a_shared_run_one_token_short_is_not_detected():
    """The boundary. One token below the window is the longest reuse that
    passes, which is why the transformation report says the maximum overlap
    across the corpus is set by this number and not by the writing."""
    shared = words(N - 1)
    assert not (shingles.fingerprints(f"start {shared} end")
                & shingles.fingerprints(f"other {shared} close"))


def test_paraphrase_shares_no_run():
    source = "a player who is asleep may not attack or retreat until the condition ends somehow"
    paraphrase = "Sleeping blocks attacking and retreating; it lasts until something removes it."
    assert not (shingles.fingerprints(source) & shingles.fingerprints(paraphrase))


def test_text_shorter_than_the_window_yields_nothing():
    # A text one token short of the window cannot form a run, so there is
    # nothing to collide with. Short quotes are the declared-quote path's
    # problem, not this one's.
    assert shingles.fingerprints(words(N - 1)) == set()
    assert len(shingles.fingerprints(words(N))) == 1


def test_fingerprints_are_salted_and_not_the_bare_hash():
    import hashlib
    run = tuple(words(N).split())
    bare = hashlib.sha256(" ".join(run).encode()).hexdigest()[:shingles.DIGEST_CHARS]
    assert shingles.fingerprint(run) != bare


def test_digest_is_the_declared_width():
    fp = next(iter(shingles.fingerprints(words(N))))
    assert len(fp) == shingles.DIGEST_CHARS
    assert all(c in "0123456789abcdef" for c in fp)


def test_the_window_matches_the_overlap_check():
    """These were two separate literals that had to agree by hand. The
    fingerprint path and the exact-text path must ask the same question, or
    a repository without the PDFs checks something different from CI."""
    from rulecheck_pipeline.content_check import OVERLAP_TOKENS
    assert OVERLAP_TOKENS == shingles.SHINGLE_TOKENS
