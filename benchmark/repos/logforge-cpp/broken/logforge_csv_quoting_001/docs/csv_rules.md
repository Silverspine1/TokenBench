# CSV rules

The parser reads one record per input line.

- A comma separates fields only when it is outside a quoted field.
- A field may be wrapped in double quotes. Inside a quoted field, a comma is an
  ordinary character and a doubled quote (`""`) stands for one literal quote.
- The decoded value of a quoted field has its surrounding quotes removed and each
  doubled quote collapsed to a single quote.
- An unquoted field is taken verbatim, including any surrounding spaces.
- Empty fields are preserved: `a,,c` decodes to three fields `a`, ``, `c`.

Examples:

| line | decoded fields |
| --- | --- |
| `a,b,c` | `a`, `b`, `c` |
| `"Smith, John",42` | `Smith, John`, `42` |
| `"she said ""hi""",x` | `she said "hi"`, `x` |
