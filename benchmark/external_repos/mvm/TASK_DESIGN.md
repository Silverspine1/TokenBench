# mvm — Bug-Task Design Notes

Repo: `github.com/mvm-sh/mvm` — a Go-source interpreter that compiles Go to a
bytecode and runs it on a register/stack VM.
Pinned checkout: `benchmark/external_repos/mvm/cache/.git_clone`
Go 1.26.4. Zero external dependencies.

Pipeline: `scan` (lexer) -> `goparser` (parse + symbolic typing, builds `*vm.Type`)
-> `comp` (compiler: emits `[]vm.Instruction`, picks per-type opcodes) ->
`vm` (executes bytecode). `mtype`/`runtype`/`symbol` support typing.

## Environment notes (READ FIRST)

- Go is **not** on PATH. Every bash command must start with:
  `export PATH="/c/Program Files/Go/bin:$PATH"`
- **Do not** blank-import `stdlib/all` — it pulls in `stdlib/ext`, which uses
  Unix-only `log/syslog` and **fails to build on Windows**. Use `stdlib/core`,
  which registers `fmt`, `strings`, `strconv`, `math`, `sort`, `bytes`, etc.
- Core packages build & test clean: `goparser scan comp interp mtype symbol
  runtype vm`.

---

## 1. Verified Black-Box Hidden-Test Harness

A standalone `package main` lives at `<clone>/tbprobe/main.go` and is **verified
working** (see below). It is the canonical pattern for an mvm hidden-test runner.

### Exact run command
```bash
export PATH="/c/Program Files/Go/bin:$PATH"
cd <clone>            # the module root, where go.mod lives
go run ./tbprobe
```
Verified output:
```
TOKENBENCH_CHECKS passed=3 total=3
```
Exit code 0 when all checks pass, 1 otherwise.

### Exact working harness code
```go
package main

import (
	"bytes"
	"fmt"
	"os"
	"strings"

	"github.com/mvm-sh/mvm/interp"
	"github.com/mvm-sh/mvm/lang/golang"
	"github.com/mvm-sh/mvm/stdlib"
	_ "github.com/mvm-sh/mvm/stdlib/core" // registers core stdlib values; avoids Unix-only stdlib/ext
)

// runProgram evaluates a full `package main` program through a FRESH interpreter
// and returns whatever it wrote to stdout, plus any eval error (includes
// interpreted-program runtime panics).
func runProgram(name, src string) (string, error) {
	i := interp.NewInterpreter(golang.GoSpec)
	i.ImportPackageValues(stdlib.Values)
	i.ImportPackageConsts(stdlib.ConstValues)
	var out bytes.Buffer
	i.SetIO(strings.NewReader(""), &out, &out)
	_, err := i.Eval(name, src)
	return out.String(), err
}

type check struct {
	name string
	src  string
	want string // expected exact stdout
}

func main() {
	checks := []check{
		{name: "arith", src: `package main
import "fmt"
func main() { fmt.Println(2 + 3*4) }`, want: "14\n"},
		{name: "loopsum", src: `package main
import "fmt"
func main() {
	s := 0
	for i := 1; i <= 10; i++ { s += i }
	fmt.Println(s)
}`, want: "55\n"},
		{name: "stringop", src: `package main
import (
	"fmt"
	"strings"
)
func main() { fmt.Println(strings.ToUpper("ab") + "c") }`, want: "ABc\n"},
	}

	passed := 0
	for _, c := range checks {
		got, err := runProgram(c.name, c.src)
		if err != nil {
			fmt.Fprintf(os.Stderr, "check %s: eval error: %v\n", c.name, err)
			continue
		}
		if got == c.want {
			passed++
		} else {
			fmt.Fprintf(os.Stderr, "check %s: got %q want %q\n", c.name, got, c.want)
		}
	}

	fmt.Printf("TOKENBENCH_CHECKS passed=%d total=%d\n", passed, len(checks))
	if passed != len(checks) {
		os.Exit(1)
	}
}
```

### Investigation results (all verified by running probe variants)

- **Capturing interpreted-program stdout.** `i.SetIO(in, out, errW)` where
  `out`/`errW` are any `io.Writer`. Point both at a `*bytes.Buffer` to capture.
  `SetIO` lives on `vm.Machine` (`vm/vm.go:492`); `Interp` embeds `*vm.Machine`.

- **Reading an Eval return value.** `Eval(name, src) (reflect.Value, error)`
  (`interp/interpreter.go:86`). Note the **arg order is `(name, src)`**, not
  `(src)`. For an **expression** eval (e.g. `Eval("expr", "1+2+3")`) the returned
  `reflect.Value` is valid and equals the value (`6`), with `i.StackLen()==1`.
  For a full `package main` program, output comes via **stdout**, and the
  returned value is not the interesting channel — assert on captured stdout.
  `EvalFiles([]goparser.PackageSource{{Name, Content}})` is the multi-file form.

- **State isolation.** A **fresh** `NewInterpreter` per program is fully isolated
  (verified: `y` defined in interp #1 is `undefined` in interp #2). **Reusing one
  interpreter** across `Eval` calls **shares** top-level symbol state (verified:
  `Eval("a","x := 41")` then `Eval("b","x + 1")` both succeed; the second sees
  `x`). **Recommendation for hidden tests: construct a fresh interpreter per
  check** (as `runProgram` does) so checks cannot leak into each other.

- **How runtime panics/errors surface.** Verified by running a div-by-zero and an
  out-of-range index program:
  - Integer divide-by-zero -> **returned as `err`** (not a host panic):
    `panic: runtime error: integer divide by zero` with a source-pointer trace.
  - Index out of range -> **returned as `err`**:
    `panic: runtime error: index out of range`.
  - Compile errors (`undefined: X`) -> **returned as `err`**:
    `<name>:<line>:<col>: undefined: X`.
  The VM converts interpreted panics into recoverable `err` returns; it does
  **not** propagate a Go-level panic to the host. So a hidden-test harness only
  needs to check the `err` return — wrap in a recover defensively but it is not
  required. `os.Exit`/`log.Fatal` from interpreted code returns an
  `*interp.ExitError` (carries `Code`).

---

## 2. Five Ranked Bug Surfaces

All five were confirmed to produce **correct** output on the pinned checkout
(baseline verified via the probe), so an injected defect yields observable wrong
output. Each is a small, plausible edit that a model must **trace through 2+
layers** to fix.

Ranking summary (best hard multi-layer task first):

| # | Surface | Files / layers | Why hard |
|---|---------|----------------|----------|
| 1 | `NumKindOffset` opcode-block dispatch | vm/value.go + comp/compiler.go + vm/vm.go (3 layers) | flag set in VM table, consumed by compiler, executed by VM; one kind mis-dispatched |
| 2 | `truncToKind` width truncation (shift/comp) | vm/numops.go + vm/vm.go (helper used by 3 opcodes) | partial fix fixes one width, others still wrong |
| 3 | `emitComparisonOp` signed/unsigned + `>=`/`<=` negate | comp/compiler.go + vm/vm.go | sign + negate interaction; naive fix breaks one operator family |
| 4 | `Value.Equal` integer/string equality helper | vm/value.go (helper used by Equal, EqualSet, switch, map keys) | one helper feeds 4 opcodes; partial fix misses switch/map |
| 5 | per-type integer arithmetic generics (`add`/`sub`/...`[T]`) | vm/numops.go + vm/vm.go | width wrap; naive fix to one op leaves siblings wrong |

---

### Surface 1 — `NumKindOffset` opcode-block dispatch (BEST)

**Layers:** table defined in `vm/value.go` -> consumed by `numericOp` in
`comp/compiler.go:4011` -> executed by per-kind opcode blocks in `vm/vm.go`.

**Where.**
- Table: `vm/value.go:78-95` (`init` filling `NumKindOffset`).
- Consumer: `comp/compiler.go:4011-4020`
  ```go
  func numericOp(base vm.Op, typ *vm.Type) vm.Op {
      ...
      return base + vm.Op(vm.NumKindOffset[k])
  }
  ```
- Opcode blocks: e.g. `AddInt..AddFloat64` at `vm/vm.go:3137-3182`, and the
  per-type `Greater*`/`Lower*` at `vm/vm.go:3425-3450`.

**Invariant.** For a value of `reflect.Kind` *k*, `base + NumKindOffset[k]` must
land on the opcode for exactly that kind. The contiguous block layout is:
Int(0) Int8(1) Int16(2) Int32(3) Int64(4) Uint(5) Uint8(6) Uint16(7) Uint32(8)
Uint64(9) Float32(10) Float64(11); Uintptr aliases Uint(5).

**Concrete defect (1 line, in `vm/value.go`).** Swap two adjacent offsets so one
kind dispatches to a neighbor's opcode block:
```go
// before
NumKindOffset[reflect.Uint8]  = 6
NumKindOffset[reflect.Uint16] = 7
// after (defect)
NumKindOffset[reflect.Uint8]  = 7
NumKindOffset[reflect.Uint16] = 6
```
Now `uint8 +,-,*,/,>,<` execute the `uint16` opcode (no truncation to 8 bits) and
vice-versa. Comparisons mostly agree but arithmetic **wrap differs**.

Alternative defect: change the Uintptr alias (`NumKindOffset[reflect.Uintptr] =
5` -> `= 0`) so `uintptr` arithmetic/compare runs **signed `int`** ops — wrong for
large values. Or `NumKindOffset[reflect.Float32] = 11` so `float32` uses
`float64` ops (loses float32 rounding).

**Observable checks (Go programs -> expected stdout).** Use the uint8/uint16 swap:
1. `var x uint8 = 200; var y uint8 = 100; println(x+y)` -> `44` (defect: `300`).
2. `var x uint8 = 255; x++; println(x)` -> `0` (defect: `256`).
3. `var x uint16 = 60000; var y uint16 = 10000; fmt.Println(x+y)` -> `4464`
   (defect: with swap, uint16 runs uint8 ops -> `112`).
4. `var x uint8 = 250; var y uint8 = 10; fmt.Println(x*y)` -> `196` (2500 mod 256)
   (defect wrong).
5. `var a uint16 = 256; var b uint16 = 1; fmt.Println(a+b)` -> `257`
   (defect: uint8 wrap -> `1`).
6. Control case that a partial fix can still pass:
   `var x uint8 = 10; var y uint8 = 20; fmt.Println(x+y)` -> `30` (both correct
   because no overflow) — proves the suite needs overflow cases.
7. `var x uint32 = 4000000000; var y uint32 = 1000000000; fmt.Println(x+y)` ->
   `705032704` (uint32 wrap) — guards against a fixer who only touches uint8.
8. `var f float32 = 0.1; fmt.Println(f + 0.2)` (float32 rounding) — guards the
   alternative float defect.

**What a partial fix still fails.** A fixer who only restores
`NumKindOffset[reflect.Uint8] = 6` but leaves `Uint16 = 6` (forgetting it must go
back to 7) passes the uint8 checks (1,2,4,5) but **fails the uint16 checks
(3,5b)**. Checks must include **both** swapped kinds. Add unrelated-kind cases (7)
so a fixer who rewrites the whole table by guesswork can still be caught.

---

### Surface 2 — `truncToKind` width truncation (shift / comp / bitwise)

**Layers:** helper in `vm/numops.go` used by **three** opcodes in `vm/vm.go`
(`BitShl`, `BitShr`, `BitComp`).

**Where.**
- Helper: `vm/numops.go:51-67` (`truncToKind`).
- Callers: `vm/vm.go:2790` (`BitShl`), `vm/vm.go:2797` (`BitShr` unsigned),
  `vm/vm.go:2810` (`BitComp` / `^`).

**Invariant.** After a uint64-width op, `truncToKind` must narrow the result to
the value's declared width, sign-extending signed kinds. E.g. `uint8(1) << 9`
must yield `0` (512 truncated to 8 bits); `^uint8(0)` must yield `255`.

**Concrete defect (1 line, in `vm/numops.go`).** Make one case not truncate:
```go
// before
case reflect.Uint8:
    return uint64(uint8(n))
// after (defect)
case reflect.Uint8:
    return n
```
Or drop sign-extension for `Int16`:
```go
// before
case reflect.Int16:
    return uint64(int64(int16(n)))
// after (defect)
case reflect.Int16:
    return uint64(uint16(n))   // zero-extends instead of sign-extends
```

**Observable checks.**
1. `var x uint8 = 1; fmt.Println(x << 9)` -> `0` (defect with Uint8 no-trunc:
   `512`).
2. `var x uint8 = 0; fmt.Println(^x)` -> `255` (defect: huge number).
3. `var x uint8 = 0xFF; fmt.Println(x << 1)` -> `254` (defect: `510`).
4. `var y int8 = -128; fmt.Println(y >> 1)` -> `-64` (guards signed path).
5. `var z int16 = -2; fmt.Println(^z)` -> `1` (relies on sign-extend of
   `^`; the Int16 defect prints `1` too — pick `^int16(-1)`=`0` and a negative
   shift result to expose it).
6. `var w uint16 = 0xFFFF; fmt.Println(w << 1)` -> `65534` (guards uint16 case).
7. `var u uint32 = 0x80000000; fmt.Println(u << 1)` -> `0` (uint32 truncation).
8. `var a int16 = -100; fmt.Println(a >> 2)` -> `-25` (arithmetic shift +
   sign-extend interplay; the Int16 zero-extend defect breaks downstream compares
   when the shifted value is later compared as a signed int).

**What a partial fix still fails.** A fixer who patches only the `Uint8` case
passes 1-3 but **fails uint16/uint32 checks (6,7)** if the defect was injected in
multiple cases; even with a single-case defect, including 6/7 forces the model to
prove it didn't break the others. Because the helper is shared by `<<`, `>>`, and
`^`, a fixer who hardcodes the answer inside `BitShl` (instead of fixing the
helper) **fails the `^`/`>>` checks (2,5)**.

---

### Surface 3 — `emitComparisonOp` signed/unsigned + `>=`/`<=` negate

**Layers:** compiler chooses the op family + a `negate` flag
(`comp/compiler.go`), VM executes signed vs unsigned compare (`vm/vm.go`).

**Where.**
- Selector: `comp/compiler.go:4038-4067` (`emitComparisonOp`).
- Dispatch sites: `comp/compiler.go:1496-1522` — note `>=` is compiled as
  `!(<)` and `<=` as `!(>)` for integers/strings (the `negate=true` arg).
- VM: signed `GreaterInt`/`LowerInt` at `vm/vm.go:3425/3436` cast to `int64`;
  unsigned `GreaterUint`/`LowerUint` at `vm/vm.go:3428/3439` compare raw `uint64`.
- `isUint64Kind` / `isInt64Kind`: `comp/compiler.go:3967-3981`.

**Invariant.** For unsigned operands the compiler must select the **uint** imm
op (`uintImm`/`fuseUint`); selecting the **int** op makes large unsigned values
compare as negative. And `>=`/`<=` must apply the `negate` flag (Not) exactly
once.

**Concrete defect (1 line, in `emitComparisonOp`).** Force the signed branch:
```go
// before
} else if isUint64Kind(typ) {
    immOp, fuseOp = uintImm, fuseUint
}
// after (defect)
} else if isUint64Kind(typ) {
    immOp, fuseOp = intImm, fuseInt   // wrong: signed imm op for unsigned operand
}
```
Alternative: drop a `negate` emit so `>=` becomes `<` (`comp/compiler.go:4057-4059`
remove the `if negate { c.emit(t, vm.Not) }`).

**Observable checks (signed-branch defect uses the *immediate* path, so RHS must
be a constant to hit `immOp`).**
1. `var x uint = 0; fmt.Println(x - 1 > 5)` -> `true` (max-uint > 5)
   (defect: signed compare of `-1` -> `false`).
2. `var x uint64 = 18446744073709551615; fmt.Println(x > 0)` -> `true`
   (defect: as int64 it's `-1` -> `false`).
3. `var x uint = 10; fmt.Println(x >= 10)` -> `true` (guards `>=` negate).
4. `var x uint = 9; fmt.Println(x >= 10)` -> `false`.
5. `var x uint64 = 1 << 63; fmt.Println(x > 100)` -> `true`
   (defect: int64 negative -> `false`).
6. Control: `var x uint = 3; fmt.Println(x > 5)` -> `false` (small values agree;
   proves the suite needs values above int64 max / wrap).
7. `var x int = -1; fmt.Println(x < 0)` -> `true` (guards that a fixer doesn't
   break the legitimate signed path).
8. `var x uint = 0; fmt.Println(x <= 0)` -> `true` (`<=` via `!(>)` negate path).

**What a partial fix still fails.** If the defect is the signed-branch swap, a
fixer who only patches `>` but not `<` passes 1,2,5 but **fails the `<`-derived
`>=`/`<=` checks (3,4,8)** because `>=` is compiled through the `LowerInt` family.
The `>=`/`<=`-as-negate compilation is the trap: a model that pattern-matches
`Greater`/`Lower` opcodes without realizing `>=` routes through the **opposite**
family leaves half the operators broken.

---

### Surface 4 — `Value.Equal` integer/string equality helper

**Layers:** one helper in `vm/value.go` feeds **four** consumers: `Equal`
opcode, `EqualSet` (switch case matching), and map-key comparison.

**Where.**
- Helper: `vm/value.go:412` (`func (v Value) Equal(u Value) bool`), specifically
  the numeric branch `vm/value.go:446-453` and the string branch
  `vm/value.go:456-458`.
- Consumers: `Equal` at `vm/vm.go:1653`; `EqualSet` at `vm/vm.go:1656` (used to
  "simplify bytecode in case clauses of switch statements" per its comment);
  map keys via `m.mapKey`.

**Invariant.** Two numeric values are equal iff `v.num == u.num` (floats compared
as floats for IEEE rules). Two strings equal iff content matches.

**Concrete defect (1 line, in `vm/value.go:452`).** Break integer equality
subtly so it ignores the high bits:
```go
// before
return v.num == u.num
// after (defect)
return uint32(v.num) == uint32(u.num)   // only low 32 bits compared
```
This is invisible for small ints (all hidden simple cases pass) but wrong for
values differing only above bit 32, AND it corrupts `switch` matching and map
lookups that hash/compare wide keys.

Alternative: in the string branch return `len(v...) == len(u...)` (equal length
=> "equal") — passes many cases, fails distinct same-length strings.

**Observable checks (int-low32 defect).**
1. `var a int64 = 1<<40; var b int64 = 0; fmt.Println(a == b)` -> `false`
   (defect: low32 of both are 0 -> `true`).
2. `var a int64 = 1<<40 + 7; var b int64 = 7; fmt.Println(a == b)` -> `false`
   (defect: `true`).
3. switch: `var x int64 = 1<<40; switch x { case 0: fmt.Print("z"); default:
   fmt.Print("d") }` -> `d` (defect: matches case 0 -> `z`).
4. map: `m := map[int64]string{1<<40: "hi"}; fmt.Println(m[0])` -> `` (empty)
   (defect: low32 collision returns `hi`).
5. Control: `fmt.Println(5 == 5)` -> `true` (small ints — both correct).
6. Control: `fmt.Println(5 == 6)` -> `false`.
7. string (guards the alternative defect): `fmt.Println("ab" == "cd")` ->
   `false`.
8. `var a uint64 = 0x1_0000_0000; var b uint64 = 0; fmt.Println(a == b)` ->
   `false` (unsigned wide).

**What a partial fix still fails.** A fixer who patches the `Equal` opcode site
in `vm/vm.go` (e.g. special-cases ints there) instead of the shared `Value.Equal`
helper **still fails the switch (3) and map (4) checks**, which route through
`EqualSet`/`mapKey` -> the same broken helper. This forces the model to find the
single shared helper rather than the first opcode it sees.

---

### Surface 5 — per-type integer arithmetic generics (`add`/`sub`/`mul`/`neg`)

**Layers:** generic helpers in `vm/numops.go` instantiated per kind, dispatched
by per-type opcodes in `vm/vm.go`.

**Where.**
- Helpers: `vm/numops.go:15-20` (`add`/`sub`/`mul`/`div`/`rem`/`neg[T integer]`).
- Opcode blocks instantiate them, e.g. `AddInt8` -> `add[int8]` at
  `vm/vm.go:3141-3148`, `AddUint8` etc.

**Invariant.** `add[T](a,b)` must compute in width `T` so results wrap at the
type's modulus: `add[uint8](200,100) == 44`, `add[int8](100,100) == -56`.

**Concrete defect (1 line, in `vm/numops.go:15`).** Compute in the wrong width:
```go
// before
func add[T integer](a, b uint64) uint64 { return uint64(T(a) + T(b)) }
// after (defect)
func add[T integer](a, b uint64) uint64 { return a + b } // no per-T wrap
```
Now every `Add*` opcode adds full uint64 then the value carries an out-of-range
`.num`, so subsequent narrow compares/prints are wrong. A subtler variant:
`func sub[T integer](a, b uint64) uint64 { return uint64(T(b) - T(a)) }` (swapped
operands) — only subtraction breaks.

**Observable checks.**
1. `var x uint8 = 200; var y uint8 = 100; fmt.Println(x+y)` -> `44`.
2. `var s int8 = 100; fmt.Println(s+s)` -> `-56`.
3. `var x uint16 = 60000; var y uint16 = 10000; fmt.Println(x+y)` -> `4464`.
4. subtraction (guards the swapped-operand variant):
   `var a int = 10; var b int = 3; fmt.Println(a-b)` -> `7` (defect: `-7`).
5. `var x uint8 = 5; var y uint8 = 10; fmt.Println(x-y)` -> `251` (uint8 wrap).
6. multiplication: `var x uint8 = 50; var y uint8 = 6; fmt.Println(x*y)` -> `44`
   (300 mod 256).
7. Control: `fmt.Println(2+3)` -> `5` (int, no wrap — passes even broken).
8. negation: `var x int8 = -128; fmt.Println(-x)` -> `-128` (int8 neg overflow).

**What a partial fix still fails.** If the defect is in `add` only, a model that
also "tidies" `sub`/`mul` consistently is fine, but a model that hardcodes a wrap
into the `AddUint8` opcode site (not the generic) **fails the uint16/int8 add
checks (2,3)**. Including subtraction/multiplication/negation cases (4,6,8)
guards against a fixer who only restores `add` while a second injected defect
sits in `sub`.

---

## Build/Verify cheatsheet for defect authoring

```bash
export PATH="/c/Program Files/Go/bin:$PATH"
cd <clone>
go build ./vm ./comp ./interp ./goparser   # confirm defect compiles
go run ./tbprobe                            # run your hidden-test harness
go test ./vm ./comp ./interp/...            # the repo's own tests (a defect
                                            # should also redden some of these,
                                            # useful as a sanity oracle)
```

`tbprobe/` is left in place at `<clone>/tbprobe/main.go` (the verified harness).
Delete it if you do not want it in the task snapshot; it has no other refs.
