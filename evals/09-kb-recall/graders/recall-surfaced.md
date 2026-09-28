---
type: llm
focus: last_message
---
Grade each claim true/false; pass only if all are true.
- It presents a spec for free shipping from 100 and asks for approval before building.
- It surfaces the money-is-Decimal decision (ADR 0001, INC-12) as a constraint on the design — for example the threshold compared as `Decimal("100")` — or flags the existing float/int code as conflicting with it.
