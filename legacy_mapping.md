# Nexora Refactoring: Legacy Mapping & Cleanup

This document maps old files and functions to the new layered architecture. Elements marked as **[DELETE]** are completely redundant and should be removed once you confirm the new flows.

## 1. Web & API Routes (The most significant change)

All main web routes have moved from `app/domains/*/routes/web.py` to `app/web/routes/*.py`. The old domain-nested routes are now redundant.

| Old Location (to be Deleted) | New Location (Replaced By) | Notes |
| :--- | :--- | :--- |
| `app/domains/content/routes/web.py` | [app/web/routes/content.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/web/routes/content.py) | Logic extracted to `app/application/content/` |
| `app/domains/item/routes/web.py` | [app/web/routes/item.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/web/routes/item.py) | Logic extracted to `app/application/item/` |
| `app/domains/user/routes/web.py` | [app/web/routes/user.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/web/routes/user.py) | Logic extracted to `app/application/user/` |
| `app/domains/interaction/routes/web.py` | [app/web/routes/interaction.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/web/routes/interaction.py) | Logic extracted to `app/application/interaction/` |
| `app/domains/system/routes/web.py` | [app/web/routes/system.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/web/routes/system.py) | Logic extracted to `app/application/system/` |
| `app/domains/recommendation/routes/web.py` | [app/web/routes/recommendation.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/web/routes/recommendation.py) | Logic extracted to `app/application/recommendation/` |

## 2. Template Context (Presentation Layer)

The monolithic `app/core/context.py` has been largely replaced by the `app/presentation/` layer.

| Logic Area | Old Location | New Location |
| :--- | :--- | :--- |
| **Global Context Registry** | `app/core/context.py` | [app/core/context.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/core/context.py) (Now just an entry point) |
| **User/Auth Context** | `app/core/context.py` (inline) | [app/presentation/context/user.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/presentation/context/user.py) |
| **Layout/Navigation** | `app/core/context.py` (inline) | [app/presentation/context/layout.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/presentation/context/layout.py) |
| **URL Filter Helpers** | `app/core/context.py` (inline) | [app/presentation/context/filters.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/presentation/context/filters.py) |
| **Newsletter State** | `app/core/context.py` (inline) | [app/presentation/context/newsletter.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/presentation/context/newsletter.py) |

## 3. Redundant Logic & Dead Functions

The following functions were moved or refactored into cleaner application workflows.

| Domain/Layer | Logic / Function | Replaced By |
| :--- | :--- | :--- |
| **System Domain** | `get_contents_render` (in system) | Moved to [app/domains/content/service/query.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/domains/content/service/query.py) |
| **User Domain** | Duplicate newsletter logic in registration | Unified in [app/application/interaction/newsletter.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/application/interaction/newsletter.py) |
| **Interaction** | Reaction/Save/Comment Logic | Moved to [app/domains/interaction/service/command.py](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/domains/interaction/service/command.py) |
| **Infrastructure** | Direct `cache.memoize` calls | Wrapped by [app/infrastructure/cache/](file:///c:/Users/ammar/Desktop/my_github/Nexora/app/infrastructure/cache/__init__.py) |

## 4. Suggested Directory Cleanup

> [!WARNING]
> **Proceed with Caution**: Do not delete these until you have verified that no other part of the system (e.g. CLI tools or old templates) imports from them.

1.  **Delete** `app/domains/*/routes/` once all blueprints are confirmed registered to `app/web/routes/`.
2.  **Delete** `app/core/context.py`'s internal implementations and keep it only as the registry for the `presentation/` layer.
