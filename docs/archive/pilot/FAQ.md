# TAE Phase D - Pilot FAQ

**Quick answers to common questions from pilot teams.**

---

## General Questions

### What is TAE?

TAE (Team Alignment Engine) helps teams make better decisions faster using:
- Evidence-backed deliberation
- Causal validation (ISL)
- AI assistance (CEE)
- Organizational intelligence (Phase D)

### What's Phase D?

Phase D adds 6 organizational intelligence capabilities:
1. Portfolio Analytics - Multi-session insights
2. Real-Time Collaboration - WebSocket sync
3. Decision Dependencies - Graph management
4. Organizational Patterns - Learn from history
5. Advanced Analytics - Trends and forecasting
6. Cross-Team Coordination - Multi-team alignment

### Why am I in the pilot?

You're helping us test Phase D before production release. Your feedback shapes TAE's future!

### How long is the pilot?

6 weeks (with possible 2-week extension if needed).

### What happens after the pilot?

If successful, you transition to production TAE. Your data persists. If not, we iterate based on your feedback.

---

## Access & Setup

### How do I log in?

**URL:** `https://tae-staging.olumi.com`

**Credentials:** Check your pilot invite email. First-time users set password on first login.

### I forgot my password. Help!

Click "Forgot Password" on login page → Enter email → Check inbox for reset link.

If not received within 5 minutes, email tae-pilot@olumi.com.

### Can I use my own email/Google account?

Not yet. Pilot uses temporary credentials. Phase E will add SSO (SAML, Google, etc.).

### Mobile app?

No mobile app yet. Use mobile browser for now. Phase E includes native mobile apps.

### Offline access?

No offline mode currently. Internet connection required.

---

## Usage & Workflow

### How do I create a decision?

1. Click "+ New Decision" (top right)
2. Fill in topic, type, context, stakeholders
3. Click "Create Session"

See [Quick Start Guide](QUICK_START.md) for detailed walkthrough.

### Who should I add as stakeholders?

Anyone who:
- Has a perspective on the decision
- Will be impacted by the outcome
- Needs to align before implementation

**Too few = missing perspectives. Too many = slow progress.**

Sweet spot: 3-7 stakeholders.

### What's a "perspective"?

Your individual view of the decision:
- **Goals:** What you want to achieve (ranked)
- **Concerns:** What worries you
- **Constraints:** Any limitations

TAE uses perspectives to calculate fit scores and identify disagreements.

### How do options work?

Options are possible solutions to your decision. Propose 3-5 options minimum. For each:
- Name (short label)
- Description (what this means)
- Assumptions (what needs to be true)
- Trade-offs (what you're giving up)

### What's a "fit score"?

Fit score = how well an option aligns with stakeholders' goals (0-100%).

- High fit = option achieves most goals
- Low fit = option misses important goals

TAE calculates this automatically from perspectives + votes.

### Should I use CEE (AI assistance)?

**Yes, for:**
- Critical decisions (high stakes)
- Complex options (many assumptions)
- Contentious decisions (strong disagreements)

**Optional for:**
- Low-stakes decisions
- Time-sensitive decisions (CEE adds time)
- Well-understood problems

### Should I use ISL (causal validation)?

**Yes, for:**
- Options with causal claims ("X will cause Y")
- Claims about customer behavior
- Technical assumptions
- Market predictions

**Not needed for:**
- Preferences ("we prefer React over Vue")
- Definitions ("our target market is SMBs")
- Simple facts ("we have 10 engineers")

### How long should decisions take?

**Target:** 2-5 days from creation to finalization.

**Typical timeline:**
- Day 1: Create, collect perspectives
- Day 2: Propose options, async voting
- Day 3-4: Discussion, alignment
- Day 5: Finalize decision

Some decisions faster (<1 day), some slower (>1 week) - that's okay!

### When should I finalize a decision?

When:
- ✅ All stakeholders have voted
- ✅ Major disagreements resolved
- ✅ Minority concerns addressed
- ✅ Clear consensus emerged

Don't force consensus if:
- ❌ Key concerns unaddressed
- ❌ Missing critical information
- ❌ Stakeholders haven't had time to digest

### What if we can't reach alignment?

Options:
1. **More discussion** - Schedule sync meeting
2. **More information** - Use CEE/ISL to validate assumptions
3. **Modify options** - Synthesize hybrid options
4. **Decision owner decides** - Acknowledge disagreements, move forward
5. **Escalate** - Bring in leadership if truly blocked

TAE shows you disagreements clearly - but can't force consensus!

---

## Phase D Features

### D1: Portfolio Analytics

**Q: When should I check portfolio analytics?**
A: Weekly team review. Check health scores, bottlenecks, strategic insights.

**Q: What's a "health score"?**
A: 0-1 score of your portfolio health based on:
- Decision velocity
- Quality ratings
- Bottleneck severity
- Stakeholder satisfaction

>0.8 = healthy, 0.5-0.8 = okay, <0.5 = needs attention.

**Q: What are "bottlenecks"?**
A: Stuck decisions flagged by TAE:
- **Stuck sessions:** No activity >7 days
- **Overloaded stakeholders:** Same person in too many decisions
- **Validation blocked:** Waiting on CEE/ISL

**Q: What are "strategic insights"?**
A: AI-generated recommendations from TAE's analysis of your portfolio. Examples:
- "Consider merging 3 related feature decisions"
- "Q1 planning decisions taking 2x longer than Q4"

### D2: Real-Time Collaboration

**Q: How do I see who's online?**
A: Green dots next to names (top right of any session). Click to see full presence.

**Q: What are the typing indicators?**
A: Shows when teammates are editing (reduces conflicts, increases awareness).

**Q: Do I have to be online at the same time?**
A: No! TAE works async or sync. Real-time features enhance sync collaboration but aren't required.

**Q: Why aren't updates appearing live?**
A: Check:
- Internet connection stable?
- Browser refreshed recently?
- Redis connection healthy? (Check `/health`)

If persists >5 minutes, report to #tae-pilot-support.

### D3: Decision Dependencies

**Q: When should I create dependencies?**
A: When decisions are related:
- One blocks another ("Set Q1 OKRs" blocks "Plan Q1 hiring")
- One depends on another ("Pricing model" depends on "Target customer segment")
- Related context ("Feature A" relates to "Feature B")

**Q: What's a circular dependency?**
A: A→B→C→A loop. TAE detects and prevents these. If you try to create one, you'll get an error explaining the cycle.

**Q: How do I visualize dependencies?**
A: Dashboard → Dependencies → Graph view. Shows all related decisions as a network.

**Q: Can I dependency across teams?**
A: Yes! That's what D6 (Cross-Team Coordination) is for. Create coordination groups for multi-team dependencies.

### D4: Organizational Patterns

**Q: What are "patterns"?**
A: Insights from your team's past decisions:
- **Success patterns:** What works (e.g., "decisions with customer validation succeed 80% of time")
- **Failure indicators:** Warning signs (e.g., "decisions with >8 stakeholders take 3x longer")

**Q: How many past decisions needed?**
A: Minimum 3 completed decisions. More data = better patterns. Recommend 10+ decisions for meaningful insights.

**Q: Why can't I see patterns yet?**
A: Likely insufficient data. Complete more decisions with retrospectives. Patterns emerge after 3+ weeks of usage.

**Q: Are patterns private to my team?**
A: Patterns are organization-level (all teams). Your specific decisions are private, but aggregated patterns are shared.

### D5: Advanced Analytics

**Q: What metrics can I track?**
A: - Decision time, Quality ratings, Stakeholder satisfaction, Option count, Validation usage, etc.

**Q: What's "trend analysis"?**
A: Shows metric changes over time (e.g., "decision time trending down 20% over last 60 days").

**Q: What's "forecasting"?**
A: Predicts future values (e.g., "expect 12 decisions next month based on current trend").

**Q: Why is forecast inaccurate?**
A: Forecasting requires:
- Sufficient historical data (60+ days recommended)
- Stable patterns (not works during major changes)
- Quality data (complete retrospectives)

Early in pilot, forecasts may be rough. Improves with time.

### D6: Cross-Team Coordination

**Q: When do I need coordination?**
A: When multiple teams' decisions interact:
- Shared resources (budget, engineers)
- Overlapping timelines
- Dependent deliverables
- Competing priorities

**Q: How do I create a coordination group?**
A: Dashboard → Coordination → "+ New Group" → Add decisions from multiple teams.

**Q: What conflicts can TAE detect?**
A: - Temporal (timeline overlaps), Resource (same people/budget), Dependency (excessive chains), Scope (overlapping boundaries)

**Q: Can TAE resolve conflicts automatically?**
A: No. TAE detects and highlights conflicts. Your teams must resolve them (adjust timelines, reallocate resources, etc.).

---

## Issues & Troubleshooting

### TAE is slow. Why?

Check:
- **Network:** Slow internet? Try different network.
- **Browser:** Try Chrome/Firefox (latest version).
- **Load:** Is staging server overloaded? Check #tae-pilot-support.
- **Data:** Large portfolios (>100 sessions) may be slow. Report if this affects you.

### I can't see a decision I created.

Check:
- **Status:** Is it archived? (Filter: Show Archived)
- **Permissions:** Are you still a stakeholder?
- **Organization:** Are you viewing correct org?

Still missing? Report with decision ID to #tae-pilot-support.

### Real-time updates not working.

**Symptoms:** Changes don't appear live, have to refresh.

**Solutions:**
1. Check internet connection
2. Refresh browser (Ctrl+R / Cmd+R)
3. Check Redis health: `/health` → dependencies.redis
4. Report if persists >5 minutes

### Portfolio analytics shows wrong data.

**Possible causes:**
- **Cache lag:** Analytics cache TTL = 5 minutes. Wait and refresh.
- **Date filters:** Check date range settings.
- **Team filters:** Verify correct teams selected.

Still wrong? Screenshot and report to #tae-pilot-support.

### Dependency graph is confusing.

**Tips:**
- Use list view instead of graph view (clearer for complex graphs)
- Filter by dependency type (blocks, depends_on, etc.)
- Zoom and pan the graph
- Check documentation: [Phase D Guide](PHASE_D_GUIDE.md)

### I got a circular dependency error.

**This is expected!** TAE prevents cycles. Review your dependency chain and remove the conflicting dependency.

Example:
- A blocks B
- B blocks C
- Trying to add: C blocks A ← This creates a cycle!

**Solution:** Decide which dependency is incorrect and remove it.

### WebSocket connection failed.

**Symptoms:** Error message "WebSocket connection failed" or "Can't connect to collaboration server"

**Solutions:**
1. Check firewall/proxy settings (WebSocket requires open connection)
2. Try different network (corporate firewalls may block WebSocket)
3. Check Redis health at `/health`
4. Report if persists

**Workaround:** TAE still works without WebSocket (no real-time features, but core functionality intact).

---

## Data & Privacy

### Is my data private?

Yes. All pilot data is organization-private. Only your organization's members can see your decisions.

### Can TAE team see my data?

Admin access for support only (with your permission). Aggregated anonymized metrics used for research.

### What data does TAE collect?

- Decision content (topics, options, votes, etc.)
- User interactions (clicks, page views, time on page)
- Performance metrics (latency, error rates)
- Feedback and survey responses

### Can I delete my data?

Yes. Request data deletion via tae-pilot@olumi.com. We'll export your data first (in case you want it later).

### Where is data stored?

- **Database:** PostgreSQL (hosted in US/EU, configurable)
- **Cache:** Redis (ephemeral, 24-hour TTL)
- **Backups:** Daily backups retained 30 days

### Is data encrypted?

- **In transit:** Yes (TLS 1.3)
- **At rest:** Yes (database encryption)
- **Backups:** Yes (encrypted archives)

### GDPR compliant?

Phase D pilot is not yet GDPR-certified. Full compliance comes in Phase E (Enterprise features).

For pilot, we follow GDPR principles:
- Right to access (export your data)
- Right to deletion
- Right to portability
- Minimal data collection

---

## Pilot Program

### How do I provide feedback?

Multiple ways:
1. **Weekly survey** (emailed Fridays)
2. **In-app feedback button** (bottom right, any page)
3. **Bi-weekly interviews** (optional, sign up in Slack)
4. **Slack** (#tae-pilot-support)
5. **Email** (tae-pilot@olumi.com)

### What if I find a bug?

**Critical bugs** (data loss, can't access): Report immediately in #tae-pilot-support (mention @tae-team).

**Non-critical bugs:** Use in-app feedback button or Slack.

**Bug reports should include:**
- What you were doing
- What you expected
- What actually happened
- Screenshot (if applicable)
- Browser and OS version

### Can I invite more teammates?

Yes! Contact tae-pilot@olumi.com with:
- Names and emails
- Roles
- Why they should join

We'll send invites within 1 business day.

### Can I drop out of the pilot?

Yes, though we'd love to understand why first. Contact tae-pilot@olumi.com to discuss.

### What's expected of pilot teams?

- Use TAE for team decisions (6 weeks)
- Provide weekly feedback
- Report bugs/issues promptly
- Participate in at least one interview or retrospective

Time commitment: ~1-2 hours/week (less than time saved from faster decisions!).

### When do I get pilot results?

Pilot wrap-up report shared within 2 weeks of pilot completion. Includes:
- Aggregated metrics
- Key insights
- Next steps

---

## Technical Questions

### What browsers are supported?

**Fully supported:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**May work but not tested:**
- Older browsers
- Mobile browsers (basic functionality only)

### Mobile app?

Not yet. Coming in Phase E. Use mobile browser for now (responsive design).

### API access?

Not yet. Phase E includes REST API and webhooks for custom integrations.

### Integrations?

Phase D pilot has no integrations. Phase E includes:
- Slack (notifications, bot commands)
- Jira (ticket linking)
- Linear (issue sync)
- Google Calendar
- Custom webhooks

### Can I export my data?

Yes. Contact tae-pilot@olumi.com for export (JSON format). Includes:
- All decisions
- Perspectives, options, votes
- Dependencies
- Analytics data

### Can I customize TAE for my team?

Limited customization via feature flags. Major customization comes in Phase E (white-label, branding).

For pilot, tell us what you'd like customized - informs Phase E roadmap!

---

## Still Have Questions?

**Slack:** #tae-pilot-support (fastest response)

**Email:** tae-pilot@olumi.com

**Office Hours:** Thursdays 2-3pm GMT (Zoom link in Slack)

**Documentation:**
- [Onboarding Guide](PILOT_ONBOARDING_GUIDE.md)
- [Quick Start](QUICK_START.md)
- [Feedback Templates](FEEDBACK_TEMPLATES.md)
- [Phase D Implementation Docs](../PHASE_D_IMPLEMENTATION.md)

**Can't find your answer?** Ask in Slack - we'll add it to this FAQ!

---

**Last Updated:** November 2025
**Version:** 2.0.0 (Phase D Pilot)
