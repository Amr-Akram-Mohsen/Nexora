# app/domains/interaction/service/insights/governance.py
import hashlib
from datetime import datetime, timezone
from app.domains.interaction.service.insights.learning_memory import load_memory_layer
from app.domains.interaction.service.insights.autonomous_execution import (
    load_execution_tasks,
    save_execution_tasks,
    process_execution_queue
)

ENABLE_LIVE_EXECUTION = False

def generate_execution_governance_layer(execution_plan, asset_mapping, strategy_data):
    """
    Implements a production-safe control and risk classification layer over
    autonomous execution tasks. Returns safe, approval-pending, and blocked queues.
    """
    system_mode = "SAFE_MODE"
    if globals().get("ENABLE_LIVE_EXECUTION", False):
        system_mode = "LIVE_MODE"
        
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
    
    entity_week_counts = {}
    platform_week_counts = {}
    for task in all_plan_tasks:
        reason_lower = task.get("reason", "").lower()
        if "week 2" in reason_lower:
            week = "Week 2"
        elif "backlog" in reason_lower:
            week = "Backlog"
        else:
            week = "Week 1"
            
        key_ent = (task["entity"], week)
        entity_week_counts[key_ent] = entity_week_counts.get(key_ent, 0) + 1
        
        key_plat = (task["platform"], week)
        platform_week_counts[key_plat] = platform_week_counts.get(key_plat, 0) + 1
        
    governed_tasks = []
    
    for task in all_plan_tasks:
        entity = task["entity"]
        platform = task["platform"]
        action = task["action"]
        content_id = task.get("content_id", "")
        
        reason_lower = task.get("reason", "").lower()
        if "week 2" in reason_lower:
            scheduled_time = "Week 2"
        elif "backlog" in reason_lower:
            scheduled_time = "Backlog"
        else:
            scheduled_time = "Week 1"
            
        task_key = f"{entity}_{platform}_{action}_{scheduled_time}"
        
        opp_score = opp_score_map.get(entity, 0.5)
        
        entity_eval = eval_map.get(entity)
        if entity_eval:
            strategy_confidence = entity_eval["performance_delta"]["accuracy_score"]
        else:
            strategy_confidence = avg_accuracy
            
        is_new = (content_id == "new" or content_id == "")
        if is_new:
            asset_match_quality = 0.5
        else:
            asset_match_quality = asset_match_map.get(entity, 0.0)
            
        entity_memory = memory_map.get(entity)
        if entity_memory:
            performance_history = 1.0 if entity_memory["outcome"] == "success" else 0.0
        else:
            performance_history = 0.5
            
        risk_reasons = []
        
        if entity_week_counts.get((entity, scheduled_time), 0) > 1:
            risk_reasons.append("Repeated entity publishing: Multiple posts scheduled in the same week.")
            
        if platform_week_counts.get((platform, scheduled_time), 0) > 1:
            risk_reasons.append("Conflicting platform schedules: Same platform scheduled multiple times in the same week.")
            
        if not is_new and asset_match_map.get(entity, 0.0) < 0.45:
            risk_reasons.append("Weak asset match: relevance score is below 0.45.")
            
        if entity_memory and entity_memory["outcome"] == "failure":
            risk_reasons.append("Unstable CTR history: historical performance indicates failure.")
            
        if not task.get("content_type") or not task.get("platform"):
            risk_reasons.append("Missing metadata: essential task properties are missing.")
            
        is_high = any("Repeated entity" in r or "Unstable CTR" in r for r in risk_reasons)
        is_medium = any("Conflicting platform" in r or "Weak asset" in r for r in risk_reasons)
        
        if is_high:
            risk_level = "HIGH"
            risk_penalty = 0.0
        elif is_medium:
            risk_level = "MEDIUM"
            risk_penalty = 0.5
        else:
            risk_level = "LOW"
            risk_penalty = 1.0
            
        decision_score = (
            0.35 * opp_score +
            0.25 * strategy_confidence +
            0.20 * asset_match_quality +
            0.10 * performance_history +
            0.10 * risk_penalty
        )
        decision_score = round(max(0.0, min(1.0, decision_score)), 2)
        
        has_blocked_trigger = (
            decision_score < 0.70 or
            any("Repeated entity" in r for r in risk_reasons) or
            any("Unstable CTR" in r for r in risk_reasons) or
            any("Conflicting platform" in r for r in risk_reasons)
        )
        
        if has_blocked_trigger:
            mode = "BLOCKED"
        elif decision_score >= 0.90 and len(risk_reasons) == 0:
            mode = "AUTO_EXECUTE"
        else:
            mode = "NEEDS_APPROVAL"
            
        if task_key in persisted_map:
            task_status = persisted_map[task_key].get("status", "queued")
            execution_log = persisted_map[task_key].get("execution_log")
        else:
            if mode == "BLOCKED":
                task_status = "blocked"
            elif mode == "AUTO_EXECUTE":
                task_status = "queued"
            else:
                task_status = "queued"
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
        
    processed_tasks = process_execution_queue(governed_tasks)
    save_execution_tasks(processed_tasks)
    
    queued_tasks = []
    approved_tasks = []
    blocked_tasks = []
    
    for t in processed_tasks:
        if t["execution_mode"] == "BLOCKED" or t["status"] == "blocked":
            blocked_tasks.append(t)
        elif t["status"] == "executed" or t["status"] == "approved":
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
