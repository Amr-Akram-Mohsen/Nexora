Execution Constraints

Before making any modifications, briefly analyze the relevant files and determine whether their current contents accurately represent Nexora's intended architecture.

Treat the existing codebase as evidence rather than absolute truth. Do not assume that every existing implementation is architecturally correct.

If you detect:

duplicated logic
inconsistent patterns
legacy implementations
temporary workarounds
architectural violations
conflicting documentation

do not encode those as project rules.

Instead:

document the intended architecture,
refactor toward the intended architecture whenever appropriate,
preserve only deliberate and consistent architectural decisions.
-----------------------------------------------------------

Execution Mode

Do not stop after producing an implementation plan.

Unless explicitly requested otherwise, execute the approved changes immediately.

Analysis should only be long enough to understand the required changes.

The primary goal is implementation rather than planning.
----------------------------------------------------------------

Documentation Quality

Every markdown document must optimize for AI execution rather than human reading.

Documents should contain:

purpose
responsibilities
dependencies
examples
anti-patterns
refactoring rules
common AI tasks
related files
cross references
implementation notes

Avoid narrative documentation.
----------------------------------------------------

Modularity

Prefer creating focused directories containing multiple small markdown files instead of large documents.

Avoid "god documents."

Every file should have a single responsibility.
-----------------------------------------------------------

Architecture Consistency

Every new document must be consistent with:

Domain architecture
Application layer
Presentation layer
Serialization rules
Routing rules
CSS architecture
Template architecture
JavaScript architecture
Existing naming conventions

If inconsistencies are found in the existing project, document the intended architecture instead of preserving the inconsistency.
