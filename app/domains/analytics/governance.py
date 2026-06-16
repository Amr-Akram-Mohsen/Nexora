# app/domains/interaction/service/insights/governance.py
import hashlib
from datetime import datetime, timezone
from app.domains.analytics.learning_memory import load_memory_layer
from app.domains.analytics.autonomous_execution import (
    load_execution_tasks,
    save_execution_tasks,
    process_execution_queue
)

ENABLE_LIVE_EXECUTION = False

# ---------------------------------------------------------
# Reusable Governance Policies
# ---------------------------------------------------------
class BaseGovernancePolicy:
    """Base interface for governance audit/compliance checks."""
    def evaluate(self, task, context):
        """Returns tuple (is_valid: bool, error_reason: str or None)"""
        raise NotImplementedError()

class FrequencyCapPolicy(BaseGovernancePolicy):
    def evaluate(self, task, context):
        entity = task["entity"]
        scheduled_time = context["scheduled_time"]
        count = context["entity_week_counts"].get((entity, scheduled_time), 0)
        if count > 1:
            return False, "Repeated entity publishing: Multiple posts scheduled in the same week."
        return True, None

class PlatformPacingPolicy(BaseGovernancePolicy):
    def evaluate(self, task, context):
        platform = task["platform"]
        scheduled_time = context["scheduled_time"]
        count = context["platform_week_counts"].get((platform, scheduled_time), 0)
        if count > 1:
            return False, "Conflicting platform schedules: Same platform scheduled multiple times in the same week."
        return True, None

class GroundingCheckPolicy(BaseGovernancePolicy):
    def evaluate(self, task, context):
        content_id = task.get("content_id", "")
        is_new = (content_id == "new" or content_id == "")
        if not is_new:
            asset_match_quality = context["asset_match_map"].get(task["entity"], 0.0)
            if asset_match_quality < 0.45:
                return False, "Weak asset match: relevance score is below 0.45."
        return True, None

class PerformanceHistoryPolicy(BaseGovernancePolicy):
    def evaluate(self, task, context):
        entity = task["entity"]
        entity_memory = context["memory_map"].get(entity)
        if entity_memory and entity_memory.get("outcome") == "failure":
            return False, "Unstable CTR history: historical performance indicates failure."
        return True, None

class MetadataValidationPolicy(BaseGovernancePolicy):
    def evaluate(self, task, context):
        if not task.get("content_type") or not task.get("platform"):
            return False, "Missing metadata: essential task properties are missing."
        return True, None

# Register active policy checks
GOVERNANCE_POLICIES = [
    FrequencyCapPolicy(),
    PlatformPacingPolicy(),
    GroundingCheckPolicy(),
    PerformanceHistoryPolicy(),
    MetadataValidationPolicy()
]

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def parse_scheduled_time(reason):
    """Parses week schedule name from task reasoning strings."""
    reason_lower = (reason or "").lower()
    if "week 2" in reason_lower:
        return "Week 2"
    elif "backlog" in reason_lower:
        return "Backlog"
    return "Week 1"

def classify_governance_risk(risk_reasons):
    """Classifies consolidated risk tier and computes associated decision penalty."""
    is_high = any("Repeated entity" in r or "Unstable CTR" in r for r in risk_reasons)
    is_medium = any("Conflicting platform" in r or "Weak asset" in r for r in risk_reasons)
    
    if is_high:
        return "HIGH", 0.0
    elif is_medium:
        return "MEDIUM", 0.5
    else:
        return "LOW", 1.0

def calculate_governance_decision_score(opp_score, strategy_confidence, asset_match_quality, performance_history, risk_penalty):
    """Calculates decision score considering signal strength, confidence, grounding, and risk."""
    score = (
        0.35 * opp_score +
        0.25 * strategy_confidence +
        0.20 * asset_match_quality +
        0.10 * performance_history +
        0.10 * risk_penalty
    )
    return round(max(0.0, min(1.0, score)), 2)

def determine_governance_mode(decision_score, risk_reasons):
    """Decides execution authorization gating category."""
    has_blocked_trigger = (
        decision_score < 0.70 or
        any("Repeated entity" in r for r in risk_reasons) or
        any("Unstable CTR" in r for r in risk_reasons) or
        any("Conflicting platform" in r for r in risk_reasons)
    )
    
    if has_blocked_trigger:
        return "BLOCKED"
    elif decision_score >= 0.90 and len(risk_reasons) == 0:
        return "AUTO_EXECUTE"
    else:
        return "NEEDS_APPROVAL"

def evaluate_governance_policies(task, context):
    """Runs registered policies on task and aggregates failed reason descriptors."""
    risk_reasons = []
    for policy in GOVERNANCE_POLICIES:
        passed, reason = policy.evaluate(task, context)
        if not passed:
            risk_reasons.append(reason)
    return risk_reasons

# ---------------------------------------------------------
# Core Service Functions
# ---------------------------------------------------------
def generate_execution_governance_layer(execution_plan, asset_mapping, strategy_data):
    """
    Implements a production-safe control and risk classification layer over
    autonomous execution tasks. Returns safe, approval-pending, and blocked queues.
    """
    system_mode = "LIVE_MODE" if globals().get("ENABLE_LIVE_EXECUTION", False) else "SAFE_MODE"
    
    all_plan_tasks = []
    for q_name in ["auto_execute", "needs_review", "blocked"]:
        for task in execution_plan.get(q_name, []):
            all_plan_tasks.append(task)
            
    persisted_tasks = load_execution_tasks()
    persisted_map = {f"{t['entity']}_{t['platform']}_{t['action']}_{t['scheduled_time']}": t for t in persisted_tasks}
    
    opp_score_map = {mapping["entity"]: mapping["opportunity_score"] for mapping in asset_mapping}
    
    asset_match_map = {}
    for mapping in asset_mapping:
        entity = mapping["entity"]
        existing = mapping.get("existing_assets", [])
        max_relevance = max([a["relevance_score"] for a in existing]) if existing else 0.0
        asset_match_map[entity] = max_relevance
        
    eval_results = strategy_data.get("evaluation_results", [])
    eval_map = {e["entity"]: e for e in eval_results}
    avg_accuracy = strategy_data.get("average_accuracy", 85.0) / 100.0
    
    memory_layer = strategy_data.get("memory_layer", [])
    memory_map = {m["entity"]: m for m in memory_layer}
    
    # Pre-calculate scheduling volume context maps for policies
    entity_week_counts = {}
    platform_week_counts = {}
    for task in all_plan_tasks:
        scheduled_time = parse_scheduled_time(task.get("reason", ""))
        
        key_ent = (task["entity"], scheduled_time)
        entity_week_counts[key_ent] = entity_week_counts.get(key_ent, 0) + 1
        
        key_plat = (task["platform"], scheduled_time)
        platform_week_counts[key_plat] = platform_week_counts.get(key_plat, 0) + 1
        
    governed_tasks = []
    
    for task in all_plan_tasks:
        entity = task["entity"]
        platform = task["platform"]
        action = task["action"]
        content_id = task.get("content_id", "")
        scheduled_time = parse_scheduled_time(task.get("reason", ""))
        task_key = f"{entity}_{platform}_{action}_{scheduled_time}"
        
        opp_score = opp_score_map.get(entity, 0.5)
        entity_eval = eval_map.get(entity)
        strategy_confidence = entity_eval["performance_delta"]["accuracy_score"] if entity_eval else avg_accuracy
        
        is_new = (content_id == "new" or content_id == "")
        asset_match_quality = 0.5 if is_new else asset_match_map.get(entity, 0.0)
        
        entity_memory = memory_map.get(entity)
        performance_history = 1.0 if entity_memory and entity_memory.get("outcome") == "success" else (0.5 if not entity_memory else 0.0)
        
        # Build policy valuation context
        context = {
            "scheduled_time": scheduled_time,
            "entity_week_counts": entity_week_counts,
            "platform_week_counts": platform_week_counts,
            "asset_match_map": asset_match_map,
            "memory_map": memory_map
        }
        
        # Evaluate governance policies
        risk_reasons = evaluate_governance_policies(task, context)
        
        # Risk classification and penalty
        risk_level, risk_penalty = classify_governance_risk(risk_reasons)
        
        # Decision score
        decision_score = calculate_governance_decision_score(
            opp_score=opp_score,
            strategy_confidence=strategy_confidence,
            asset_match_quality=asset_match_quality,
            performance_history=performance_history,
            risk_penalty=risk_penalty
        )
        
        # Mode
        mode = determine_governance_mode(decision_score, risk_reasons)
        
        # Sync with persisted queues
        if task_key in persisted_map:
            task_status = persisted_map[task_key].get("status", "queued")
            execution_log = persisted_map[task_key].get("execution_log")
        else:
            task_status = "blocked" if mode == "BLOCKED" else "queued"
            execution_log = None
            
        h = hashlib.md5(task_key.encode('utf-8')).hexdigest()[:8]
        task_id = f"exec_{h}"
        
        governed_task = {
            "id": task_id,
            "entity": entity,
            "platform": platform,
            "action": action,
            "execution_mode": mode,
            "status": task_status,
            "scheduled_time": scheduled_time,
            "risk_level": risk_level,
            "decision_score": decision_score,
            "risk_reasons": risk_reasons,
            "created_at": persisted_map[task_key].get("created_at") if task_key in persisted_map else datetime.now(timezone.utc).isoformat()
        }
        
        if execution_log:
            governed_task["execution_log"] = execution_log
            
        governed_tasks.append(governed_task)
        
    # Process queue tasks
    processed_tasks = process_execution_queue(governed_tasks)
    save_execution_tasks(processed_tasks)
    
    queued_tasks = []
    approved_tasks = []
    blocked_tasks = []
    
    for t in processed_tasks:
        if t["execution_mode"] == "BLOCKED" or t["status"] == "blocked":
            blocked_tasks.append(t)
        elif t["status"] in ("executed", "approved"):
            approved_tasks.append(t)
        else:
            queued_tasks.append(t)
            
    risk_summary = {
        "low_count": sum(1 for t in processed_tasks if t["risk_level"] == "LOW"),
        "medium_count": sum(1 for t in processed_tasks if t["risk_level"] == "MEDIUM"),
        "high_count": sum(1 for t in processed_tasks if t["risk_level"] == "HIGH"),
        "reasons": list(set(r for t in processed_tasks for r in t.get("risk_reasons", [])))
    }
    
    return {
        "mode": system_mode,
        "queued_tasks": queued_tasks,
        "approved_tasks": approved_tasks,
        "blocked_tasks": blocked_tasks,
        "risk_summary": risk_summary
    }

