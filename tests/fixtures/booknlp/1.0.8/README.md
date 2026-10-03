<!-- Copyright 2026 Aaron John Schlosser, PhD. -->

# BookNLP 1.0.8 consumer fixtures

These fixtures describe the narrow upstream shapes that DerridAI's BookNLP adapter consumes. They are adapter fixtures, not BookNLP conformance tests and not evidence that BookNLP itself is correct.

Keep assertions focused on DerridAI-owned normalization: stable cluster identity, alias projection, source offsets/lemmas, and fields intentionally omitted from the provider-neutral contract. Compatibility with the installed third-party package belongs in a small integration smoke test rather than duplicated schema assertions.
