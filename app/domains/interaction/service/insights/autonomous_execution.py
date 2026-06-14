# app/domains/interaction/service/insights/autonomous_execution.py
import os
import json
from datetime import datetime, timezone
from app.domains.interaction.service.insights.learning_memory import load_json_file, save_json_file

# Queue File Path
QUEUE_FILE_PATH = os.path.join("instance", "execution_governance_queue.json")

def load_execution_tasks():
    """Loads execution tasks from the centralized persistence queue."""
    return load_json_file(QUEUE_FILE_PATH, default_factory=list)

def save_execution_tasks(tasks):
    """Saves execution tasks to the centralized persistence queue."""
    save_json_file(QUEUE_FILE_PATH, tasks)

# ---------------------------------------------------------
# Execution Adapters System
# ---------------------------------------------------------
class BasePlatformAdapter:
    """Interface / base class for platform execution adapters."""
    def execute(self, task):
        raise NotImplementedError("Platform execution not implemented.")

class YouTubeAdapter(BasePlatformAdapter):
    def execute(self, task):
        return {
            "status": "simulated",
            "platform": "youtube",
            "entity": task.get("entity", ""),
            "mock_url": f"/youtube/mock/{task.get('entity', '').lower().replace(' ', '_')}"
        }

class PinterestAdapter(BasePlatformAdapter):
    def execute(self, task):
        # Backward-compatible mock url builder
        return {
            "status": "simulated",
            "platform": "pinterest",
            "entity": task.get("entity", ""),
            "mock_url": f"/pinterest/mock/{task.get('entity', '').lower().replace(' ', '_')}"
        }

class BlogAdapter(BasePlatformAdapter):
    def execute(self, task):
        return {
            "status": "simulated",
            "platform": "blog",
            "entity": task.get("entity", ""),
            "mock_url": f"/blog/mock/{task.get('entity', '').lower().replace(' ', '_')}"
        }

class DynamicPlatformAdapter(BasePlatformAdapter):
    """Fallback adapter for easily adding new platforms (e.g. TikTok, X)."""
    def __init__(self, platform_name):
        self.platform_name = platform_name.lower()
        
    def execute(self, task):
        return {
            "status": "simulated",
            "platform": self.platform_name,
            "entity": task.get("entity", ""),
            "mock_url": f"/{self.platform_name}/mock/{task.get('entity', '').lower().replace(' ', '_')}"
        }

PLATFORM_ADAPTERS = {
    "youtube": YouTubeAdapter(),
    "pinterest": PinterestAdapter(),
    "blog": BlogAdapter()
}

def get_adapter(platform_name):
    """Retrieves or creates execution adapter for the given platform name."""
    name_clean = (platform_name or "").lower().strip()
    return PLATFORM_ADAPTERS.get(name_clean, DynamicPlatformAdapter(name_clean))

# ---------------------------------------------------------
# Adapter Functions wrapper for backwards compatibility
# ---------------------------------------------------------
def execute_youtube_publish(task):
    return get_adapter("youtube").execute(task)

def execute_pinterest_publish(task):
    return get_adapter("pinterest").execute(task)

def execute_pinterest_pin(task):
    res = execute_pinterest_publish(task)
    return {
        "status": "success",
        "platform": "pinterest",
        "content_id": task.get("content_id") or "new",
        "published_url": res["mock_url"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

def execute_blog_publish(task):
    return get_adapter("blog").execute(task)

# ---------------------------------------------------------
# Planning & Analytics Helpers
# ---------------------------------------------------------
def calculate_execution_confidence(opp_score, strat_acc, asset_match, hist_perf):
    """Centralized execution confidence calculation logic."""
    confidence = 0.4 * opp_score + 0.3 * strat_acc + 0.2 * asset_match + 0.1 * hist_perf
    return round(max(0.0, min(1.0, confidence)), 2)

def detect_execution_risks(task, opp_score, asset_match, entity_memory, week_name, existing_entities, existing_platforms):
    """Detects operational risk factors for execution planning."""
    entity = task["entity"]
    platform = task["platform"]
    source = task["source"]
    
    risk_factors = []
    
    # Scheduling conflicts for Week 1
    if week_name == "Week 1":
        if entity in existing_entities:
            risk_factors.append("Duplicate content scheduled for this entity in the same week.")
            
        platform_key = f"{week_name}_{platform}"
        if platform_key in existing_platforms:
            risk_factors.append(f"Platform scheduling conflict: multiple {platform} tasks queued for {week_name}.")
            
    # Weak asset grounding
    if source != "new" and asset_match < 0.45:
        risk_factors.append("Weak existing asset mapping grounding (relevance score < 0.45).")
        
    # Unstable performance history
    if entity_memory and entity_memory.get("outcome") == "failure":
        risk_factors.append("Historical strategy performance in memory layer indicates performance instability.")
        
    # Conflicting prioritization signal
    if opp_score < 0.45:
        risk_factors.append("Conflicting strategy signals: prioritization opportunity score is too low.")
        
    return risk_factors

def determine_execution_mode(confidence, risk_factors):
    """Decides execution mode (BLOCKED, AUTO_EXECUTE, NEEDS_REVIEW) based on confidence and risks."""
    has_critical_risks = any(x in risk_factors for x in [
        "Duplicate content scheduled for this entity in the same week.",
        "Historical strategy performance in memory layer indicates performance instability."
    ])
    
    if confidence < 0.60 or has_critical_risks:
        return "BLOCKED"
    elif confidence >= 0.85 and len(risk_factors) == 0:
        return "AUTO_EXECUTE"
    else:
        return "NEEDS_REVIEW"

# ---------------------------------------------------------
# Core Service Functions
# ---------------------------------------------------------
def generate_execution_plan(content_publishing_plan, content_asset_mapping, strategy_data):
    """
    Evaluates each scheduled task in the content publishing plan, calculates
    execution confidence scores, and determines the execution mode (AUTO_EXECUTE,
    NEEDS_REVIEW, BLOCKED) with safety guardrails.
    """
    memory_layer = strategy_data.get("memory_layer", [])
    memory_map = {m["entity"]: m for m in memory_layer}
    
    eval_results = strategy_data.get("evaluation_results", [])
    eval_map = {e["entity"]: e for e in eval_results}
    
    # Extract asset match quality (relevance scores)
    asset_match_map = {}
    opp_score_map = {}
    for mapping in content_asset_mapping:
        entity = mapping["entity"]
        opp_score_map[entity] = mapping["opportunity_score"]
        existing = mapping.get("existing_assets", [])
        max_relevance = max([a["relevance_score"] for a in existing]) if existing else 0.0
        asset_match_map[entity] = max_relevance

    avg_accuracy = strategy_data.get("average_accuracy", 85.0) / 100.0
    
    execution_plan = {
        "auto_execute": [],
        "needs_review": [],
        "blocked": []
    }
    
    # Process tasks from all weeks
    scheduled_tasks = []
    for week_data in content_publishing_plan.get("weekly_plan", []):
        week_name = week_data["week"]
        for task in week_data.get("tasks", []):
            scheduled_tasks.append((task, week_name))
            
    # Track platform schedules in Week 1 to identify duplicates or timing conflicts
    platform_schedule_week1 = set()
    entity_schedule_week1 = set()
    
    for task, week_name in scheduled_tasks:
        entity = task["entity"]
        platform = task["platform"]
        action = task["action"]
        source = task["source"]
        content_type = task["content_type"]
        
        opp_score = opp_score_map.get(entity, 0.5)
        entity_eval = eval_map.get(entity)
        strat_acc = entity_eval["performance_delta"]["accuracy_score"] if entity_eval else avg_accuracy
        asset_match = asset_match_map.get(entity, 0.0) if source != "new" else 0.5
        
        entity_memory = memory_map.get(entity)
        hist_perf = 1.0 if entity_memory and entity_memory.get("outcome") == "success" else (0.5 if not entity_memory else 0.0)
        
        # Centralized confidence calculation
        confidence = calculate_execution_confidence(opp_score, strat_acc, asset_match, hist_perf)
        
        # Risk checks
        risk_factors = detect_execution_risks(
            task=task,
            opp_score=opp_score,
            asset_match=asset_match,
            entity_memory=entity_memory,
            week_name=week_name,
            existing_entities=entity_schedule_week1,
            existing_platforms=platform_schedule_week1
        )
        
        # Track for subsequent checks in this week
        if week_name == "Week 1":
            entity_schedule_week1.add(entity)
            platform_schedule_week1.add(f"{week_name}_{platform}")
            
        # Determine mode
        mode = determine_execution_mode(confidence, risk_factors)
        
        exec_action = "create" if action == "postpone" else action
            
        exec_item = {
            "entity": entity,
            "platform": platform,
            "action": exec_action,
            "content_id": source if source != "new" else "",
            "content_type": content_type,
            "confidence_score": confidence,
            "execution_mode": mode,
            "reason": f"Priority timing: {week_name.lower()}. " + (
                "Approved for autonomous publishing pipeline." if mode == "AUTO_EXECUTE" else (
                    "Queued for human approval due to risk factors or medium confidence." if mode == "NEEDS_REVIEW" else
                    "Blocked from execution to prevent publishing risk."
                )
            ),
            "risk_factors": risk_factors
        }
        
        # Autonomous execution logic via adapters
        if mode == "AUTO_EXECUTE":
            if platform == "youtube":
                adapter_res = execute_youtube_publish(exec_item)
            elif platform == "pinterest":
                adapter_res = execute_pinterest_pin(exec_item)
            else:
                adapter_res = execute_blog_publish(exec_item)
            exec_item["execution_log"] = adapter_res
            
        # Distribute into return queues
        if mode == "AUTO_EXECUTE":
            execution_plan["auto_execute"].append(exec_item)
        elif mode == "NEEDS_REVIEW":
            execution_plan["needs_review"].append(exec_item)
        else:
            execution_plan["blocked"].append(exec_item)
            
    return execution_plan

def process_execution_queue(tasks):
    """Processes task status and executes actions using platform adapters registry."""
    tasks.sort(key=lambda x: x.get("decision_score", 0.0), reverse=True)
    
    executed_entities_week = set()
    for task in tasks:
        if task.get("status") == "executed":
            executed_entities_week.add((task["entity"], task["scheduled_time"]))
            
    for task in tasks:
        key = (task["entity"], task["scheduled_time"])
        
        is_ready = (task.get("status") == "queued" and task.get("execution_mode") == "AUTO_EXECUTE") or (task.get("status") == "approved")
        if is_ready:
            if key in executed_entities_week:
                print(f"[GOVERNANCE] Prevented duplicate execution for {task['entity']} in {task['scheduled_time']}")
                continue
                
            platform = task["platform"]
            if platform == "youtube":
                res = execute_youtube_publish(task)
            elif platform == "pinterest":
                res = execute_pinterest_publish(task)
            else:
                res = execute_blog_publish(task)
                
            task["status"] = "executed"
            task["execution_log"] = res
            executed_entities_week.add(key)
            
    return tasks
