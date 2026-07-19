"""What a good answer looks like, written down so it can be measured.

Every entry is a question a real person might type, paired with the catalog
entry that ought to answer it. None of them repeats the wording of the FAQ:
asking the catalog its own questions measures string matching, not retrieval,
and would pass however badly the embedding model performed.

The off-topic set matters just as much. Nearest-neighbour search always returns
neighbours, and OR-ed full-text search matches on a single shared word, so
"answer nothing" is a behaviour that has to be asserted rather than assumed. It
is also what the gap report is built on: a question recorded as answered never
reaches the backlog it belongs in.
"""

from typing import Final

# (what a user types, which pair should answer it)
PARAPHRASED: Final[tuple[tuple[str, str], ...]] = (
    ("I forgot my password and cannot log in", "FAQ-0001"),
    ("my sign-in link never showed up", "FAQ-0001"),
    ("I want to use a different email address", "FAQ-0002"),
    ("can my teammate use the same login", "FAQ-0003"),
    ("close my account for good", "FAQ-0004"),
    ("do you take american express", "FAQ-0005"),
    ("when do you take the money", "FAQ-0006"),
    ("I need a receipt for accounting", "FAQ-0007"),
    ("my card was declined, what now", "FAQ-0009"),
    ("I want to pay yearly instead of monthly", "FAQ-0010"),
    ("how many days until my parcel arrives", "FAQ-0011"),
    ("do you send things abroad", "FAQ-0012"),
    ("where is my package right now", "FAQ-0013"),
    ("I typed the wrong street, can it be fixed", "FAQ-0014"),
    ("my delivery never turned up", "FAQ-0015"),
    ("how do I send something back", "FAQ-0017"),
    ("how long until I see the money again", "FAQ-0018"),
    ("who pays the postage when I send it back", "FAQ-0019"),
    ("I would rather swap it for another size", "FAQ-0020"),
    ("does this work in safari", "FAQ-0021"),
    ("can I pull my data out programmatically", "FAQ-0022"),
    ("I want a copy of everything I have stored", "FAQ-0023"),
    ("can I turn on 2fa", "FAQ-0024"),
    ("sign me out of all my other devices", "FAQ-0025"),
    ("hand the account over to someone else", "FAQ-0027"),
    ("I changed my mind about the yearly plan", "FAQ-0028"),
    ("my card expired, where do I put the new one", "FAQ-0029"),
    ("we are a charity, is there a cheaper rate", "FAQ-0030"),
    ("nobody will be in when it arrives", "FAQ-0032"),
    ("can it go to a locker instead of my house", "FAQ-0033"),
    ("it turned up smashed", "FAQ-0035"),
    ("how many requests am I allowed", "FAQ-0037"),
    ("I would rather be notified than keep asking", "FAQ-0038"),
    ("is my information kept safe", "FAQ-0039"),
    ("what kind of spreadsheet can I upload", "FAQ-0040"),
)

# Questions this catalog genuinely cannot answer. Each is a gap report entry,
# and answering any of them from an unrelated pair is worse than saying nothing.
OFF_TOPIC: Final[tuple[str, ...]] = (
    "what is the boiling point of mercury",
    "who won the world cup in 1998",
    "how do I bake sourdough bread",
    "what time does the museum close",
    "translate good morning into japanese",
    "how many kilometres to the moon",
    "recommend a film for tonight",
    "what is the capital of peru",
)

# Minimum share of PARAPHRASED that must rank its pair first, and within top 3.
# Set from the measured baseline, not from ambition: a regression suite that has
# never passed teaches nobody anything.
MIN_TOP_1: Final[float] = 0.70
MIN_TOP_3: Final[float] = 0.85

# Share of OFF_TOPIC that must come back empty.
MIN_REFUSED: Final[float] = 0.75
