from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SearchConfig:
    """Relevance floors each retriever applies to its own candidates.

    Filtering here is what makes "the catalog cannot answer this" observable at
    all. Both retrievers return their nearest matches whether or not anything is
    close, so without a floor every query looks answered and the gap report stays
    empty however badly the catalog fits its users. Fusion cannot do this job —
    Reciprocal Rank Fusion scores positions, so the top result of a hopeless
    query scores exactly as well as the top result of a perfect one.

    The two retrievers are filtered on different principles, because their scores
    mean different things.

    A cosine similarity is a property of the embedding model: 0.64 means roughly
    the same closeness whether the catalog holds twenty pairs or twenty million,
    so an absolute floor keeps its meaning as the corpus grows. The default is
    the measured crossover on ``tests/quality/dataset.py``, whose 35 paraphrased
    questions and 8 unanswerable ones are labelled by hand: on-topic pairs scored
    0.6253 to 0.8227 and the best any off-topic query reached was 0.6307. The two
    distributions overlap by 0.005, so no floor separates them perfectly, and
    0.64 is the value that costs one on-topic question to refuse all eight
    off-topic ones. Raising it buys nothing — 0.70 refused the same eight and
    lost nine more real questions.

    ``ts_rank_cd`` is not such a property. Its value rises with the number of
    matched terms and the length of the document, so one pair scored 1.4 for the
    query "orders" and 3.2 for "how do I track my order" — a 2.3x difference from
    query length alone, on an identical match. No absolute number *ranks*
    reliably across queries like that, which is why the lexical side is filtered
    relative to the best match for its own query.

    A relative floor alone cannot refuse, though: it compares each candidate to
    the best in its own set, so the best always scores 1.0 and survives every
    setting from 0.0 to 1.0. When a query matches nothing meaningful, that
    winner is junk and is served as an answer. ``lexical_absolute_floor`` is what
    supplies the missing "and the best is itself good enough", and it is a
    threshold rather than a ranking, so ``ts_rank_cd``'s incomparability across
    queries does not apply.

    Its default is a weight boundary rather than a tuning knob. The search vector
    weights the question ``A`` and the answer ``B``, which ``ts_rank_cd`` scores
    1.0 and 0.4, so 0.5 admits exactly the matches that touched the question text
    and rejects those that only brushed a word of the answer prose. Every
    off-topic query measured leaked through at precisely 0.4 — "what time does
    the museum close" matched five unrelated pairs, all tied, all served.

    The floors decide which candidates compete. ``dense_weight`` and
    ``lexical_weight`` decide how much each retriever's opinion counts once they
    do, by scaling its ``1 / (k + rank)`` contribution to the fused score. They
    are not interchangeable with the floors: no floor can reorder a candidate
    that passed it, and lowering one to suppress a retriever would delete its
    recall rather than discount its ranking.

    Weighting is needed because lexical terms are OR-ed, so a pair sharing one
    word of a natural question competes on equal footing with the pair the
    embedding model ranked first. Measured on the quality set, that cost top-1
    accuracy outright: the pair a human labelled correct held the highest cosine
    in the result set and still came third, behind two pairs that merely shared
    vocabulary.

    The default 2:1 is swept rather than chosen. Top-1 accuracy over the 35
    labelled paraphrases ran 69% at 1:1, 77% at 1.5, and 80% from 2.0 onwards —
    3.0 and 5.0 measured identically, so 2.0 is the smallest ratio that reaches
    the plateau, and the one that leaves the lexical side the most say it can
    have without costing accuracy. Refusals were unaffected throughout, which is
    the expected shape: weighting reorders candidates that already cleared their
    floors and cannot admit one that did not.

    Attributes:
        dense_score_floor: Minimum cosine similarity a dense candidate needs.
        lexical_relative_floor: Fraction of the best ``ts_rank_cd`` in the same
            result set a lexical candidate must reach. ``0.0`` keeps everything
            the tsquery matched; ``1.0`` keeps only joint winners. Orders the
            survivors; it cannot empty the set.
        lexical_absolute_floor: Minimum ``ts_rank_cd`` any lexical candidate
            needs regardless of its neighbours. ``0.0`` restores the previous
            behaviour, where no query was ever lexically unanswerable.
        dense_weight: Multiplier on each dense candidate's fused contribution.
        lexical_weight: Multiplier on each lexical candidate's fused
            contribution. Only the ratio between the two matters; equal values
            are plain RRF.
    """

    dense_score_floor: float = 0.64
    lexical_relative_floor: float = 0.35
    lexical_absolute_floor: float = 0.5
    dense_weight: float = 2.0
    lexical_weight: float = 1.0
