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

// run evaluates a full guest program through a fresh, isolated interpreter and
// returns whatever it wrote to stdout plus any evaluation error.
func run(name, src string) (string, error) {
	i := interp.NewInterpreter(golang.GoSpec)
	i.ImportPackageValues(stdlib.Values)
	i.ImportPackageConsts(stdlib.ConstValues)
	var out bytes.Buffer
	i.SetIO(strings.NewReader(""), &out, &out)
	_, err := i.Eval(name, src)
	return out.String(), err
}

type check struct{ name, ml, want string }

// prog builds a guest program that prints tbx.Run(ml). The mini-language
// source is embedded in a raw string literal so its newlines survive.
func prog(ml string) string {
	header := "package main\nimport (\"fmt\"; \"tbx\")\nfunc main(){ fmt.Print(tbx.Run(`"
	return header + ml + "`)) }"
}

func main() {
	checks := []check{
		{"num_precedence", "print 2+3*4", "14"},
		{"str_concat", "print \"foo\" + \"bar\"", "foobar"},
	}

	passed := 0
	for _, c := range checks {
		got, err := run(c.name, prog(c.ml))
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
