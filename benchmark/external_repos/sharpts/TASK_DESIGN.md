# SharpTS — Bug-Fix Task Design

Target repo: `SharpTS` (TypeScript interpreter + IL compiler in C#, net10.0).
Pinned checkout: `benchmark/external_repos/sharpts/cache/.git_clone`
Black-box surface for hidden tests: `sharpts prog.ts` (tree-walking interpreter), assert stdout.

---

## 1. Verified Harness

### Build (run ONCE; restore is offline/cached)
```
# PowerShell: prepend dotnet to PATH first
$env:Path = "C:\Program Files\dotnet;" + $env:Path
# from the clone dir:
dotnet build SharpTS.csproj -c Release -p:MinVerVersionOverride=0.0.0-tb --nologo -v quiet
```
- Output DLL: `<clone>\bin\Release\net10.0\SharpTS.dll`
- Observed build time: ~9-12 s (warm NuGet cache, incremental ~9 s).
- "Build succeeded. 0 Warning(s) 0 Error(s)".

### Run a program (interpreter path)
```
dotnet <clone>\bin\Release\net10.0\SharpTS.dll path\to\prog.ts
```
- Per-run wall time observed: ~0.19-0.28 s (cold JIT of the runtime; steady-state similar).
- console.log writes to **stdout**, one line per call, each terminated by a newline
  (verified: two `console.log` calls → exactly `A\nB\n`, no extra blank line, no missing trailing newline).

### QUIRKS THAT ARE LOAD-BEARING FOR TEST DESIGN

1. **SharpTS runs a STATIC TYPE CHECKER before execution.** A type error rejects the
   whole program (nothing runs) and the message is `Error: Type Error at line N: ...`,
   **exit code 1**, printed to stdout/stderr.
   - Example: `"3" * 2` → `Error: Type Error at line N: Operands must be numbers...` exit 1.
   - Example: `[1,2,3].indexOf("2")` → `Type Error ... Argument 1 expected type '1 | 2 | 3' but got '"2"'.` exit 1.
   - **CONSEQUENCE:** every `.ts` check program must be TYPE-VALID. Use `: any`,
     `as any`, or `: number[]` / explicit annotations to dodge literal-union narrowing
     when you intentionally feed "wrong" types. Heterogeneous arrays need an explicit
     type (e.g. `const a: any[] = [...]`).

2. **A guest RUNTIME error does NOT change the exit code.** An uncaught throw /
   runtime TypeError prints `Runtime Error: <message>` to **stdout** and the process
   **still exits 0**.
   - `undefined.foo.bar` → stdout line `Runtime Error: TypeError: Cannot read properties of undefined (reading 'foo')`, **exit 0**.
   - `throw new Error("explicit boom")` → stdout line `Runtime Error: [object Error]`, **exit 0**
     (note: uncaught Error stringifies to `[object Error]`, NOT the message; but inside
     `catch (e:any) { e.message }` the message is correct → `"boom"`).
   - **CONSEQUENCE for hidden tests:** to assert "should error", DO NOT rely on a nonzero
     exit code. Instead assert that stdout CONTAINS `Runtime Error:` (and/or that the
     pre-error console.log lines are present but the post-error ones are absent). To assert
     "should NOT error", assert the full expected stdout with no `Runtime Error:` line.
   - Type errors (category 1) DO exit 1; runtime errors (category 2) exit 0. Keep these
     two failure modes distinct in test assertions.

3. **Number formatting is mostly JS-correct but DIVERGES in the exponential range.**
   `console.log` / string concat / template / array join all route through the same
   `Stringify` (Interpreter.Operators.cs ~L949). Verified:
   - Integers and normal decimals: JS-correct. `5`→`5`, `5.0`→`5`, `5.5`→`5.5`,
     `100/4`→`25`, `123456789`→`123456789`, `10/3`→`3.3333333333333335`,
     `0.1+0.2`→`0.30000000000000004`.
   - `1/0`→`Infinity`, `-1/0`→`-Infinity`, `0/0`→`NaN`. `-0`→`-0`.
   - **DIVERGENT (avoid in expected-output unless you target this):** very large/small
     numbers use .NET `double.ToString()`, not JS: `1e21`→`1E+21` (JS `1e+21`),
     `0.000001`→`1E-06` (JS `0.000001`), `0.0000001`→`1E-07` (JS `1e-7`).
     **Keep test numbers in the "normal" range (no scientific notation) so expected
     stdout is stable and unambiguous.**

4. **`==` is NOT full JS loose equality.** SharpTS `IsEqual` only coerces object↔primitive
   (boxed wrappers); for primitive-vs-primitive it does typed `.Equals`. So
   `1 == "1"`→`false`, `true == 1`→`false`, `0 == false`→`false` (NON-JS), but
   `null == undefined`→`true`. **Predict SharpTS behavior, not Node.** Prefer `===` and
   same-type operands in tests to avoid this hazard.

5. No-arg invocation launches a REPL (irrelevant; never invoke without a file).

### Confirmed-correct baseline behaviors (safe to build expected stdout on)
arithmetic/precedence, string slice/substring/indexOf/split/replace/replaceAll/at,
array map/filter/reduce/slice, destructuring + defaults (only `undefined` triggers a
default), `...rest`, closures, `for-of`/`for-in`, `?.` short-circuit (side effects in
args are NOT evaluated), `??` vs `||` (`0 ?? "x"`→`0`), template literals, classes +
inheritance + `instanceof`, try/catch/finally, `typeof` (incl. `typeof null === "object"`),
`let` vs `var` loop capture (`0,1,2` vs `3,3,3`), bitwise (`1<<31`→`-2147483648`,
`-1>>>0`→`4294967295`).

---

## 2. Five Ranked Bug Surfaces

All line numbers are against the pinned checkout. Each "defect to inject" shows the
exact before/after for a 1-3 line edit. All check programs are TYPE-VALID and use
normal-range numbers. Expected stdout is the VERIFIED SharpTS output of the UNMODIFIED
build (i.e., the correct answer the fix must restore).

---

### SURFACE 1 (BEST — HARD, 2-layer, partial-fix-resistant): Relational comparison string-vs-number dispatch

**Files / functions:**
- `Execution/Interpreter.Calls.cs` — `EvaluateBinaryOperationRV` (L486), branch at **L516-520** (`OperatorDescriptor.Comparison`); `EvaluateComparison` (L546-553); `EvaluateStringComparison` (L559-570).
- `TypeSystem/SemanticOperatorResolver.cs` — `Resolve` (L18) classifies `<,>,<=,>=` as `OperatorDescriptor.Comparison` (L33-36). (The dispatch decision is read here and consumed in the interpreter — genuine 2-layer.)

**Correct invariant (ECMA-262 AbstractRelationalComparison):** if BOTH operands are
strings, compare lexicographically by UTF-16 code unit (`string.CompareOrdinal`);
otherwise coerce both to numbers and compare numerically. So `"10" < "9"` is `true`
(string), but `10 < 9` is `false` (number). Verified SharpTS matches JS here.

**Concrete defect to inject** (drop the string-comparison branch so everything goes numeric — the classic "simplify" bug). In `EvaluateBinaryOperationRV`, L517-520:
```
            OperatorDescriptor.Comparison =>
                left is string ls && right is string rs
                    ? RuntimeValue.FromBoolean(EvaluateStringComparison(op.Type, ls, rs))
                    : RuntimeValue.FromBoolean(EvaluateComparison(op.Type, CoerceToNumber(left), CoerceToNumber(right))),
```
becomes:
```
            OperatorDescriptor.Comparison =>
                RuntimeValue.FromBoolean(EvaluateComparison(op.Type, CoerceToNumber(left), CoerceToNumber(right))),
```
Now string operands are coerced via `CoerceToNumber` (parses numeric strings, NaN
otherwise), so `"10" < "9"` becomes `10 < 9`→false, and `"apple" < "banana"` becomes
`NaN < NaN`→false.

**Alternative subtler defect** (mutate the comparator inside `EvaluateStringComparison`,
breaking only `<=`/`>=`): change L566-567 `LESS_EQUAL => cmp <= 0` to `cmp < 0` and
`GREATER_EQUAL => cmp >= 0` to `cmp > 0`. This passes strict `<`/`>` and only fails on
equal strings — good for partial-fix discrimination.

**Observable checks (.ts → expected stdout, all on UNMODIFIED build):**
1. `console.log("10" < "9");` → `true`   (numeric-bug fix path fails: would be `false`)
2. `console.log(10 < 9);` → `false`
3. `console.log("apple" < "banana");` → `true`
4. `console.log("banana" < "apple");` → `false`
5. `console.log("Z" < "a");` → `true`   (uppercase < lowercase by code unit)
6. `console.log("2" > "10");` → `true`   (lexicographic)
7. `console.log("abc" <= "abc", "abc" >= "abc");` → `true true`  (kills the `<=`/`>=` subtle defect)
8. `console.log("apple" <= "apple", "apple" < "banana");` → `true true`

**Partial fix that still fails:** a candidate who "fixes" by special-casing only `<`/`>`
to string-compare but leaves `<=`/`>=` numeric (or vice-versa) fails checks 7-8. A
candidate who restores string compare but uses `string.Compare` (culture) instead of
`CompareOrdinal` fails check 5 (`"Z" < "a"`: ordinal true, many cultures false). Requires
tracing the resolver→dispatch→helper chain, not pattern-matching.

---

### SURFACE 2 (STRONG — HARD, shared helper, partial-fix-resistant): Default `Array.prototype.sort` lexicographic vs numeric

**File / function:** `Runtime/BuiltIns/ArrayBuiltIns.cs` — `StableSort` (L183), default-comparator branch **L198-201**; reached from both `Sort` (L130, in-place) and `ToSorted` (L158, copy) → shared helper across two public methods.

**Correct invariant (ECMA-262 23.1.3.30):** with NO compare function, elements are
converted to strings and sorted by UTF-16 code units (a STABLE sort). So
`[10,9,2,1,100].sort()` → `[1,10,100,2,9]`. With a compare function, numeric order is
honored. `undefined`s sort to the end. Verified SharpTS matches.

**Concrete defect to inject** (make the default sort numeric — the seductively "correct-
looking" bug). Replace L199-200:
```
            sorted = items.OrderBy(x => Stringify(x.Element), StringComparer.Ordinal)
                          .ThenBy(x => x.Index);
```
with:
```
            sorted = items.OrderBy(x => x.Element is double d ? d : double.MaxValue)
                          .ThenBy(x => x.Index);
```
Now `[10,9,2,1,100].sort()` wrongly yields `[1,2,9,10,100]`, and string arrays collapse
(all map to MaxValue → original order).

**Observable checks (.ts → expected stdout, UNMODIFIED build):**
1. `console.log([10, 9, 2, 1, 100].sort().join(","));` → `1,10,100,2,9`
2. `console.log([5, 50, 6].sort().join(","));` → `5,50,6`
3. `console.log([1, 30, 4, 21, 100000].sort().join(","));` → `1,100000,21,30,4`
4. `console.log(["banana", "apple", "cherry"].sort().join(","));` → `apple,banana,cherry`
5. `console.log([3, 1, 2].sort().join(","));` → `1,2,3`  (also correct numerically — trap: a numeric "fix" passes this)
6. `console.log([10, 9, 2, 1, 100].sort((a, b) => a - b).join(","));` → `1,2,9,10,100`  (explicit comparator must still work)
7. Stability: `const a:any[]=[{k:"b",v:1},{k:"a",v:2},{k:"a",v:3}]; console.log(a.sort((x,y)=>x.k<y.k?-1:x.k>y.k?1:0).map(o=>o.v).join(","));` → `2,3,1`

**Partial fix that still fails:** a fix that switches to numeric default sort passes 5
(already sorted) but fails 1-4. A fix that lexicographically sorts but loses stability
fails 7. A fix that special-cases all-number arrays but mishandles strings fails 4.
Tracing required: realize default sort is string-based AND used by both Sort/ToSorted.

---

### SURFACE 3 (STRONG — 2-layer, edge-case-rich): `string.slice` vs `string.substring` negative/swapped indices

**File / functions:** `Runtime/BuiltIns/StringBuiltIns.cs` — `SliceV2` (L342-352) and
`SubstringV2` (L301-309). Two methods registered side-by-side (L17, L30) with DIFFERENT
index normalization rules; a single shared mistake (or copy-paste of one into the other)
breaks distinguishing edge cases.

**Correct invariants:**
- `slice(start,end)`: negative indices count from end (`len+start`, clamped ≥0); does
  NOT swap; `end<=start`→`""`.
- `substring(start,end)`: negative/NaN→0; SWAPS so smaller is start... **but** SharpTS's
  `SubstringV2` does NOT swap (it returns `""` when `end<=start`) — VERIFY: SharpTS
  `"hello world".substring(6,3)` → `""` (NOT the JS-swapped `"lo "`). Build expected
  stdout from SharpTS behavior below.
- Verified SharpTS: `slice(-5)`→`"world"`, `slice(0,-6)`→`"hello"`, `substring(6)`→`"world"`, `substring(6,3)`→`""`.

**Concrete defect to inject** (break `slice`'s negative-`start` normalization — common
off-by-sign error). In `SliceV2`, L346:
```
        if (start < 0) start = Math.Max(0, str.Length + start);
```
becomes:
```
        if (start < 0) start = Math.Max(0, str.Length - start);   // sign flip
```
Now `slice(-5)` computes `len-(-5)=len+5` → clamped to len → `""` instead of `"world"`.

**Alternative defect** (break negative `end`): change L347 `str.Length + end` to
`str.Length - end`, so `slice(0,-6)` becomes `slice(0, len+6)`→whole string.

**Observable checks (.ts → expected stdout, UNMODIFIED build):**
1. `console.log("hello world".slice(-5));` → `world`
2. `console.log("hello world".slice(0, -6));` → `hello`
3. `console.log("hello world".slice(6));` → `world`
4. `console.log("hello world".slice(-5, -1));` → `worl`
5. `console.log("hello world".substring(6));` → `world`
6. `console.log("hello world".substring(6, 3));` → `` (empty line — SharpTS does not swap)
7. `console.log("abcdef".slice(2, 4));` → `cd`   (no negatives — a sign-flip fix that special-cases negatives must keep this)
8. `console.log("abc".slice(-1));` → `c`

**Partial fix that still fails:** fixing only negative `start` but not negative `end`
fails 2/4 (or vice versa). A fix that makes slice swap like substring fails 4. Requires
distinguishing the two methods' normalization and handling both index args.

---

### SURFACE 4 (GOOD — shared `Stringify` helper, multi-consumer): integer-double `.0` rendering

**File / function:** `Execution/Interpreter.Operators.cs` — `Stringify` (L944), number
branch **L949-957**. This single helper backs console.log, `+` string concat, template
literals, and array element stringification (`Stringify` recurses for arrays at L966).
Genuine multi-consumer: one defect shows up across log/concat/template/join.

**Correct invariant:** a double with no fractional part prints without a decimal point
(`5`, not `5.0`). The code calls `d.ToString()` then strips a trailing `".0"`. (Note:
`Array.prototype.join` uses a SEPARATE `Stringify` at ArrayBuiltIns.cs L913 with the same
`.0`-strip — to keep the bug single-surface, target the Interpreter one and test via
console.log / template / `+`, NOT via `join`.)

**Concrete defect to inject** (drop the `.0` strip). In `Stringify`, L951-955:
```
            string text = d.ToString();
            if (text.EndsWith(".0"))
            {
                text = text.Substring(0, text.Length - 2);
            }
            return text;
```
becomes:
```
            return d.ToString();
```
On the .NET runtime in use, integer-valued doubles render as e.g. `5` already (so the
strip is a no-op for those) — **VERIFY which integers actually produce `".0"`** before
committing this defect. If `double.ToString()` never yields `.0` here, instead inject the
inverse, more reliably observable defect below.

**More reliable defect (RECOMMENDED): force a `.0` suffix on whole numbers.** Replace the
number branch body (L951-956) with:
```
            string text = d.ToString();
            return d == Math.Floor(d) && !double.IsInfinity(d) ? text + ".0" : text;
```
Now every integer prints with a spurious `.0` everywhere Stringify is used.

**Observable checks (.ts → expected stdout, UNMODIFIED build):**
1. `console.log(5);` → `5`
2. `console.log(2 + 3);` → `5`
3. `console.log("x" + 42);` → `x42`
4. `` console.log(`v=${100}`); `` → `v=100`
5. `console.log(10 / 2);` → `5`
6. `console.log(5.5);` → `5.5`   (non-integer must be unaffected)
7. `console.log(0);` → `0`
8. `console.log("" + (4 * 25));` → `100`

**Partial fix that still fails:** a fix that only handles the console.log path but not
`+`/template (e.g. patches a different formatter) fails 3-4-8. A fix that strips `.0` but
also mangles genuine decimals fails 6. Requires recognizing `Stringify` is the single
shared coercion point.

> NOTE: confirm the chosen direction empirically first (run `console.log(5.0)` on the
> patched build) — the runtime's default `double.ToString()` already omits `.0`, so the
> "force `.0`" variant is the dependable one.

---

### SURFACE 5 (GOOD — 2-layer, edge-rich): `Array.prototype.indexOf` `fromIndex` clamping

**File / function:** `Runtime/BuiltIns/ArrayBuiltIns.cs` — `IndexOfV2` (L402-425),
`fromIndex` handling **L409-417**; uses `ToIntegerOrInfinity(object?)` (L459-474) — the
defect can live in either the clamping math (IndexOfV2) or the shared coercion
(ToIntegerOrInfinity, also used by lastIndexOf/fill/splice — careful, that widens blast
radius; prefer the local clamp).

**Correct invariant (ECMA-262 23.1.3.17):** search starts at `fromIndex`; negative
`fromIndex` is relative to length (`max(len+fromIndex,0)`); `fromIndex>=len`→ not found
(`-1`); default start 0. Returns first matching index or -1. Verified SharpTS:
`[1,2,3,2,1].indexOf(2)`→`1`, `indexOf(2,2)`→`3`, `indexOf(2,-2)`→`3`, `indexOf(2,10)`→`-1`.

**Concrete defect to inject** (break negative `fromIndex` — off-by-sign). In `IndexOfV2`,
L416:
```
            else start = (int)Math.Max(len + fromIndex, 0);
```
becomes:
```
            else start = (int)Math.Max(len - fromIndex, 0);   // sign flip on negative fromIndex
```
Now `indexOf(2,-2)` starts at `len-(-2)=len+2` → clamps to `len` → never searches → `-1`.

**Observable checks (.ts → expected stdout, UNMODIFIED build; use `: number[]` to keep types valid):**
1. `const a: number[] = [1, 2, 3, 2, 1]; console.log(a.indexOf(2));` → `1`
2. `const a: number[] = [1, 2, 3, 2, 1]; console.log(a.indexOf(2, 2));` → `3`
3. `const a: number[] = [1, 2, 3, 2, 1]; console.log(a.indexOf(2, -2));` → `3`
4. `const a: number[] = [1, 2, 3, 2, 1]; console.log(a.indexOf(1, -1));` → `4`
5. `const a: number[] = [1, 2, 3, 2, 1]; console.log(a.indexOf(2, 10));` → `-1`
6. `const a: number[] = [1, 2, 3]; console.log(a.indexOf(5));` → `-1`
7. `const a: number[] = [1, 2, 3, 2, 1]; console.log(a.indexOf(1, -100));` → `0` (over-negative clamps to 0)
8. `const a: number[] = [1, 2, 3, 2, 1]; console.log(a.indexOf(3, 0));` → `2`

**Partial fix that still fails:** a fix that handles positive `fromIndex` but mis-clamps
the over-negative case fails 7; one that fixes the sign but forgets the `>=len`→`-1`
guard fails 5. Requires reasoning about all three regions (positive-clamped,
negative-relative, out-of-range).

---

## Ranking (most→least suitable as HARD, traceable, multi-layer)

1. **Surface 1 — relational comparison string/number dispatch.** Best: spans resolver +
   interpreter + two helper methods, subtle partial-fix traps (`<=`/`>=`, ordinal vs
   culture), output is crisp booleans.
2. **Surface 2 — default sort lexicographic-vs-numeric.** Strong: shared helper across
   Sort/ToSorted, the "numeric looks correct" trap, stability sub-check.
3. **Surface 3 — slice/substring negative indices.** Strong: two adjacent methods,
   multiple index regions, distinct semantics to keep straight.
4. **Surface 5 — indexOf fromIndex clamping.** Good: three index regions, clean integer
   output; slightly narrower (one method).
5. **Surface 4 — Stringify `.0` rendering.** Good multi-consumer reach but verify the
   defect direction empirically first (runtime already omits `.0`); use the "force `.0`"
   variant.

All expected-stdout values above are the VERIFIED outputs of the unmodified Release
build, so a `defect.patch` + multi-case `cases.json` can be authored directly. Remember
the two assertion modes: stdout match for "no error", and stdout-contains-`Runtime Error:`
for runtime-error cases (exit code is 0 for runtime errors, 1 only for static type errors).
