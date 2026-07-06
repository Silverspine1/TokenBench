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
	// A simple inclusive range should expand to include its upper bound.
	got, err := run("vis", `package main
import ("fmt"; "tbx")
func main() { fmt.Println(tbx.ExpandRange("1-3")) }`)
	ok := err == nil && got == "1,2,3\n"
	if ok {
		fmt.Println("ok - range expansion")
	} else {
		fmt.Printf("not ok - range expansion: got %q err %v\n", got, err)
	}
	if !ok {
		os.Exit(1)
	}
}
