// Package apiutil holds small HTTP helpers shared by the handlers.
package apiutil

import (
	"encoding/json"
	"net/http"
)

// WriteJSON serializes v as an indented JSON response with the given status.
func WriteJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	enc := json.NewEncoder(w)
	enc.SetIndent("", "  ")
	_ = enc.Encode(v)
}

// WriteError writes a JSON error envelope with the given status.
func WriteError(w http.ResponseWriter, status int, message string) {
	WriteJSON(w, status, map[string]string{"error": message})
}
