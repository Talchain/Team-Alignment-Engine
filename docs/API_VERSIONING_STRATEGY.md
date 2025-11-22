# TAE API Versioning Strategy

## Overview

Team Alignment Engine (TAE) uses **URL-based semantic versioning** for its REST API to ensure backward compatibility and smooth transitions between API versions.

## Versioning Scheme

### Current Version
- **API Version**: `v1`
- **URL Prefix**: `/api/v1/`
- **Service Version**: `2.0.0` (from pyproject.toml)

### Semantic Versioning Rules

We follow semantic versioning for both the API and service:
- **Major version (v1, v2)**: Breaking changes that are not backward compatible
- **Minor version (service 2.x.0)**: New features, backward compatible
- **Patch version (service 2.0.x)**: Bug fixes, backward compatible

## API Version Lifecycle

### v1 (Current - Stable)
**Status**: Production
**Release Date**: 2025-11
**Endpoints**: All Phase A-D endpoints
**Deprecation Date**: TBD (minimum 12 months after v2 release)
**Sunset Date**: TBD (minimum 18 months after v2 release)

### v2 (Future)
**Status**: Not yet planned
**Expected Changes**: TBD
**Planned Release**: When breaking changes are necessary

## Breaking vs Non-Breaking Changes

### Breaking Changes (Require New Major Version)
- Removing endpoints
- Removing request/response fields
- Changing field types
- Renaming fields
- Changing authentication mechanisms
- Changing error response formats

### Non-Breaking Changes (Can Be Added to Current Version)
- Adding new endpoints
- Adding optional request fields
- Adding response fields
- Adding new enum values (with defaults)
- Performance improvements
- Bug fixes

## Deprecation Policy

### Timeline
1. **Announcement** (T+0): Deprecation notice in release notes, API documentation, and response headers
2. **Warning Period** (T+6 months): `Deprecation` header added to affected endpoints
3. **Support End** (T+12 months): Feature marked as deprecated but still functional
4. **Sunset** (T+18 months): Feature removed from API

### Deprecation Headers
```http
Deprecation: Sun, 01 Jan 2026 00:00:00 GMT
Sunset: Sun, 01 Jul 2026 00:00:00 GMT
Link: <https://docs.tae.olumi.com/api/v2/migration>; rel="successor-version"
```

## Version Detection

Clients should:
1. **Always specify version in URL**: `/api/v1/alignment/sessions`
2. **Check response headers** for deprecation warnings
3. **Monitor `X-API-Version` header** in responses

Example response header:
```http
X-API-Version: v1
X-Service-Version: 2.0.0
```

## Migration Guide

When migrating to a new major version:

1. **Read Migration Documentation**
   - Review breaking changes
   - Update client code
   - Run tests against new version

2. **Test in Parallel**
   - Run both v1 and v2 clients side-by-side
   - Validate results match expected behavior
   - Monitor error rates

3. **Gradual Rollout**
   - Migrate non-critical services first
   - Monitor performance and error rates
   - Rollback plan ready

4. **Complete Migration**
   - Migrate all clients before v1 sunset
   - Remove v1 dependencies
   - Monitor for any issues

## Version Support Matrix

| Version | Status | Support Level | Sunset Date |
|---------|--------|---------------|-------------|
| v1 | Stable | Full support | TBD |
| v2 | Not released | N/A | N/A |

## Endpoint Stability Levels

Each endpoint may have different stability levels:

### Stable
- Production-ready
- Covered by deprecation policy
- Full backward compatibility guarantee

Example: `/api/v1/alignment/sessions`

### Beta
- Feature-complete but may change
- 30-day notice for breaking changes
- Not recommended for production critical paths

Example: `/api/v1/plot/alignment-session` (PLoT Integration POC v02)

### Alpha
- Experimental
- May change without notice
- Not recommended for production

Example: Future experimental endpoints

## Client Recommendations

### 1. Version Pinning
Always use explicit version in API calls:
```python
BASE_URL = "https://tae.olumi.com/api/v1"
```

### 2. Error Handling
Handle version-related errors gracefully:
```python
if response.status_code == 410:  # Gone
    # Version sunset - migrate to new version
    raise VersionSunsetError("API v1 no longer supported")
```

### 3. Health Monitoring
Monitor deprecation headers:
```python
deprecation = response.headers.get("Deprecation")
if deprecation:
    logger.warning(f"API deprecation warning: {deprecation}")
```

## Contact & Support

For API versioning questions:
- **Documentation**: https://docs.tae.olumi.com/api
- **Migration Support**: api-support@olumi.com
- **Changelog**: https://github.com/olumi/tae/blob/main/CHANGELOG.md

## Version History

| Version | Release Date | Major Changes |
|---------|--------------|---------------|
| v1.0.0 | 2025-11-01 | Initial release (Phases A-B) |
| v1.1.0 | 2025-11-15 | Phase C (Intelligent Assistance) |
| v1.2.0 | 2025-11-20 | Phase D (Organizational Intelligence) |
| v2.0.0 | TBD | Future breaking changes |

---

**Last Updated**: 2025-11-22
**Document Version**: 1.0
