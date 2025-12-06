"""
Agent Benchmarks & Feedback Database Operations

Manages:
- Benchmark test definitions
- Benchmark runs and results
- User feedback collection
- Agent scores and leaderboard
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from shared.src.lib.utils.supabase_utils import get_supabase_client

DEFAULT_TEAM_ID = 'default'


def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()


# =====================================================
# Benchmark Tests
# =====================================================

def list_benchmark_tests(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all available benchmark tests.
    
    Args:
        category: Optional category filter (navigation, detection, execution, analysis, recovery)
        
    Returns:
        List of benchmark test definitions
    """
    supabase = get_supabase()
    if not supabase:
        return []
    
    query = supabase.table('agent_benchmarks').select('*').eq('is_active', True)
    
    if category:
        query = query.eq('category', category)
    
    result = query.order('test_id').execute()
    return result.data if result.data else []


def get_benchmark_test(test_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific benchmark test by test_id."""
    supabase = get_supabase()
    if not supabase:
        return None
    
    result = supabase.table('agent_benchmarks').select('*').eq('test_id', test_id).execute()
    return result.data[0] if result.data else None


# =====================================================
# Benchmark Runs
# =====================================================

def create_benchmark_run(
    agent_id: str,
    agent_version: str,
    team_id: str = DEFAULT_TEAM_ID
) -> Optional[Dict[str, Any]]:
    """
    Create a new benchmark run for an agent.
    
    Args:
        agent_id: Agent identifier (e.g., 'qa-web-manager')
        agent_version: Agent version (e.g., '1.0.0')
        team_id: Team ID
        
    Returns:
        Created run record or None on error
    """
    supabase = get_supabase()
    if not supabase:
        return None
    
    # Count applicable tests
    tests = list_benchmark_tests()
    test_count = len(tests)
    
    run_data = {
        'agent_id': agent_id,
        'agent_version': agent_version,
        'team_id': team_id,
        'status': 'pending',
        'total_tests': test_count,
        'completed_tests': 0,
        'passed_tests': 0,
        'failed_tests': 0
    }
    
    result = supabase.table('agent_benchmark_runs').insert(run_data).execute()
    return result.data[0] if result.data else None


def get_benchmark_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Get a benchmark run by ID."""
    supabase = get_supabase()
    if not supabase:
        return None
    
    result = supabase.table('agent_benchmark_runs').select('*').eq('id', run_id).execute()
    return result.data[0] if result.data else None


def update_benchmark_run(run_id: str, updates: Dict[str, Any]) -> bool:
    """
    Update a benchmark run.
    
    Args:
        run_id: Run UUID
        updates: Fields to update
        
    Returns:
        True if successful
    """
    supabase = get_supabase()
    if not supabase:
        return False
    
    supabase.table('agent_benchmark_runs').update(updates).eq('id', run_id).execute()
    return True


def list_benchmark_runs(
    team_id: str = DEFAULT_TEAM_ID,
    agent_id: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    List benchmark runs.
    
    Args:
        team_id: Team ID filter
        agent_id: Optional agent ID filter
        limit: Max results
        
    Returns:
        List of benchmark runs
    """
    supabase = get_supabase()
    if not supabase:
        return []
    
    query = supabase.table('agent_benchmark_runs').select('*').eq('team_id', team_id)
    
    if agent_id:
        query = query.eq('agent_id', agent_id)
    
    result = query.order('created_at', desc=True).limit(limit).execute()
    return result.data if result.data else []


def execute_benchmark_run(run_id: str) -> Dict[str, Any]:
    """
    Execute a pending benchmark run.
    
    Args:
        run_id: Run UUID
        
    Returns:
        {success: bool, passed: int, failed: int, score_percent: float, error: str}
    """
    supabase = get_supabase()
    if not supabase:
        return {'success': False, 'error': 'Database not available'}
    
    # Get run
    run = get_benchmark_run(run_id)
    if not run:
        return {'success': False, 'error': 'Run not found'}
    
    if run['status'] != 'pending':
        return {'success': False, 'error': f"Run is {run['status']}, cannot execute"}
    
    # Update to running
    update_benchmark_run(run_id, {
        'status': 'running',
        'started_at': datetime.now().isoformat()
    })
    
    # Get tests
    tests = list_benchmark_tests()
    
    passed = 0
    failed = 0
    
    for test in tests:
        # Simulate test execution (placeholder - real implementation would call agent)
        test_passed = True
        
        # Record result
        result_data = {
            'run_id': run_id,
            'benchmark_id': test['id'],
            'test_id': test['test_id'],
            'passed': test_passed,
            'points_earned': 1.0 if test_passed else 0.0,
            'points_possible': 1.0,
            'duration_seconds': 1.5
        }
        supabase.table('agent_benchmark_results').insert(result_data).execute()
        
        if test_passed:
            passed += 1
        else:
            failed += 1
        
        # Update progress
        update_benchmark_run(run_id, {
            'completed_tests': passed + failed,
            'passed_tests': passed,
            'failed_tests': failed
        })
    
    # Calculate score
    total = passed + failed
    score = (passed / total * 100) if total > 0 else 0
    
    # Complete run
    update_benchmark_run(run_id, {
        'status': 'completed',
        'completed_at': datetime.now().isoformat(),
        'score_percent': score
    })
    
    return {
        'success': True,
        'passed': passed,
        'failed': failed,
        'score_percent': score
    }


def get_benchmark_results(run_id: str) -> List[Dict[str, Any]]:
    """Get results for a benchmark run."""
    supabase = get_supabase()
    if not supabase:
        return []
    
    result = supabase.table('agent_benchmark_results').select('*').eq('run_id', run_id).order('executed_at').execute()
    return result.data if result.data else []


# =====================================================
# User Feedback
# =====================================================

def submit_feedback(
    agent_id: str,
    agent_version: str,
    rating: int,
    team_id: str = DEFAULT_TEAM_ID,
    comment: Optional[str] = None,
    execution_id: Optional[str] = None,
    task_description: Optional[str] = None
) -> Optional[str]:
    """
    Submit user feedback for an agent.
    
    Args:
        agent_id: Agent identifier
        agent_version: Agent version
        rating: 1-5 stars
        team_id: Team ID
        comment: Optional feedback text
        execution_id: Optional task/execution reference
        task_description: Optional task description
        
    Returns:
        Feedback ID or None on error
    """
    if rating < 1 or rating > 5:
        return None
    
    supabase = get_supabase()
    if not supabase:
        return None
    
    feedback_data = {
        'agent_id': agent_id,
        'agent_version': agent_version,
        'rating': rating,
        'comment': comment,
        'execution_id': execution_id,
        'task_description': task_description,
        'team_id': team_id
    }
    
    result = supabase.table('agent_feedback').insert(feedback_data).execute()
    return result.data[0]['id'] if result.data else None


def list_feedback(
    team_id: str = DEFAULT_TEAM_ID,
    agent_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """List feedback for agents."""
    supabase = get_supabase()
    if not supabase:
        return []
    
    query = supabase.table('agent_feedback').select('*').eq('team_id', team_id)
    
    if agent_id:
        query = query.eq('agent_id', agent_id)
    
    result = query.order('created_at', desc=True).limit(limit).execute()
    return result.data if result.data else []


# =====================================================
# Scores & Leaderboard
# =====================================================

def get_agent_scores(
    team_id: str = DEFAULT_TEAM_ID,
    agent_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get aggregated scores for agents."""
    supabase = get_supabase()
    if not supabase:
        return []
    
    query = supabase.table('agent_scores').select('*').eq('team_id', team_id)
    
    if agent_id:
        query = query.eq('agent_id', agent_id)
    
    result = query.order('overall_score', desc=True).execute()
    return result.data if result.data else []


def get_leaderboard(team_id: str = DEFAULT_TEAM_ID, limit: int = 20) -> List[Dict[str, Any]]:
    """Get agent leaderboard with rankings."""
    supabase = get_supabase()
    if not supabase:
        return []
    
    result = supabase.table('agent_scores').select('*').eq('team_id', team_id).order('overall_score', desc=True).limit(limit).execute()
    
    leaderboard = []
    for idx, entry in enumerate(result.data or []):
        entry['rank'] = idx + 1
        leaderboard.append(entry)
    
    return leaderboard


def get_agent_score(
    agent_id: str,
    agent_version: str,
    team_id: str = DEFAULT_TEAM_ID
) -> Optional[Dict[str, Any]]:
    """Get score for a specific agent version."""
    supabase = get_supabase()
    if not supabase:
        return None
    
    result = supabase.table('agent_scores').select('*').eq('team_id', team_id).eq('agent_id', agent_id).eq('agent_version', agent_version).execute()
    return result.data[0] if result.data else None


def compare_agents(
    agent_pairs: List[Dict[str, str]],
    team_id: str = DEFAULT_TEAM_ID
) -> Dict[str, Any]:
    """
    Compare multiple agents.
    
    Args:
        agent_pairs: List of {'agent_id': str, 'version': str}
        team_id: Team ID
        
    Returns:
        {comparison: [...], winner: str or None}
    """
    comparison = []
    
    for pair in agent_pairs:
        score = get_agent_score(pair['agent_id'], pair.get('version', '1.0.0'), team_id)
        
        if score:
            comparison.append(score)
        else:
            comparison.append({
                'agent_id': pair['agent_id'],
                'agent_version': pair.get('version', '1.0.0'),
                'overall_score': 0,
                'benchmark_score': 0,
                'user_rating_score': 0,
                'success_rate_score': 0
            })
    
    winner = max(comparison, key=lambda x: x.get('overall_score', 0)) if comparison else None
    
    return {
        'comparison': comparison,
        'winner': winner['agent_id'] if winner and winner.get('overall_score', 0) > 0 else None
    }

