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

    A cosine similarity is a property of the embedding model: 0.7 means roughly
    the same closeness whether the catalog holds twenty pairs or twenty million,
    so an absolute floor keeps its meaning as the corpus grows.

    The default is nonetheless a guess, and there is no test that can tell you
    it is wrong — a badly set floor does not fail, it silently refuses questions
    the catalog could have answered. Until served queries carry a "did this
    help" label, the honest way to check it is to watch ``unanswered_rate`` on
    ``/v1/statistics/`` and read ``/v1/statistics/unanswered``: sensible
    on-topic questions in that list mean the floor is too high, junk means it is
    doing its job.

    ``ts_rank_cd`` is not such a property. Its value rises with the number of
    matched terms and the length of the document, so one pair scored 1.4 for the
    query "orders" and 3.2 for "how do I track my order" — a 2.3x difference from
    query length alone, on an identical match. No absolute number separates a
    good match from a bad one across queries like that, and normalising does not
    rescue it: the bounded variant still moved from 0.58 to 0.76 on that pair.
    The lexical side is therefore filtered *relative to the best match for its
    own query*, which normalises itself and needs no calibration at any size.

    Attributes:
        dense_score_floor: Minimum cosine similarity a dense candidate needs.
        lexical_relative_floor: Fraction of the best ``ts_rank_cd`` in the same
            result set a lexical candidate must reach. ``0.0`` keeps everything
            the tsquery matched; ``1.0`` keeps only joint winners.
    """

    dense_score_floor: float = 0.7
    lexical_relative_floor: float = 0.35
