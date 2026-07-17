class BaseDomainService:
    """Marker base class for all domain services.

    Domain services encapsulate business logic that:
    - Does not naturally belong to a single entity or aggregate.
    - Operates across multiple domain objects.
    - Represents a significant domain operation in the ubiquitous language.

    Domain services must be stateless — all required data comes from method
    parameters or injected domain ports (Protocols).
    """
