# Integration Tests for Synchronous Enrichment

This directory contains integration tests that test the synchronous enrichment system against real external services.

## Test Files

### Unit Tests (Mock-based)
- `test_synchronous_enrichment_service.py` - Unit tests for the core enrichment service
- `test_enrichment_models.py` - Tests for API response models
- `test_enrichment_api.py` - API endpoint tests with mocking
- `test_orchestrator_api_client.py` - API client tests with mocking

### Integration Tests (Real Services)
- `test_synchronous_enrichment_api.py` - Tests synchronous enrichment endpoints against real services
- `test_synchronous_orchestration_api.py` - Tests full orchestration process against real services
- `test_image_analyser_api.py` - Tests image analysis against real services (existing)
- `test_description_analyser_api.py` - Tests description analysis against real services (existing)

## Running Integration Tests

### Prerequisites

1. **Environment Variables**: Set up all required environment variables:
   ```bash
   export ORCHESTRATOR_BASE_URL="http://localhost:3100"
   export ORCHESTRATOR_API_KEY="your-api-key-here"

   export LISTINGS_DB_BASE_URL="https://your-listings-db-url"
   export LISTINGS_DB_API_KEY="your-listings-db-key"

   export ENRICHMENT_DB_BASE_URL="https://your-enrichment-db-url"
   export ENRICHMENT_DB_API_KEY="your-enrichment-db-key"

   export GOOGLE_GEMINI_API_KEY="your-google-ai-key"
   ```

2. **Running Services**: Ensure all external services are running and accessible:
   - Listings Database API
   - Enrichment Database API
   - Google AI API (for image and description analysis)

3. **Local Orchestrator**: The tests expect the orchestrator API to be running locally on port 3100.

### Running Tests

#### Run All Integration Tests
```bash
cd /Users/giacomokavanagh/github/finder/finder-enrichment-orchestrator
uv run python -m pytest src/finder_enrichment/tests/test_synchronous_enrichment_api.py -v
uv run python -m pytest src/finder_enrichment/tests/test_synchronous_orchestration_api.py -v
```

#### Run Specific Test Categories

```bash
# Test synchronous enrichment endpoints
uv run python -m pytest src/finder_enrichment/tests/test_synchronous_enrichment_api.py::test_synchronous_single_listing_enrichment_integration -v

# Test full orchestration process
uv run python -m pytest src/finder_enrichment/tests/test_synchronous_orchestration_api.py::test_full_synchronous_orchestration_process -v

# Test performance baseline
uv run python -m pytest src/finder_enrichment/tests/test_synchronous_orchestration_api.py::test_synchronous_orchestration_performance_baseline -v

# Test error recovery
uv run python -m pytest src/finder_enrichment/tests/test_synchronous_orchestration_api.py::test_synchronous_orchestration_error_recovery -v
```

#### Run with Custom Timeout
```bash
# For tests that might take longer due to AI processing
uv run python -m pytest src/finder_enrichment/tests/test_synchronous_enrichment_api.py -v --timeout=300
```

### Test Coverage

#### Integration Tests Cover:
- ✅ **Real API Endpoints**: Tests actual HTTP endpoints running locally
- ✅ **External Service Integration**: Tests against real Listings DB, Enrichment DB, and Google AI
- ✅ **Authentication**: Tests API key authentication and error handling
- ✅ **Rate Limiting**: Tests rate limiting behavior
- ✅ **Error Handling**: Tests various error conditions and recovery
- ✅ **Database Operations**: Tests actual database record creation and retrieval
- ✅ **Performance**: Establishes performance baselines for monitoring
- ✅ **Full Orchestration**: Tests the complete enrichment pipeline

#### Unit Tests Cover:
- ✅ **Service Logic**: Tests business logic with mocked dependencies
- ✅ **Model Validation**: Tests data models and validation
- ✅ **Edge Cases**: Tests boundary conditions and unusual inputs
- ✅ **Error Scenarios**: Tests error handling without external dependencies

### Test Data Requirements

The integration tests require:
1. At least one listing in the Listings Database
2. Valid API keys for all external services
3. Network connectivity to all external services
4. Sufficient quota/limits for AI API calls

### Expected Test Results

#### Successful Run
```bash
==================================== test session starts =====================================
collected 6 items

src/finder_enrichment/tests/test_synchronous_enrichment_api.py::test_synchronous_enrichment_health_check PASSED
src/finder_enrichment/tests/test_synchronous_enrichment_api.py::test_synchronous_single_listing_enrichment_integration PASSED
src/finder_enrichment/tests/test_synchronous_enrichment_api.py::test_synchronous_batch_listing_enrichment_integration PASSED
src/finder_enrichment/tests/test_synchronous_enrichment_api.py::test_synchronous_enrichment_with_invalid_listing PASSED
src/finder_enrichment/tests/test_synchronous_enrichment_api.py::test_synchronous_enrichment_authentication PASSED
src/finder_enrichment/tests/test_synchronous_enrichment_api.py::test_synchronous_enrichment_rate_limiting PASSED

==================================== 6 passed in 45.32s ========================================
```

#### Performance Expectations
- **Health Check**: < 1 second
- **Single Listing**: 10-60 seconds (depending on image count)
- **Batch Processing**: 30-180 seconds (depending on batch size and images)
- **Invalid Listing**: < 5 seconds

### Troubleshooting

#### Common Issues

1. **Connection Errors**: Check that all external services are running and accessible
2. **Authentication Errors**: Verify API keys are correct and have sufficient permissions
3. **Timeout Errors**: Increase timeout values or check network connectivity
4. **Database Errors**: Ensure database services are running and have test data
5. **AI API Errors**: Check API quotas and ensure keys have access to required models

#### Debug Mode
```bash
# Run with debug output
uv run python -m pytest src/finder_enrichment/tests/test_synchronous_enrichment_api.py -v -s --log-cli-level=DEBUG
```

### Continuous Integration

These integration tests should be run:
- After any changes to the synchronous enrichment service
- Before production deployments
- As part of regular regression testing
- When external service contracts change

### Test Environment Setup

For automated testing environments:
1. Set up test databases with known test data
2. Use dedicated API keys for testing
3. Mock AI services for faster test execution when possible
4. Implement proper cleanup to avoid test data pollution
