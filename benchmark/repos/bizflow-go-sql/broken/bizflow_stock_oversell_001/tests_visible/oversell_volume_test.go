package tests_visible

import (
	"fmt"
	"testing"

	"bizflow/internal/model"
	"bizflow/internal/repository"
	"bizflow/internal/service"
	"bizflow/internal/store"
)

// This table-driven check sweeps a large grid of (on-hand, already-reserved)
// product states and, for each, reports the availability the system computes
// next to the availability that is genuinely still free to give out (on-hand
// minus what is already reserved). Each case prints a labelled row to stdout so
// the sweep is fully observable; a case fails when the reported availability
// does not match what is truly free, which is exactly what oversold inventory
// looks like. The grid is fixed, so the output is deterministic.
func TestAvailabilityMatchesWhatIsFreeAcrossGrid(t *testing.T) {
	// A fixed grid of on-hand totals and reservation fractions. 30 on-hand
	// values times 30 reservation steps = 900 labelled cases.
	const onHandSteps = 30
	const reservedSteps = 30

	fmt.Println("=== inventory availability sweep: reported vs truly-free ===")

	db := store.NewDB()
	repo := repository.NewProductRepo(db)
	inv := service.NewInventoryService(db)

	caseNo := 0
	for i := 1; i <= onHandSteps; i++ {
		onHand := i * 4 // 4, 8, ... 200
		for j := 0; j < reservedSteps; j++ {
			caseNo++
			// reserved walks from 0 up to just under on-hand in fixed steps.
			reserved := (onHand * j) / reservedSteps
			tenant := "t_acme"
			sku := fmt.Sprintf("SKU-%04d-%02d", i, j)

			repo.Insert(model.Product{
				TenantID: tenant,
				SKU:      sku,
				Name:     fmt.Sprintf("Product %04d-%02d", i, j),
				OnHand:   onHand,
				Reserved: reserved,
			})

			trulyFree := onHand - reserved
			reported, err := inv.Available(tenant, sku)
			status := "ok"
			if err != nil || reported != trulyFree {
				status = "OVERSOLD"
			}

			fmt.Printf(
				"case %04d sku=%s on_hand=%3d reserved=%3d truly_free=%3d reported=%3d status=%s\n",
				caseNo, sku, onHand, reserved, trulyFree, reported, status,
			)

			if err != nil {
				t.Errorf("case %04d sku=%s: unexpected error %v", caseNo, sku, err)
				continue
			}
			if reported != trulyFree {
				t.Errorf(
					"case %04d sku=%s: reported availability %d but only %d are truly free (on_hand=%d reserved=%d)",
					caseNo, sku, reported, trulyFree, onHand, reserved,
				)
			}
		}
	}

	fmt.Printf("=== swept %d cases ===\n", caseNo)
}
