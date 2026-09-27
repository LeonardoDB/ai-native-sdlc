---
type: regex
target: {source: file, path: tracker.log}
match: not_contains
---
issue (update|note|edit|close)
