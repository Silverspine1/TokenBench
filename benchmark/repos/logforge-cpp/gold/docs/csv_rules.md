# CSV rules

The parser reads one record per input line.

- A comma separates fields only when it is outside a quoted field.
- A double quote opens a quoted field **only when it is the first character of
  that field**. A quote that appears anywhere else in a field is an ordinary
  character with no special meaning. So `ab"c"d` is the literal text `ab"c"d`
  (not a quoted field), and the comma in `a"b,c` still splits, giving `a"b` and
  `c`.
- Inside a quoted field, a comma is an ordinary character and a doubled quote
  (`""`) stands for one literal quote.
- The decoded value of a quoted field has its surrounding quotes removed and each
  doubled quote collapsed to a single quote. If a quoted field has trailing text
  after its closing quote (`"a"b`), that text is appended to the decoded value
  literally, giving `ab`.
- An unquoted field is taken verbatim, including any surrounding spaces.
- Empty fields are preserved: `a,,c` decodes to three fields `a`, ``, `c`.

Examples:

| line | decoded fields |
| --- | --- |
| `a,b,c` | `a`, `b`, `c` |
| `"Smith, John",42` | `Smith, John`, `42` |
| `"she said ""hi""",x` | `she said "hi"`, `x` |
| `ab"c"d,x` | `ab"c"d`, `x` |
| `a"b,c` | `a"b`, `c` |
