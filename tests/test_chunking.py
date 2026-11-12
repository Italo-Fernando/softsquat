import random

import pytest

from softsquat.services.attach_service import chunk_text

SIZE = 100
OVERLAP = 20
GIANT = 5000


def make_text(words: int, seed: int = 7) -> str:
    rng = random.Random(seed)
    vocabulary = [
        ''.join(rng.choices('abcdefghij', k=rng.randint(2, 11))) for _ in range(60)
    ]
    return ' '.join(rng.choice(vocabulary) for _ in range(words))


def test_text_without_whitespace_keeps_hard_cut_behaviour():
    chunks = chunk_text('a' * 900)

    assert [len(chunk) for chunk in chunks] == [800, 250]


def test_short_text_is_a_single_chunk():
    assert chunk_text('hello world') == ['hello world']


@pytest.mark.parametrize('text', ['', '   ', '\n\n\t'])
def test_blank_text_produces_no_chunks(text):
    assert chunk_text(text) == []


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError, match='overlap'):
        chunk_text('some text', size=10, overlap=10)


def test_chunks_never_exceed_size():
    chunks = chunk_text(make_text(400), size=SIZE, overlap=OVERLAP)

    assert chunks
    assert all(len(chunk) <= SIZE for chunk in chunks)


def test_chunks_never_cut_words_in_half():
    text = make_text(400)
    original_words = set(text.split())

    chunks = chunk_text(text, size=SIZE, overlap=OVERLAP)

    chunk_words = {word for chunk in chunks for word in chunk.split()}
    assert chunk_words <= original_words


def test_no_words_are_lost():
    text = make_text(400)

    chunks = chunk_text(text, size=SIZE, overlap=OVERLAP)

    assert {word for chunk in chunks for word in chunk.split()} == set(text.split())


def test_consecutive_chunks_overlap():
    chunks = chunk_text(make_text(400), size=SIZE, overlap=OVERLAP)

    for previous, current in zip(chunks, chunks[1:]):
        assert current.split()[0] in previous.split()


def test_prefers_paragraph_boundary():
    first = ' '.join(['alpha'] * 10)
    second = ' '.join(['bravo'] * 10)

    chunks = chunk_text(f'{first}\n\n{second}', size=SIZE, overlap=OVERLAP)

    assert chunks[0] == first


def test_prefers_sentence_boundary_over_word_boundary():
    text = 'The first sentence ends here. The second one keeps going for a good while'

    chunks = chunk_text(text, size=40, overlap=10)

    assert chunks[0] == 'The first sentence ends here.'


def test_giant_token_is_hard_cut_and_terminates():
    chunks = chunk_text('x' * GIANT, size=SIZE, overlap=OVERLAP)

    assert all(len(chunk) <= SIZE for chunk in chunks)
    assert sum(len(chunk) for chunk in chunks) >= GIANT
