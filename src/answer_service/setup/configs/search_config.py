from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SearchConfig:
    """Relevance floors each retriever applies to its own candidates.

    Two settings rather than one because the scales are unrelated and neither is
    normalised: the dense floor is a cosine similarity, the lexical floor is a
    ``ts_rank_cd`` value. Fusion cannot do this job — Reciprocal Rank Fusion
    scores positions, so the top result of a hopeless query scores exactly as
    well as the top result of a perfect one.

    Filtering here is what makes "the catalog cannot answer this" observable at
    all. Both retrievers return their nearest matches whether or not anything is
    close, so without a floor every query looks answered and the gap report stays
    empty however badly the catalog fits its users.

    Attributes:
        dense_score_floor: Minimum cosine similarity a dense candidate needs.
        lexical_score_floor: Minimum ``ts_rank_cd`` a lexical candidate needs.
    """

    dense_score_floor: float = 0.7
    lexical_score_floor: float = 0.05
