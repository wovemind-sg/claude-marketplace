# Compliance layer

## 7. Compliance-aware product design

Compliance is part of product architecture, not copy added afterward.

Trigger deeper compliance review when the feature involves areas such as:

* children/minors
* parental consent
* personal or sensitive data
* photos
* AI processing
* third-party data sharing
* identity/authentication
* location
* payments/subscriptions
* health/financial information
* marketing consent
* tracking
* account deletion
* data retention
* user-generated content

Separate:

**Legal/policy requirement**
What appears required.

**Product requirement**
What the system must enforce.

**UX requirement**
What the user must see or do.

**Technical/security requirement**
What must be enforced outside the UI.

**Good practice**
Additional protection that is recommended but not necessarily required.

Never present uncertain legal interpretation as fact.

## 8. Current-law and platform verification

Do not spend tokens researching compliance for every task.

Research only when:

1. the issue materially affects the proposed flow or implementation; and
2. the relevant requirement could reasonably be jurisdiction-, provider- or time-dependent.

When research is required and tools are available:

1. identify the relevant jurisdiction/context;
2. check current authoritative sources;
3. prefer regulators, legislation and official platform/provider documentation;
4. verify only the questions necessary to make the product decision;
5. stop researching once sufficient evidence exists.

Do not repeatedly search the same question.

Distinguish confirmed requirements from interpretation.

Flag qualified legal review where genuinely necessary.

Never claim that a product is legally compliant solely because the UX appears appropriate.

## 9. Compliance with minimum friction

More friction does not automatically mean better compliance.

Avoid unnecessary:

* consent screens
* checkboxes
* warnings
* modals
* repeated verification
* confirmations

Determine the minimum interaction necessary to satisfy the legitimate requirement.

Request permissions and consent contextually, as close as practical to the relevant action.
