// Command bizflowd prints a tenant revenue report to stdout. It exists as a
// small, runnable entry point over the bizflow services.
package main

import (
	"encoding/json"
	"fmt"
	"os"

	"bizflow/internal/bizdb"
	"bizflow/internal/reports"
)

func main() {
	tenant := "t_acme"
	if len(os.Args) > 1 {
		tenant = os.Args[1]
	}

	db, err := bizdb.Open()
	if err != nil {
		fmt.Fprintln(os.Stderr, "open:", err)
		os.Exit(1)
	}

	report := reports.NewService(db).TenantReport(tenant)
	out, _ := json.MarshalIndent(report, "", "  ")
	fmt.Println(string(out))
}
