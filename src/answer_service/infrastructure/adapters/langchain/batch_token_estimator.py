from typing import Final

from tokenizers import Regex, Tokenizer, models
from tokenizers.pre_tokenizers import Split

# Mistral averages roughly four characters per token on prose. Three is
# deliberately pessimistic: overestimating costs one extra embedding request,
# underestimating gets the batch rejected for exceeding the token limit.
CHARS_PER_TOKEN: Final[int] = 3

# Named for the placeholder it is, not the credential ruff mistakes it for.
UNKNOWN_SYMBOL: Final[str] = "<unk>"


def create_batch_token_estimator() -> Tokenizer:
    """Builds the tokenizer ``MistralAIEmbeddings`` uses to size its batches.

    Left unset, that model downloads the Mixtral tokenizer from HuggingFace on
    first use — a third-party network call in the indexing path, for a decision
    that only has to be approximately right. The field is typed as a real
    ``Tokenizer`` and validated with ``isinstance``, so a plain estimator object
    is rejected; this builds a genuine one that needs no vocabulary.

    Splitting on runs of ``CHARS_PER_TOKEN`` characters makes the encoded length
    a length estimate, which is the only thing the caller reads.
    """
    tokenizer = Tokenizer(
        models.WordLevel(vocab={UNKNOWN_SYMBOL: 0}, unk_token=UNKNOWN_SYMBOL),
    )
    tokenizer.pre_tokenizer = Split(
        pattern=Regex(f".{{1,{CHARS_PER_TOKEN}}}"),
        behavior="isolated",
    )
    return tokenizer
