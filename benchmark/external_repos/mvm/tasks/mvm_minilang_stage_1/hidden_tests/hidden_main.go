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
		{"add", "print 2+3", "5"},
		{"precedence", "print 2+3*4", "14"},
		{"left_sub", "print 10-3-2", "5"},
		{"left_div", "print 8/4/2", "1"},
		{"parens", "print (2+3)*4", "20"},
		{"nested_parens", "print ((1+2)*(3+4))", "21"},
		{"unary_neg", "print -5+3", "-2"},
		{"unary_mid", "print 2 - -3", "5"},
		{"unary_mul", "print 3 * -2", "-6"},
		{"trunc1", "print 7/2", "3"},
		{"trunc2", "print 8/3", "2"},
		{"trunc_neg", "print -7/2", "-3"},
		{"whitespace", "print   3   *   4  ", "12"},
		{"let_use", "let x = 2+3\nprint x", "5"},
		{"let_chain", "let a = 4\nlet b = a*2\nprint b+1", "9"},
		{"semicolons", "let x=10; let y=20; print x+y", "30"},
		{"multi_print", "print 1\nprint 2\nprint 3", "1\n2\n3"},
		{"undef_var", "print zzz", "error: undefined variable: zzz"},
		{"parse_err", "print 2+", "error: parse error"},
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
