package main

import (
	"bytes"
	"fmt"
	"os"
	"strings"

	"github.com/mvm-sh/mvm/interp"
	"github.com/mvm-sh/mvm/lang/golang"
	"github.com/mvm-sh/mvm/stdlib"
	_ "github.com/mvm-sh/mvm/stdlib/core"
)

func run(name, src string) (string, error) {
	i := interp.NewInterpreter(golang.GoSpec)
	i.ImportPackageValues(stdlib.Values)
	i.ImportPackageConsts(stdlib.ConstValues)
	var out bytes.Buffer
	i.SetIO(strings.NewReader(""), &out, &out)
	_, err := i.Eval(name, src)
	return out.String(), err
}

func main() {
	// A title with punctuation between words should slugify to clean,
	// single-dash-separated words.
	got, err := run("vis", `package main
import ("fmt"; "tbx")
func main() { fmt.Println(tbx.Slug("Hello, World!")) }`)
	ok := err == nil && got == "hello-world\n"
	if ok {
		fmt.Println("ok - slug formatting")
	} else {
		fmt.Printf("not ok - slug formatting: got %q err %v\n", got, err)
	}
	if !ok {
		os.Exit(1)
	}
}
