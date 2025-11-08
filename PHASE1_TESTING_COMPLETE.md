# Phase 1: Database Snapshot - COMPLETE

## Summary

Successfully implemented Phase 1 of the RAG testing implementation plan: Database snapshot script and ground truth validation.

## What Was Done

### 1. Database Snapshot Script Created ✅

**File**: [dev_tools/scripts/diagnostics/snapshot_database.py](dev_tools/scripts/diagnostics/snapshot_database.py)

**Functionality**:
- Connects to Supabase PostgreSQL database
- Extracts comprehensive database statistics:
  - All document filenames from `vecs.document_registry`
  - All VRNs from document content and metadata
  - Document count by type and status
  - Total vector chunks from `vecs.documents`
  - Vehicle information from `vecs.vehicles` table
  - Entity extraction (owners, makes, models) from metadata

**Output**: [dev_tools/datasets/ground_truth/database_snapshot.json](dev_tools/datasets/ground_truth/database_snapshot.json)

**Usage**:
```bash
python dev_tools/scripts/diagnostics/snapshot_database.py
```

### 2. Database Snapshot Results

Current database state (as of 2025-11-08):

```
Total Documents:      6
Total Chunks:         18
Unique VRNs:          3

Documents in registry:
- VCR - Copy.docx
- VCR2.docx
- CVRT Pass Statement.pdf
- certificate-of-motor-insurance2025.pdf
- VCR.docx
- Vehicle Registration Certificate.pdf

VRNs Found:
- 141-D-98765
- 231-D-54321
- 231-D-54329

Document Status:
- processed: 1
- assigned: 5

Vehicles in vehicles table:
- 141-D-98765 (no make/model data yet)
- 231-D-54321 (no make/model data yet)
- 231-D-54329 (no make/model data yet)
```

### 3. Ground Truth Validation ✅

**File Updated**: [dev_tools/datasets/ground_truth/vehicle_queries.json](dev_tools/datasets/ground_truth/vehicle_queries.json)

**Changes Made**:
1. **Version updated**: 1.0 → 1.1
2. **Added validation metadata**:
   - `last_validated: "2025-11-08"`
   - `validated_against: "database_snapshot.json"`
   - `database_vrns`, `database_documents`, `database_chunks`

3. **Updated test cases to match reality**:
   - `agg_001`: Changed expected count from 4 to 3 vehicles
   - `entity_001`: Changed to "Show me all VCR documents" (entity data not populated)
   - `semantic_001`: Changed to "Tell me about vehicle 141-D-98765" (matches DB)
   - `semantic_002`: Changed to "Show me insurance information" (matches available docs)
   - `doc_001`: Updated filename to `.pdf` (was `.md`)
   - `doc_002`: Changed to `expected_answer_may_contain` for flexible date matching
   - `complex_001`: Changed to "What documents do we have for vehicle 141-D-98765?"

4. **All test cases now reference**:
   - VRNs that exist in database: 141-D-98765, 231-D-54321, 231-D-54329
   - Documents that exist: VCR.docx, CVRT Pass Statement.pdf, certificate-of-motor-insurance2025.pdf
   - No made-up entities (Murphy Builders, Ford Transit, etc.)

## Key Findings

### Database Observations

1. **Document Types Not Set**: All 6 documents have `document_type: unknown`
   - Should be classified as: insurance, nct_certificate, registration_document, etc.

2. **Entity Data Not Populated**: vehicles table has no make/model information
   - VIN fields are NULL
   - Make/model fields are NULL
   - Current driver assignments are NULL

3. **Extracted Data Empty**: `extracted_data` field in `document_registry` appears empty
   - Metadata extraction may not be running
   - VRN extraction working (found 3 VRNs from content)

4. **Processing Status**: Mixed status
   - 1 document marked as "processed"
   - 5 documents marked as "assigned"
   - May need status reconciliation

### Test Case Adjustments

**Why adjustments were needed**:
- Original ground truth assumed richer metadata (owners, makes, models)
- Original ground truth assumed 4 vehicles (database has 3)
- Original ground truth used `.md` extensions (database has `.pdf`/`.docx`)
- Original ground truth included non-existent VRN (231-D-55555)

**Impact on testing**:
- Tests are now realistic and will PASS with current database
- Tests validate actual system capabilities (not aspirational features)
- Tests can detect regressions in VRN extraction and document retrieval

## Next Steps

According to [TESTING_IMPLEMENTATION_PLAN.md](TESTING_IMPLEMENTATION_PLAN.md):

### Immediate (Week 1)
- ✅ Read RAG_TESTING_GUIDE.md
- ✅ Review vehicle_queries.json ground truth
- ✅ Implement snapshot_database.py
- ✅ Update ground truth based on database snapshot
- **Next**: Implement smoke_test.py (5 critical queries, < 1 minute execution)

### Week 2
- Implement test_retrieval.py (retrieval quality metrics)
- Run retrieval tests on current system
- Establish baseline metrics

### Week 3
- Implement test_faithfulness.py (hallucination detection)
- Implement run_full_suite.py (all 15 test cases)
- Generate first comprehensive report

## Files Modified/Created

### Created
1. `dev_tools/scripts/diagnostics/snapshot_database.py` - Database snapshot tool
2. `dev_tools/datasets/ground_truth/database_snapshot.json` - Current DB state
3. `PHASE1_TESTING_COMPLETE.md` (this file) - Phase 1 summary

### Modified
1. `dev_tools/datasets/ground_truth/vehicle_queries.json` - Ground truth validation
   - Version: 1.0 → 1.1
   - 7 test cases updated to match database reality
   - Metadata section enhanced with validation info

## Testing the Snapshot Script

To verify snapshot script works on your system:

```bash
# From project root
python dev_tools/scripts/diagnostics/snapshot_database.py

# Check output
cat dev_tools/datasets/ground_truth/database_snapshot.json
```

**Expected Output**:
- Database connection success
- 6 documents listed
- 18 chunks counted
- 3 VRNs extracted
- 3 vehicles listed
- JSON file saved successfully

## Recommendations

### Before Phase 2 (Smoke Test)

1. **Populate Entity Data** (Optional but recommended):
   - Run metadata extraction on existing documents
   - Update vehicles table with make/model information
   - This will enable richer test cases in future

2. **Set Document Types** (Optional):
   - Classify documents in `document_registry.document_type`
   - Enables testing of document-type-specific queries

3. **Verify Document Processing** (Important):
   - Confirm all 6 documents are fully indexed (status="processed")
   - Check that chunks exist for all documents
   - Run: `SELECT registry_id, COUNT(*) FROM vecs.documents GROUP BY registry_id`

### For Production Deployment

1. **Automate Snapshot**:
   - Run snapshot script before each test suite execution
   - Include snapshot in CI/CD pipeline
   - Track database growth over time

2. **Monitor Test/Reality Drift**:
   - Re-run snapshot monthly
   - Update ground truth when database changes significantly
   - Version ground truth datasets (1.0, 1.1, 2.0, etc.)

## Success Criteria Met ✅

From TESTING_IMPLEMENTATION_PLAN.md Phase 1:

- ✅ Script connects to database successfully
- ✅ Extracts all document filenames
- ✅ Extracts all VRNs mentioned
- ✅ Counts documents by type
- ✅ Identifies available entities
- ✅ Saves to database_snapshot.json
- ✅ Ground truth validated against snapshot
- ✅ Test cases updated to match reality

**Phase 1 Status**: COMPLETE
**Ready for Phase 2**: YES (Smoke Test Implementation)
