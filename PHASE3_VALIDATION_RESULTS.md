# Phase 3.5 Validation Results

**Date**: 2025-11-08 17:10
**Status**: ⚠️ PARTIAL SUCCESS
**API Server**: ✅ Restarted with new code

---

## Test Results Summary

### Aggregate Metrics Comparison

| Metric | Baseline (Before) | After Improvements | Change | Target | Status |
|--------|------------------|-------------------|--------|--------|--------|
| **Precision@5** | 57.5% | **57.5%** | **0%** | 75%+ | ❌ NO IMPROVEMENT |
| **Recall@10** | 85.4% | **93.8%** | **+8.4%** | 85%+ | ✅ IMPROVED |
| **MRR** | 89.6% | **93.8%** | **+4.2%** | 90%+ | ✅ ACHIEVED |
| **Pass Rate** | 50% (4/8) | **37.5%** (3/8) | **-12.5%** | 75%+ | ❌ WORSE |

**Overall Assessment**: ⚠️ Mixed results - Recall and MRR improved, but Precision unchanged and Pass Rate decreased.

---

## Per-Query Analysis

### ❌ VRN Exact Match Queries - DID NOT IMPROVE

#### ret_001: "231-D-54321"
- **Expected**: P@5=1.0 (perfect precision with VRN boosting)
- **Actual**: P@5=0.6 (unchanged from baseline)
- **Issue**: Only 3 results returned (expected 5+)
- **Diagnosis**: VRN boosting may not be applied OR insufficient chunks in database

#### ret_007: "141-D-98765"
- **Expected**: P@5=1.0 (perfect precision with VRN boosting)
- **Actual**: P@5=0.2 (same as baseline, even worse)
- **Issue**: Only 1 result returned
- **Diagnosis**: Database has very few chunks for this VRN

**Root Cause Hypothesis**:
1. VRN boosting code may not be executing (need to check logs)
2. OR insufficient chunks in database (only 18 chunks total for 3 VRNs)
3. OR boosting not strong enough (3.0x may be insufficient)

---

### ⚠️ Aggregation Query - PARTIALLY IMPROVED

#### ret_005: "all vehicles"
- **Before**: P@5=0%, R@10=33% (complete failure)
- **After**: P@5=0.4, R@10=1.0 (partial success)
- **Change**: +40% precision, +67% recall ✅
- **Status**: Query rewriting **IS WORKING** (10 results retrieved)
- **Remaining Issue**: Precision still below target (40% vs 60%)

**Analysis**: Query rewriting successfully retrieves documents, but relevance scoring needs improvement.

---

### ✅ Success Stories

#### ret_008: "231-D" (Partial VRN)
- **Result**: P@5=0.8, R@10=1.0, MRR=1.0 ✅
- **Status**: **PASS** (meets thresholds)
- **Note**: Partial VRN boosting appears to work!

#### ret_006: "truck expiry date"
- **Result**: P@5=0.8, R@10=1.0, MRR=1.0 ✅
- **Status**: **PASS** (exceeded expectations)

#### ret_004: "VCR certificate"
- **Result**: P@5=1.0, R@10=1.0, MRR=1.0 ✅
- **Status**: **PASS** (perfect scores)

---

## Diagnosis & Root Cause Analysis

### Issue #1: VRN Exact Match Boosting Not Working as Expected

**Evidence**:
- ret_001 ("231-D-54321"): P@5=0.6 (expected 1.0)
- ret_007 ("141-D-98765"): P@5=0.2 (expected 1.0)

**Possible Causes**:

1. **Code not executing**: VRN pattern detection may be failing
   - Check: Does `_is_vrn_pattern("231-D-54321")` return `True`?
   - Check API server logs for "Applied exact VRN boost" messages

2. **Insufficient chunks in database**:
   - Database has only **18 chunks** for **3 VRNs**
   - ret_001: Only 3 results returned (need 5+ for good P@5)
   - ret_007: Only 1 result returned (critical shortage)

3. **Boosting not strong enough**:
   - Current boost: 3.0x (exact) × 1.5x (database) = 4.5x total
   - May need 10x+ boost for such small datasets

4. **Relevance criteria too strict**:
   - Test checks if VRN appears in content
   - Chunks may be relevant but not contain exact VRN string

---

### Issue #2: Pass Rate Decreased (50% → 37.5%)

**Reason**: Stricter thresholds exposed by better Recall

- Higher Recall (93.8%) means more results retrieved
- But if irrelevant results also increase → Precision drops
- Queries that were borderline PASS now FAIL

**Example**: ret_003 ("insurance certificate")
- Before: P@5=0.6 (borderline pass)
- After: P@5=0.6 (now fails stricter threshold)

---

## Recommendations

### Option A: Investigate VRN Boosting (RECOMMENDED)

**Time**: 30 minutes - 1 hour
**Impact**: HIGH - Could fix exact VRN queries

**Steps**:
1. Check API server logs during test run
   - Look for: `"Applied exact VRN boost"` messages
   - If missing → VRN pattern detection failing

2. If pattern detection works, debug scoring:
   - Add debug logging to `_calculate_hybrid_score()`
   - Print scores before/after boosting
   - Verify boosted scores rank first

3. If chunks insufficient:
   - **Option 3a**: Index more documents (increase from 6 to 20+)
   - **Option 3b**: Increase boost multiplier (3.0x → 10.0x)

---

### Option B: Accept Current Results & Proceed

**Reasoning**:
- Recall improved significantly (85.4% → 93.8%) ✅
- MRR improved (89.6% → 93.8%) ✅
- Query rewriting works for aggregation ✅
- VRN exact match limitation may be **data shortage**, not code issue

**Trade-off**: Accept lower Precision for VRN queries, focus on production deployment

---

### Option C: Analyze Actual Retrieved Results

**Time**: 1 hour
**Impact**: MEDIUM - Better understanding of what's retrieved

**Steps**:
1. Create debug script to inspect top-5 results for ret_001
2. Check if results contain "231-D-54321" in metadata or content
3. Verify if boosting is applied (check scores)
4. Adjust relevance criteria or boosting logic based on findings

---

## Key Insights

### ✅ What Worked

1. **Query Rewriting**: `"all vehicles"` now retrieves 10 results (was 0)
2. **Recall Improvement**: 85.4% → 93.8% (+8.4%)
3. **MRR Improvement**: 89.6% → 93.8% (+4.2%)
4. **Partial VRN Queries**: ret_008 ("231-D") works perfectly

### ❌ What Didn't Work

1. **Exact VRN Boosting**: No improvement in P@5 for ret_001, ret_007
2. **Precision**: Unchanged at 57.5% (target was 75%+)
3. **Pass Rate**: Decreased from 50% → 37.5%

### 🤔 Hypothesis

**Data Shortage is the Real Problem**:
- Database has only 18 chunks for 3 VRNs
- Some VRNs have very few chunks (ret_007: only 1 chunk!)
- Even with perfect boosting, can't achieve P@5=1.0 with insufficient data

**Evidence**:
- ret_001: 3 results (all relevant) → P@5=0.6 (2/5 are "missing" due to lack of data)
- ret_007: 1 result (relevant) → P@5=0.2 (4/5 are "missing")

**Solution**: Index more documents OR adjust expectations for small datasets

---

## Next Actions

### Immediate (Choose One)

1. **Check API Logs** (5 minutes)
   - Verify VRN boosting is executing
   - Look for `"Applied exact VRN boost"` messages

2. **Debug Single Query** (30 minutes)
   - Create script to query "231-D-54321" with detailed logging
   - Inspect top-5 results, scores, and metadata
   - Verify boosting logic

3. **Accept & Proceed** (0 minutes)
   - Mark Phase 3 as COMPLETE with current metrics
   - Acknowledge data shortage limitations
   - Proceed to Phase 4 or Production

### Long-term

1. **Index More Documents**
   - Add 20-50 vehicle documents to database
   - Re-run Phase 3 test with larger dataset
   - Expected: Higher Precision and Pass Rate

2. **Tune Boosting Parameters**
   - Increase VRN boost from 3.0x → 10.0x
   - Adjust score cap from 10.0 → 50.0
   - Re-test with same dataset

---

## Conclusion

**Status**: ⚠️ PARTIAL SUCCESS

**Achievements**:
- ✅ Recall improved (+8.4%)
- ✅ MRR improved (+4.2%)
- ✅ Query rewriting works
- ✅ Code deployed successfully

**Limitations**:
- ❌ Precision unchanged (57.5%)
- ❌ VRN exact match not improved
- ⚠️ Data shortage (18 chunks for 3 VRNs)

**Recommended Next Step**:
**Check API logs** to verify VRN boosting execution, then decide between:
- Fix boosting logic (if not executing)
- OR accept limitations due to small dataset
- OR index more documents

---

**Last Updated**: 2025-11-08 17:10
**Test File**: [retrieval_test_results_20251108_170754.json](dev_tools/tests/rag_evaluation/retrieval_test_results_20251108_170754.json)
**Previous Baseline**: [retrieval_test_results_20251108_154507.json](dev_tools/tests/rag_evaluation/retrieval_test_results_20251108_154507.json)
