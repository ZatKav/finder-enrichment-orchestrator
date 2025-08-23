# 🚀 Synchronous Property Listing Enrichment - Implementation Plan

## 📋 **Project Overview**

**Goal**: Replace the existing asynchronous background orchestrator with synchronous processing optimized for serverless environments.

**Current State**: Async background orchestrator with job polling (problematic in serverless due to timeouts)

**Target State**: Synchronous API endpoints that process listings immediately and return results

## 🎯 **Requirements & Decisions**

### **Core Requirements**
- ✅ **Big Bang Migration**: Complete replacement of async orchestrator
- ✅ **Single Listing Focus**: Primary endpoint for individual listing enrichment
- ✅ **Serverless Optimized**: Handle up to 300 seconds processing time (Vercel limit)
- ✅ **Error Resilience**: Continue processing other listings if one fails
- ✅ **Batch Support**: Optional batch processing (for future use)
- ✅ **Client Compatibility**: Maintain similar API structure where possible
- ✅ **Test Updates**: Update all tests for synchronous pattern

### **Technical Constraints**
- **Processing Time**: 300 seconds per listing (depending on image count)
- **Environment**: Vercel serverless functions (30s typical, 300s max)
- **Architecture**: Synchronous request/response pattern
- **Error Handling**: Continue on individual failures, don't fail entire batch

### **Success Criteria**
- Single listing enrichment: < 10 seconds for typical listings
- Heavy listings (40+ images): < 150 seconds
- Error rate: < 1% for valid requests
- Test coverage: 90%+ code coverage
- Availability: 99.9% uptime

## 🏗️ **Implementation Architecture**

### **New File Structure**
```
src/finder_enrichment/
├── services/
│   └── synchronous_enrichment_service.py    # Core sync service
├── api/
│   ├── routers/
│   │   ├── enrichment.py                     # NEW: Sync enrichment endpoints
│   │   └── orchestration.py                  # Keep for legacy support
│   ├── models.py                            # Add new response models
│   └── api_server.py                        # Update app initialization
```

### **Key Components**

#### **1. SynchronousEnrichmentService**
```python
class SynchronousEnrichmentService:
    def enrich_listing(self, listing_id: str) -> EnrichmentResult:
        """Enrich single listing with timeout handling"""

    def enrich_listings_batch(self, listing_ids: List[str]) -> List[EnrichmentResult]:
        """Enrich multiple listings, continue on errors"""

    def enrich_description(self, description: str) -> str:
        """Run the description analyser agent on the description"""

    def enrich_images(self, images: List[str]) -> List[str]:
        """Run the image analyser agent on the images"""

    def enrich_floorplan(self, location: str) -> str:
        """TBA Run the location analyser agent on the location"""
```

#### **2. New Response Models**
```python
class EnrichmentResult:
    listing_id: str
    status: str  # "success", "failed", "timeout"
    enriched_data: Optional[EnrichedListing]
    error_message: Optional[str]
    processing_time_seconds: float
    image_count: int
    timestamp: datetime

class BatchEnrichmentResult:
    results: List[EnrichmentResult]
    total_processed: int
    total_failed: int
    total_successful: int
    processing_time_seconds: float
```

#### **3. New API Endpoints**
```python
# Individual listing enrichment
POST /api/enrich-listing/{listing_id}
# Returns: EnrichmentResult immediately

# Batch enrichment (optional)
POST /api/enrich-listings
# Body: { "listing_ids": ["id1", "id2"] }
# Returns: BatchEnrichmentResult
```

## 📊 **Implementation Phases**

### **Phase 1: Foundation**
1. **Create SynchronousEnrichmentService** - Extract logic from existing orchestrator
2. **Add proper timeout handling** - 150 second limit with graceful degradation
3. **Implement error resilience** - Continue processing on individual failures
4. **Add logging and monitoring** - Comprehensive observability

### **Phase 2: API Layer**
1. **Create new enrichment router** (`/api/routers/enrichment.py`)
2. **Add request/response models** to `api/models.py`
3. **Implement authentication** - Reuse existing API key system
4. **Add input validation** and error handling

### **Phase 3: Integration & Testing**
1. **Update existing API client** to work with new endpoints
2. **Write comprehensive unit tests** for sync service
3. **Write integration tests** for new endpoints

### **Phase 4: Documentation**
1. **Update documentation** and API specs
2. **Performance optimization** for serverless

## 🔧 **Technical Implementation Details**

### **Timeout Strategy**
```python
@router.post("/enrich-listing/{listing_id}")
async def enrich_listing(
    listing_id: str,
    api_key: str = Depends(require_api_key)
):
    try:
        # Wait with 150 second timeout
        result = await asyncio.wait_for(
            enrichment_service.enrich_listing(listing_id),
            timeout=150.0
        )
        return result
    except asyncio.TimeoutError:
        return EnrichmentResult(
            listing_id=listing_id,
            status="timeout",
            error_message="Processing exceeded 150 second limit",
            processing_time_seconds=150.0
        )
```

### **Error Handling Strategy**
```python
def enrich_listings_batch(self, listing_ids: List[str]) -> List[EnrichmentResult]:
    results = []
    for listing_id in listing_ids:
        try:
            result = self.enrich_listing(listing_id)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to enrich listing {listing_id}: {e}")
            results.append(EnrichmentResult(
                listing_id=listing_id,
                status="failed",
                error_message=str(e),
                processing_time_seconds=0
            ))
    return results
```

### **Client Updates**
Keep the existing `OrchestratorAPIClient` structure:

```python
# Update existing method to use sync endpoint
def enrich_listing(self, listing_id: str) -> EnrichmentResult:
    response = self._post(f"/enrich-listing/{listing_id}")
    return EnrichmentResult(**response)

# Add new batch method
def enrich_listings_batch(self, listing_ids: List[str]) -> BatchEnrichmentResult:
    response = self._post("/enrich-listings", json={"listing_ids": listing_ids})
    return BatchEnrichmentResult(**response)
```

## 🧪 **Testing Strategy**

### **Unit Tests**
- **Service layer**: Test enrichment logic with basic mocks
- **Timeout handling**: Test 300 second limit behavior
- **Error resilience**: Test continuation on failures
- **Data validation**: Test input/output models

### **Integration Tests**
- **API endpoints**: Full request/response cycle
- **Authentication**: API key and auth validation
- **Error responses**: Proper HTTP status codes

## 📋 **Migration Checklist**

### **Pre-Implementation**
- [ ] Analyze current orchestrator logic to extract reusable components
- [ ] Identify all data models and dependencies
- [ ] Plan test data and scenarios
- [ ] Set up monitoring and alerting

### **Implementation**
- [ ] Create SynchronousEnrichmentService
- [ ] Implement core enrichment logic
- [ ] Add timeout and error handling
- [ ] Create new enrichment router
- [ ] Add response models
- [ ] Update API client
- [ ] Implement authentication

### **Testing**
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Load testing
- [ ] Error scenario testing
- [ ] Timeout testing

### **Migration**
- [ ] Update existing tests
- [ ] Remove old orchestrator code
- [ ] Update documentation
- [ ] Performance optimization
- [ ] Production deployment

## 🎯 **Ready to Implement**

This specification provides everything needed to implement the synchronous enrichment system:

- **Clear requirements** and success criteria
- **Detailed architecture** and file structure
- **Implementation phases** with specific tasks
- **Code examples** and patterns
- **Testing strategy** and success metrics
- **Migration plan** and checklist

The new system will be optimized for serverless environments while maintaining the core enrichment functionality and providing a much more reliable and debuggable architecture.
