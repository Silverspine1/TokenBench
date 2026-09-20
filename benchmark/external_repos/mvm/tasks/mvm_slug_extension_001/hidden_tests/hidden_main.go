package main

import (
	"bytes"
	"fmt"
	"os"
	"strings"

	"github.com/mvm-sh/mvm/interp"
	"github.com/mvm-sh/mvm/lang/golang"
	"github.com/mvm-sh/mvm/stdlib"
	_ "github.com/mvm-sh/mvm/stdlib/core" // register core stdlib; avoid Unix-only stdlib/ext
)

// run evaluates a full program through a fresh, isolated interpreter and returns
// whatever it wrote to stdout plus any evaluation error.
func run(name, src string) (string, error) {
	i := interp.NewInterpreter(golang.GoSpec)
	i.ImportPackageValues(stdlib.Values)
	i.ImportPackageConsts(stdlib.ConstValues)
	var out bytes.Buffer
	i.SetIO(strings.NewReader(""), &out, &out)
	_, err := i.Eval(name, src)
	return out.String(), err
}

// slugProg builds a guest program that prints tbx.Slug(in).
func slugProg(in string) string {
	return `package main
import ("fmt"; "tbx")
func main() { fmt.Println(tbx.Slug(` + fmt.Sprintf("%q", in) + `)) }`
}

type check struct{ name, in, want string }

func main() {
	checks := []check{
		// Punctuation and whitespace runs collapse to a single dash.
		{"punct_comma", "Hello, World!", "hello-world\n"},
		{"symbols", "C++ & Go", "c-go\n"},
		{"double_dash", "a--b", "a-b\n"},

		// Digit runs are preserved verbatim, never shortened.
		{"digits_run", "a1111b", "a1111b\n"},
		{"digits_zip", "zone55500", "zone55500\n"},

		// Length cap respects a separator sitting exactly on the limit.
		{"trunc_data", "data sciencetoolkitx guide", "data-sciencetoolkitx\n"},
		{"trunc_fast", "fast foodrestaurantx menu", "fast-foodrestaurantx\n"},

		// Straightforward inputs.
		{"basic", "Hello World", "hello-world\n"},
		{"letter_run", "Buzzzz", "buzz\n"},
		{"trim_edges", "  Trim Me  ", "trim-me\n"},
		{"upper_lower", "UPPER lower", "upper-lower\n"},
		{"with_year", "season 2024", "season-2024\n"},
	}

	passed := 0
	for _, c := range checks {
		got, err := run(c.name, slugProg(c.in))
		if err != nil {
			fmt.Fprintf(os.Stderr, "not ok - %s: eval error: %v\n", c.name, err)
			continue
		}
		if got == c.want {
			passed++
		} else {
			fmt.Fprintf(os.Stderr, "not ok - %s: got %q want %q\n", c.name, got, c.want)
		}
	}

	fmt.Printf("TOKENBENCH_CHECKS passed=%d total=%d\n", passed, len(checks))
	if passed != len(checks) {
		os.Exit(1)
	}
}
