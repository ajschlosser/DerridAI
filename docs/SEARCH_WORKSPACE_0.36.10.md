# Search workspace contract — 0.36.10

`/search` is a native Vue workspace. The runtime remains the state/transport
owner for browser-local JSONL records, Chroma search, evidence selection, and URL
serialization, but it exposes an operation-specific Search bridge rather than HTML.

## Search scopes

- **Loaded records** searches the JSONL records already present in the browser
  workspace. Text search is local/live; metadata facets and advanced filters are
  evaluated against those records.
- **Corpus database** searches the selected Chroma corpus collection. Similarity,
  MMR, and metadata-only search remain explicit server operations. Common facets
  refine the returned semantic candidate set; advanced metadata filters are sent
  with the database request.

A researcher account is database-only. An administrator with no usable local
records and no corpus database is routed to database creation when permitted.

## Shareable state

The Search URL is the public state contract. Its compressed `ts` payload preserves
query, scope, advanced metadata filters, facet selections, sort, page/page size,
column selection, layout, MMR settings, and whether Search options are expanded.
The selected corpus database remains in the `store` query parameter.

Browser-local **Saved views** store that complete URL rather than duplicating a
second Search-state schema. **Recent searches** use the same URL form. Consequently,
opening a saved view and sharing a link exercise the same restoration path.

Saved-view names/history are intentionally browser-local in 0.36.10; the URL is
what makes a view portable between browsers and users.

## Result interpretation

Database Search receives Chroma distance and derives the same bounded proximity
signal used by the existing interface. It is presented alongside an explanation
that it is derived from vector distance and is not a probability/confidence score.
`Why this result` supplements that signal with the ranking mode and metadata fields
whose values overlap the query terms.

## Accessibility and responsive behavior

Search uses explicit headings/regions, labelled filter groups, removable filter
chips, keyboard-visible focus, native dialogs, reduced-motion handling, and a
keyboard-scrollable result table. Sticky table controls remain within the scroll
container. On narrow screens, the facet sidebar becomes a dismissible drawer; the
close button remains keyboard reachable and the overlay is not the only dismissal
mechanism.
