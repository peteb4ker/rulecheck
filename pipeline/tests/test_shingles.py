from rulecheck_pipeline import shingles


def test_identical_text_fingerprints_identically():
    a = "the active pokemon is asleep and cannot attack or retreat this turn"
    assert shingles.fingerprints(a) == shingles.fingerprints(a)


def test_case_and_punctuation_are_ignored_like_the_tokenizer():
    a = "The Active Pokemon is Asleep, and cannot attack or retreat this turn."
    b = "the active pokemon is asleep and cannot attack or retreat this turn"
    assert shingles.fingerprints(a) == shingles.fingerprints(b)


def test_shared_run_of_twelve_is_detected():
    source = "a player who is asleep may not attack or retreat until the condition ends somehow"
    reuse = "note that a player who is asleep may not attack or retreat until the condition ends"
    assert shingles.fingerprints(source) & shingles.fingerprints(reuse)


def test_paraphrase_shares_no_run():
    source = "a player who is asleep may not attack or retreat until the condition ends somehow"
    paraphrase = "Sleeping blocks attacking and retreating; it lasts until something removes it."
    assert not (shingles.fingerprints(source) & shingles.fingerprints(paraphrase))


def test_text_shorter_than_the_window_yields_nothing():
    # Eleven tokens cannot form a twelve-token run, so there is nothing to
    # collide with — short quotes are the declared-quote path's problem.
    assert shingles.fingerprints("one two three four five six seven eight nine ten eleven") == set()
    assert len(shingles.fingerprints("one two three four five six seven eight nine ten eleven twelve")) == 1


def test_fingerprints_are_salted_and_not_the_bare_hash():
    import hashlib
    run = tuple("one two three four five six seven eight nine ten eleven twelve".split())
    bare = hashlib.sha256(" ".join(run).encode()).hexdigest()[:shingles.DIGEST_CHARS]
    assert shingles.fingerprint(run) != bare


def test_digest_is_the_declared_width():
    fp = next(iter(shingles.fingerprints("one two three four five six seven eight nine ten eleven twelve")))
    assert len(fp) == shingles.DIGEST_CHARS
    assert all(c in "0123456789abcdef" for c in fp)
