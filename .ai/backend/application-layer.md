# Application Layer Architecture

The Application Layer (`app/application`) serves as the orchestrator of the Nexora backend. It sits between the Presentation Layer (Web/Admin Routes) and the Domain Layer, managing cross-domain workflows and use cases.

## Core Philosophy

*   **Conductor, Not Player:** The Application Layer does not contain core business logic, complex algorithms, or raw database queries. It coordinates Domain Services to execute a specific user journey.
*   **Domain Decoupling:** By orchestrating cross-domain interactions here, we prevent Domain A from becoming tightly coupled to Domain B.
*   **HTTP Agnostic:** The Application Layer must remain completely oblivious to Flask. It never imports `request`, `session`, or returns HTTP responses.

---

## When to Use the Application Layer

1.  **Cross-Domain Orchestration:** If a feature requires fetching an Article (Content Domain), fetching related Products (Item Domain), and updating user analytics (User Domain), this logic belongs in an application workflow (e.g., `get_content_page.py`).
2.  **Complex Side Effects:** If mutating data in one domain triggers side effects in another (e.g., Liking an item updates the Recommendation weights), the Application service coordinates these calls.
3.  **When to Skip It:** If a route is performing a simple, single-domain operation (e.g., fetching a User's basic profile), the route may call the Domain Service directly.

---

## Transaction Boundaries

The Application Layer acts as the primary **Transaction Boundary** for complex mutations.

*   **Domain Service Role:** Domain services perform validation, apply business rules, and add/modify objects in the database session (`db.session.add()`). They generally *do not* call `.commit()`.
*   **Application Service Role:** The application workflow invokes all necessary domain services. If all succeed, the Application service calls `db.session.commit()`. This ensures that cross-domain mutations either succeed entirely or fail safely together.

**Example:**
```python
def handle_interaction_workflow(user, target_id, interaction_type):
    # 1. Domain A Mutation
    react_result = react_service(user, target_id, interaction_type)
    
    # 2. Domain B Side Effect
    update_recommendation_interest(user, target_id)
    
    # 3. Transaction Commit
    db.session.commit()
    
    return react_result
```

---

## DTO Construction & Serialization Boundaries

Application services are often responsible for assembling the final Data Transfer Object (DTO) or "Context Dictionary" required by the frontend.

1.  **Fetching Serialized Data:** It calls domain query services which return pre-serialized dictionaries.
2.  **Aggregation:** It merges data from multiple domains into a single cohesive dictionary structure.
3.  **No Formatting:** Like domain serializers, the Application layer does not format data for UI presentation (e.g., no date string formatting). It returns clean, aggregated data structures.

**Example Return Structure:**
```python
return {
    "content": content_dict,       # From Content Domain
    "related_items": items_list,   # From Item Domain
    "user_status": status_dict     # From User Domain
}
```

---

## Permissions & Authorization

*   **Route Layer:** Handles Authentication (Is the user logged in?) via decorators like `@login_required`.
*   **Domain Layer:** Handles Entity-level authorization (Does this user own this specific comment?).
*   **Application Layer:** Handles Workflow-level permissions (Is this user allowed to execute this complex system sync process?).

---

## Organization & Naming

The `app/application` directory is organized by feature or macro-domain, containing isolated Python files that usually represent a single major use case or a small group of related workflows.

*   **File Naming:** Files are named after the action or the entity group (e.g., `get_content_page.py`, `handle_interaction.py`, `article_ingestion.py`).
*   **Function Naming:** Functions should be verbs describing the use case (e.g., `get_feed_data()`, `run_ingestion_pipeline()`).
*   **Classes vs. Functions:** Functions are preferred for simple workflows. Classes should only be used if the workflow requires maintaining complex internal state across multiple steps.

---

## Anti-Patterns

1.  **Leaking HTTP Context:** Passing the Flask `request` object into an Application service. Always unpack the necessary parameters in the Route and pass them as native Python variables.
2.  **Database Queries:** Writing `Content.query.filter_by(...)` inside an Application service. This must be delegated to a Domain service.
3.  **God Workflows:** Creating a massive `handle_everything.py` file. Keep application services focused on specific use cases.
