# Stage 1 Strict Check

## result/v005

Failures:
- parse failures: 15
- non-zero exits: 15
- v005/deep-v6: total_delta_lb <= 0 (-3551)
- v005/deep-v6: total_delta_gap >= 0 (27872)
- v005/deep-v6: max UB regression 21586 > 500
- v005/deep-v6/SNAP: max UB regression 21586 > 500

Warnings:
- v005/deep-v6/SNAP: family gap regression (28415)
- v005/deep-v6/T1: family gap regression (10)
- v005/deep-v6/T2: family gap regression (28)

## result/v006

Failures:
- parse failures: 15
- non-zero exits: 15
- v006/deep-v6: total_delta_lb <= 0 (-1971)
- v006/deep-v6: total_delta_gap >= 0 (3179)
- v006/deep-v6: max UB regression 951 > 500
- v006/fast-v19: total_delta_gap >= 0 (425242)
- v006/fast-v19: max UB regression 183600 > 500
- v006/deep-v6/SNAP: max UB regression 951 > 500
- v006/fast-v19/DIMACS10: max UB regression 108847 > 500
- v006/fast-v19/SNAP: max UB regression 183600 > 500

Warnings:
- v006/deep-v6/SNAP: family gap regression (3738)
- v006/deep-v6/T1: family gap regression (19)
- v006/fast-v19/SNAP: family gap regression (547839)

## result/v007

Failures:
- parse failures: 15
- non-zero exits: 15
- v007/deep-v6: total_delta_lb <= 0 (-12937)
- v007/deep-v6: total_delta_gap >= 0 (11379)
- v007/fast-v19: total_delta_gap >= 0 (545229)
- v007/fast-v19: max UB regression 183600 > 500
- v007/fast-v19/DIMACS10: max UB regression 105760 > 500
- v007/fast-v19/SNAP: max UB regression 183600 > 500

Warnings:
- v007/deep-v6: LB wins <= losses (13/17)
- v007/deep-v6: gap wins <= losses (15/19)
- v007/deep-v6/DIMACS10: family gap regression (1256)
- v007/deep-v6/SNAP: family gap regression (10021)
- v007/deep-v6/T2: family gap regression (144)
- v007/deep-v6/UDG: family gap regression (1)
- v007/fast-v19/DIMACS10: family gap regression (312856)
- v007/fast-v19/SNAP: family gap regression (234799)

## result/v009

Failures:
- parse failures: 13
- non-zero exits: 13
- v009/deep-v6: total_delta_lb <= 0 (-9170)
- v009/deep-v6: total_delta_gap >= 0 (29373)
- v009/deep-v6: max UB regression 22131 > 500
- v009/fast-v19: total_delta_gap >= 0 (430109)
- v009/fast-v19: max UB regression 183600 > 500
- v009/deep-v6/SNAP: max UB regression 22131 > 500
- v009/fast-v19/DIMACS10: max UB regression 108537 > 500
- v009/fast-v19/SNAP: max UB regression 183600 > 500

Warnings:
- v009/deep-v6: LB wins <= losses (9/16)
- v009/deep-v6: gap wins <= losses (11/18)
- v009/deep-v6/DIMACS10: family gap regression (867)
- v009/deep-v6/SNAP: family gap regression (28660)
- v009/fast-v19/SNAP: family gap regression (547702)

## Summary

- checked_dirs: 4
- failures: 34
- warnings: 19
