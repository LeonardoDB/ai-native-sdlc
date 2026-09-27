---
type: regex
target: {source: file, path: tracker.log}
match: contains
---
mr note|api .*(notes|discussions)
