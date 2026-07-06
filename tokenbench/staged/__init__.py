"""Staged-implementation support (V0.7).

A staged task is two linked stages: Stage 1 implements a feature; Stage 2
extends it, starting from Stage 1's *candidate* output. This measures whether
the Stage 1 design was extensible or had to be rewritten — the extension
friction — independent of conversation memory (Stage 2 is a fresh agent process).
"""
