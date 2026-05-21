from typing import Literal


EntityType = Literal[
    "Technology",
    "Organization",
    "Person",
    "Paper",
    "Product",
]

RelationType = Literal[
    "BuiltWith",
    "Implements",
    "ProposedBy",
    "CompetesWith",
    "Deprecates",
    "DependsOn",
    "PublishedBy",
]
