# Team Alignment Engine (TAE) - Database Integration Proposal

**Version**: 1.0
**Date**: 2025-11-23
**Status**: DRAFT - Awaiting Workstream Review
**Author**: TAE Development Team

---

## 🎯 Purpose

This document proposes the database schema for the Team Alignment Engine (TAE) workstream to integrate with the shared Olumi Supabase database. **We need input from all workstreams** to ensure:

1. **No naming conflicts** with existing tables
2. **Shared resources** (users, organizations) are properly referenced
3. **Optimal architecture** for multi-workstream platform
4. **Scalability** for future Olumi workstreams

---

## 📊 Current State Assessment

### Step 1: Run Diagnostic SQL

**Action Required**: Run `SUPABASE_DIAGNOSTIC.sql` in your Supabase SQL Editor and share results.

This will show:
- All existing tables in Supabase
- Potential naming conflicts
- Current foreign key relationships
- Existing schema isolation (if any)
- Row-level security status

---

## 🏗️ TAE Proposed Schema

TAE proposes adding **21 new tables** across 5 functional areas:

### **Area 1: Core Decision Alignment (7 tables)**

Purpose: Manage team decision sessions, stakeholder profiles, and option evaluation

| Table Name | Purpose | Key Data | References |
|------------|---------|----------|------------|
| `sessions` | Decision-making sessions | session_id, decision_topic, status | team_id, created_by |
| `profiles` | Stakeholder profiles per session | goals, concerns, constraints | session_id, user_id |
| `options` | Decision options proposed | title, description, causal_rationale | session_id |
| `validations` | Causal validation results | validation_status, predicted_outcomes | option_id |
| `fits` | Stakeholder-option fit scores | alignment scores, consensus_level | option_id |
| `concerns` | Raised concerns on options | concern_text, status, resolution | option_id, raised_by |
| `decision_briefs` | Final decision documentation | rationale, consensus_strength | session_id |

**Potential Conflicts**: `sessions`, `profiles`, `options` are generic names

---

### **Area 2: Deliberation (Phase 1 - Habermas Machine) (5 tables)**

Purpose: Multi-round team deliberation with anonymous voting

| Table Name | Purpose | Key Data | References |
|------------|---------|----------|------------|
| `deliberation_sessions` | Deliberation session container | decision_context, participants | None (standalone session_id) |
| `deliberation_rounds` | Individual rounds in session | round_type, synthesis_options | session_id |
| `deliberation_submissions` | User causal graph submissions | graph, reasoning, quality_score | round_id, user_id |
| `deliberation_votes` | Anonymous ranked votes | encrypted_user_id, rankings | round_id (encrypted for privacy) |
| `deliberation_conflicts` | Detected conflicts | conflict_analysis, resolution | session_id, round_id |

**Privacy Note**: `deliberation_votes.encrypted_user_id` uses AES-256-GCM encryption to preserve anonymity during active voting.

---

### **Area 3: Aggregation Intelligence (Phase 3 - Navajas) (2 tables)**

Purpose: Track user prediction accuracy for optimal team sizing

| Table Name | Purpose | Key Data | References |
|------------|---------|----------|------------|
| `user_accuracy_history` | Historical prediction tracking | brier_score, confidence_error | user_id, session_id |
| `user_domain_expertise` | Domain-specific expertise scores | accuracy, overconfidence_bias | user_id |

---

### **Area 4: Organizational Intelligence (Phase D) (5 tables)**

Purpose: Cross-session analytics and coordination

| Table Name | Purpose | Key Data | References |
|------------|---------|----------|------------|
| `decision_dependencies` | Links between related decisions | source/target sessions | session_id (FK) |
| `pattern_analysis_cache` | Common decision patterns | pattern_type, recommendations | organization_id |
| `coordination_groups` | Multi-session coordination | session_ids array | None |
| `detected_conflicts` | Cross-session conflicts | conflict_type, severity | None |
| `analytics_cache` | Performance analytics cache | metric_name, result_data | organization_id |

---

### **Area 5: Learning & Retrospectives (2 tables)**

Purpose: Post-decision learning and assumption tracking

| Table Name | Purpose | Key Data | References |
|------------|---------|----------|------------|
| `assumption_validations` | Validate key assumptions | validation_method, result | session_id |
| `decision_retrospectives` | Post-decision reviews | actual_outcomes, lessons_learned | session_id, brief_id |

---

## 🔗 Shared Resource Dependencies

TAE **requires** the following shared resources (assumed to exist in Olumi platform):

| Resource | Used In TAE Tables | Purpose |
|----------|-------------------|---------|
| `users` table | sessions.created_by, profiles.user_id, deliberation_submissions.user_id | User authentication & identity |
| `organizations` table | sessions.organization_id, pattern_analysis_cache.organization_id | Multi-tenancy |
| `teams` table | sessions.team_id | Team-based decision sessions |

**Critical Questions:**
1. ✅ Do these shared tables exist? What are their primary keys?
2. ✅ What's the relationship between users → teams → organizations?
3. ✅ Should TAE use existing auth or implement its own?

---

## ⚠️ Naming Conflict Analysis

### **High Risk Conflicts** (Generic Names)

These table names are likely to conflict with other workstreams:

- `sessions` - Very generic, likely used by other workstreams
- `profiles` - Could conflict with user profile tables
- `options` - Generic name for choices/settings
- `validations` - Generic validation tracking

### **Proposed Solutions**

**Option A: Schema Isolation** (Recommended)
```sql
CREATE SCHEMA tae;

-- All TAE tables in tae schema
CREATE TABLE tae.sessions (...);
CREATE TABLE tae.deliberation_sessions (...);

-- Clean separation, no naming conflicts
-- Access via: SELECT * FROM tae.sessions
```

**Option B: Table Prefixing**
```sql
-- All TAE tables prefixed with tae_
CREATE TABLE tae_sessions (...);
CREATE TABLE tae_deliberation_sessions (...);

-- Simpler but clutters public schema
```

**Option C: Separate Database**
```sql
-- TAE gets its own database: tae_db
-- Shared auth/users in: olumi_platform_db
-- Cross-database queries via foreign data wrappers
```

**Recommendation**: **Option A (Schema Isolation)** provides best balance of clarity, isolation, and maintainability.

---

## 📐 Proposed Architecture

### **Recommended: Schema-Based Isolation**

```
Supabase Database
├── public schema (shared Olumi resources)
│   ├── users
│   ├── organizations
│   ├── teams
│   └── [other shared tables]
│
├── tae schema (Team Alignment Engine)
│   ├── sessions
│   ├── deliberation_sessions
│   ├── user_accuracy_history
│   └── [all 21 TAE tables]
│
├── [workstream2] schema
│   └── [workstream2 tables]
│
└── [workstream3] schema
    └── [workstream3 tables]
```

**Benefits:**
- ✅ Zero naming conflicts
- ✅ Clear ownership boundaries
- ✅ Easy to manage permissions (GRANT on schema)
- ✅ Scalable for future workstreams
- ✅ Easier to backup/restore individual workstreams

**Foreign Key Example:**
```sql
CREATE TABLE tae.sessions (
    session_id UUID PRIMARY KEY,
    team_id UUID REFERENCES public.teams(id),
    created_by UUID REFERENCES public.users(id),
    organization_id UUID REFERENCES public.organizations(id)
);
```

---

## 🔒 Security & Access Control

### **Row-Level Security (RLS) Considerations**

TAE tables should enforce:

1. **Organization Isolation**: Users only see data from their organization
2. **Team Access**: Users only access sessions for their teams
3. **Anonymous Voting**: `deliberation_votes` encrypted, no direct user_id access during active voting

**Example RLS Policy:**
```sql
-- Only show sessions from user's organization
ALTER TABLE tae.sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY org_isolation ON tae.sessions
    FOR ALL
    USING (organization_id IN (
        SELECT organization_id FROM public.users WHERE id = auth.uid()
    ));
```

**Question for Workstreams**: What RLS patterns are already in use for `users`, `organizations`, `teams`?

---

## 📊 Performance Considerations

### **Indexing Strategy**

TAE requires 15+ indexes for optimal query performance:

**Critical Indexes:**
```sql
-- High-frequency queries
CREATE INDEX idx_sessions_org_status ON tae.sessions (organization_id, status);
CREATE INDEX idx_deliberation_sessions_created ON tae.deliberation_sessions (created_at DESC);
CREATE INDEX idx_user_accuracy_user_domain ON tae.user_accuracy_history (user_id, domain);

-- Foreign key indexes
CREATE INDEX idx_sessions_team_id ON tae.sessions (team_id);
CREATE INDEX idx_profiles_user_id ON tae.profiles (user_id);
```

**Composite Indexes (Phase D Analytics):**
```sql
CREATE INDEX idx_sessions_org_type_completed
    ON tae.sessions (organization_id, decision_type, completed_at)
    WHERE status = 'complete';
```

**Question**: What's current index count? Should we be concerned about total index overhead?

---

## 💾 Storage Estimates

### **Expected Data Volume (Year 1)**

| Table | Estimated Rows | Size per Row | Total |
|-------|----------------|--------------|-------|
| `tae.sessions` | 10,000 | ~2 KB | 20 MB |
| `tae.deliberation_sessions` | 5,000 | ~1 KB | 5 MB |
| `tae.deliberation_submissions` | 50,000 | ~3 KB (with graphs) | 150 MB |
| `tae.user_accuracy_history` | 100,000 | ~500 B | 50 MB |
| **TOTAL (all tables)** | ~200,000 | - | **~300 MB** |

**With Indexes**: ~450 MB total (Year 1)

**Supabase Free Tier**: 500 MB database (would need paid plan if other workstreams also heavy)

---

## 🔄 Migration Strategy

### **Phased Rollout**

**Phase 1: Shared Infrastructure** (Week 1)
```sql
-- Ensure shared tables exist
CREATE TABLE IF NOT EXISTS public.users (...);
CREATE TABLE IF NOT EXISTS public.organizations (...);
CREATE TABLE IF NOT EXISTS public.teams (...);
```

**Phase 2: TAE Schema Creation** (Week 1)
```sql
CREATE SCHEMA tae;
GRANT USAGE ON SCHEMA tae TO authenticated;
```

**Phase 3: TAE Tables - Core** (Week 2)
```sql
-- Core decision alignment tables (7 tables)
CREATE TABLE tae.sessions (...);
CREATE TABLE tae.profiles (...);
-- ...
```

**Phase 4: TAE Tables - Deliberation** (Week 3)
```sql
-- Deliberation tables (5 tables)
CREATE TABLE tae.deliberation_sessions (...);
-- ...
```

**Phase 5: TAE Tables - Analytics** (Week 4)
```sql
-- Phase D organizational intelligence (5 tables)
CREATE TABLE tae.pattern_analysis_cache (...);
-- ...
```

---

## ✅ Decision Points for Workstream Leads

### **Questions Requiring Cross-Workstream Alignment**

1. **Schema Isolation**: Do we adopt schema-based isolation for all workstreams?
   - [ ] Yes - Each workstream gets its own schema (recommended)
   - [ ] No - Use table prefixing instead
   - [ ] Other - Specify: _____________

2. **Shared Tables**: Which tables are shared across Olumi?
   - [ ] users, organizations, teams (confirm structure)
   - [ ] Add: _____________
   - [ ] None - Each workstream fully independent

3. **Authentication**: Single auth system or per-workstream?
   - [ ] Shared Supabase Auth (with custom claims for workstreams)
   - [ ] Per-workstream JWT auth
   - [ ] Other: _____________

4. **RLS Policies**: Organization-level or team-level isolation?
   - [ ] Organization-level (users see all data in their org)
   - [ ] Team-level (users only see their team's data)
   - [ ] Mixed (depends on table)

5. **Naming Conflicts**: Any existing tables that conflict with TAE proposals?
   - [ ] None - Proceed as proposed
   - [ ] Conflicts found: _____________

6. **Database Limits**: Expected total data volume across all workstreams?
   - [ ] < 500 MB (Supabase free tier OK)
   - [ ] 500 MB - 8 GB (Supabase Pro needed)
   - [ ] > 8 GB (Enterprise planning needed)

---

## 📋 Next Steps

### **For TAE Team**
1. ✅ Run `SUPABASE_DIAGNOSTIC.sql` and share results
2. ⏳ Await workstream feedback on this proposal
3. ⏳ Revise schema based on feedback
4. ⏳ Generate final migration SQL

### **For Other Workstream Leads**
1. ⏳ Review this proposal
2. ⏳ Share your current table names (avoid conflicts)
3. ⏳ Provide feedback on architecture decisions
4. ⏳ Confirm shared table structure (users, orgs, teams)

### **For Platform/DevOps**
1. ⏳ Assess Supabase plan requirements
2. ⏳ Review RLS policy standards
3. ⏳ Confirm backup/restore procedures
4. ⏳ Set up monitoring for query performance

---

## 📞 Contact & Feedback

**TAE Team Lead**: [Your Name]
**Slack Channel**: #tae-development
**Review Deadline**: [Date - suggest 1 week]

**Please provide feedback on**:
- Naming conflicts with your workstream
- Shared table structure confirmations
- Architecture preference (schema vs prefix vs separate DB)
- RLS policy requirements
- Any concerns or questions

---

## 📎 Appendix: Full Table Definitions

<details>
<summary>Click to expand complete SQL schema</summary>

```sql
-- Full SQL schema available in: supabase_migration.sql
-- This appendix intentionally omitted for brevity
-- See main migration file for complete table definitions
```

</details>

---

**Document Status**: DRAFT
**Next Review**: After diagnostic results and workstream feedback
**Version History**:
- v1.0 (2025-11-23): Initial proposal for workstream review
