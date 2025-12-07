"""
Agent Benchmark & Feedback REST API Routes

Thin route layer that delegates to shared/src/lib/database/agent_benchmarks_db.py
"""

from flask import Blueprint, request, jsonify

from shared.src.lib.database.agent_benchmarks_db import (
    list_benchmark_tests,
    get_benchmark_test,
    create_benchmark_run,
    get_benchmark_run,
    list_benchmark_runs,
    execute_benchmark_run,
    get_benchmark_results,
    submit_feedback,
    list_feedback,
    get_agent_scores,
    get_leaderboard,
    compare_agents
)

# Create blueprint
server_agent_benchmark_bp = Blueprint('server_agent_benchmark', __name__, url_prefix='/server/benchmarks')


def get_team_id() -> str:
    """Get team ID from request"""
    return request.args.get('team_id', request.headers.get('X-Team-ID', 'default'))


# =====================================================
# Benchmark Tests
# =====================================================

@server_agent_benchmark_bp.route('/tests', methods=['GET'])
def route_list_benchmark_tests():
    """List all available benchmark tests"""
    try:
        category = request.args.get('category')
        tests = list_benchmark_tests(category=category)
        return jsonify({'tests': tests, 'count': len(tests)}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================================================
# Benchmark Runs
# =====================================================

@server_agent_benchmark_bp.route('/run', methods=['POST'])
def route_create_benchmark_run():
    """Create a new benchmark run"""
    try:
        data = request.get_json()
        
        if not data or 'agent_id' not in data:
            return jsonify({'error': 'agent_id required'}), 400
        
        agent_id = data['agent_id']
        version = data.get('version', '1.0.0')
        team_id = get_team_id()
        
        run = create_benchmark_run(agent_id, version, team_id)
        
        if not run:
            return jsonify({'error': 'Failed to create benchmark run'}), 500
        
        return jsonify({
            'run_id': run['id'],
            'agent_id': run['agent_id'],
            'version': run['agent_version'],
            'total_tests': run['total_tests'],
            'status': run['status'],
            'message': 'Benchmark run created. Execute /server/benchmarks/run/{run_id}/execute to start.'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/run/<run_id>/execute', methods=['POST'])
def route_execute_benchmark_run(run_id: str):
    """Execute a pending benchmark run"""
    try:
        result = execute_benchmark_run(run_id)
        
        if not result.get('success'):
            return jsonify({'error': result.get('error', 'Unknown error')}), 400
        
        return jsonify({
            'run_id': run_id,
            'status': 'completed',
            'passed': result['passed'],
            'failed': result['failed'],
            'score_percent': result['score_percent']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/runs', methods=['GET'])
def route_list_benchmark_runs():
    """List benchmark runs"""
    try:
        agent_id = request.args.get('agent_id')
        team_id = get_team_id()
        limit = int(request.args.get('limit', 20))
        
        runs = list_benchmark_runs(team_id=team_id, agent_id=agent_id, limit=limit)
        
        return jsonify({'runs': runs, 'count': len(runs)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/runs/<run_id>', methods=['GET'])
def route_get_benchmark_run(run_id: str):
    """Get benchmark run details with results"""
    try:
        run = get_benchmark_run(run_id)
        
        if not run:
            return jsonify({'error': 'Run not found'}), 404
        
        results = get_benchmark_results(run_id)
        
        return jsonify({
            'run': run,
            'results': results
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================================================
# Feedback
# =====================================================

@server_agent_benchmark_bp.route('/feedback', methods=['POST'])
def route_submit_feedback():
    """Submit user feedback for an agent"""
    try:
        data = request.get_json()
        
        if not data or 'agent_id' not in data or 'rating' not in data:
            return jsonify({'error': 'agent_id and rating required'}), 400
        
        rating = int(data['rating'])
        if rating < 1 or rating > 5:
            return jsonify({'error': 'rating must be 1-5'}), 400
        
        team_id = get_team_id()
        
        feedback_id = submit_feedback(
            agent_id=data['agent_id'],
            agent_version=data.get('version', '1.0.0'),
            rating=rating,
            team_id=team_id,
            comment=data.get('comment'),
            execution_id=data.get('execution_id'),
            task_description=data.get('task_description')
        )
        
        if not feedback_id:
            return jsonify({'error': 'Failed to submit feedback'}), 500
        
        return jsonify({
            'feedback_id': feedback_id,
            'message': 'Feedback submitted successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/feedback', methods=['GET'])
def route_list_feedback():
    """List feedback for agents"""
    try:
        agent_id = request.args.get('agent_id')
        team_id = get_team_id()
        limit = int(request.args.get('limit', 50))
        
        feedback = list_feedback(team_id=team_id, agent_id=agent_id, limit=limit)
        
        return jsonify({'feedback': feedback, 'count': len(feedback)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================================================
# Scores & Leaderboard
# =====================================================

@server_agent_benchmark_bp.route('/scores', methods=['GET'])
def route_get_agent_scores():
    """Get aggregated scores for agents"""
    try:
        agent_id = request.args.get('agent_id')
        team_id = get_team_id()
        
        scores = get_agent_scores(team_id=team_id, agent_id=agent_id)
        
        return jsonify({'scores': scores, 'count': len(scores)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/leaderboard', methods=['GET'])
def route_get_leaderboard():
    """Get agent leaderboard with rankings"""
    try:
        team_id = get_team_id()
        limit = int(request.args.get('limit', 20))
        
        leaderboard = get_leaderboard(team_id=team_id, limit=limit)
        
        return jsonify({'leaderboard': leaderboard, 'count': len(leaderboard)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================================================
# Comparison
# =====================================================

@server_agent_benchmark_bp.route('/compare', methods=['GET'])
def route_compare_agents():
    """Compare two or more agents"""
    try:
        agents_param = request.args.get('agents', '')
        if not agents_param:
            return jsonify({'error': 'agents parameter required'}), 400
        
        team_id = get_team_id()
        
        # Parse agent:version pairs
        agent_pairs = []
        for pair in agents_param.split(','):
            parts = pair.strip().split(':')
            if len(parts) == 2:
                agent_pairs.append({'agent_id': parts[0], 'version': parts[1]})
            elif len(parts) == 1:
                agent_pairs.append({'agent_id': parts[0], 'version': '1.0.0'})
        
        if not agent_pairs:
            return jsonify({'error': 'No valid agent:version pairs found'}), 400
        
        result = compare_agents(agent_pairs, team_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
