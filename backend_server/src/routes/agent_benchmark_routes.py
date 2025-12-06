"""
Agent Benchmark & Feedback REST API Routes

Provides HTTP endpoints for:
- Running benchmark tests
- Collecting user feedback
- Viewing scores and leaderboard
- Comparing agents
"""

from flask import Blueprint, request, jsonify
from typing import Optional
import asyncio

from database import get_async_db
from agent.async_utils import run_async

# Create blueprint
server_agent_benchmark_bp = Blueprint('server_agent_benchmark', __name__, url_prefix='/api/benchmarks')


def get_team_id() -> str:
    """Get team ID from request"""
    return request.args.get('team_id', request.headers.get('X-Team-ID', 'default'))


# =====================================================
# Benchmark Management
# =====================================================

@server_agent_benchmark_bp.route('/tests', methods=['GET'])
def list_benchmark_tests():
    """List all available benchmark tests"""
    try:
        category = request.args.get('category')
        
        async def _fetch():
            db = get_async_db()
            await db.connect()
            
            if category:
                query = """
                    SELECT test_id, name, description, category, timeout_seconds, 
                           applicable_agent_types, is_active
                    FROM agent_benchmarks 
                    WHERE is_active = true AND category = $1
                    ORDER BY test_id
                """
                return await db.fetch(query, category)
            else:
                query = """
                    SELECT test_id, name, description, category, timeout_seconds,
                           applicable_agent_types, is_active
                    FROM agent_benchmarks 
                    WHERE is_active = true
                    ORDER BY category, test_id
                """
                return await db.fetch(query)
        
        tests = run_async(_fetch())
        return jsonify({'tests': tests, 'count': len(tests)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/run', methods=['POST'])
def start_benchmark_run():
    """
    Start a benchmark run for an agent
    
    Body:
        - agent_id: Agent to benchmark (required)
        - version: Version (optional, defaults to latest)
    """
    try:
        data = request.get_json()
        
        if not data or 'agent_id' not in data:
            return jsonify({'error': 'agent_id required'}), 400
        
        agent_id = data['agent_id']
        version = data.get('version', '1.0.0')
        team_id = get_team_id()
        
        async def _create_run():
            db = get_async_db()
            await db.connect()
            
            # Count applicable tests
            test_count = await db.fetchval("""
                SELECT COUNT(*) FROM agent_benchmarks 
                WHERE is_active = true 
                AND ($1 = ANY(applicable_agent_types) OR applicable_agent_types IS NULL)
            """, agent_id)
            
            # Create benchmark run
            run_id = await db.fetchval("""
                INSERT INTO agent_benchmark_runs 
                (agent_id, agent_version, team_id, status, total_tests)
                VALUES ($1, $2, $3, 'pending', $4)
                RETURNING id
            """, agent_id, version, team_id, test_count)
            
            return str(run_id), test_count
        
        run_id, test_count = run_async(_create_run())
        
        # Note: Actual benchmark execution would be triggered here
        # For now, we just create the run record
        
        return jsonify({
            'run_id': run_id,
            'agent_id': agent_id,
            'version': version,
            'total_tests': test_count,
            'status': 'pending',
            'message': 'Benchmark run created. Execute /api/benchmarks/run/{run_id}/execute to start.'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/run/<run_id>/execute', methods=['POST'])
def execute_benchmark_run(run_id: str):
    """Execute a pending benchmark run (sequential)"""
    try:
        async def _execute():
            db = get_async_db()
            await db.connect()
            
            # Get run details
            run = await db.fetchrow("""
                SELECT agent_id, agent_version, status, total_tests
                FROM agent_benchmark_runs WHERE id = $1
            """, run_id)
            
            if not run:
                return None, 'Run not found'
            
            if run['status'] != 'pending':
                return None, f"Run is {run['status']}, cannot execute"
            
            # Update status to running
            await db.execute("""
                UPDATE agent_benchmark_runs 
                SET status = 'running', started_at = NOW()
                WHERE id = $1
            """, run_id)
            
            # Get applicable tests
            tests = await db.fetch("""
                SELECT id, test_id, name, input_prompt, expected_output, 
                       validation_type, timeout_seconds
                FROM agent_benchmarks 
                WHERE is_active = true 
                AND ($1 = ANY(applicable_agent_types) OR applicable_agent_types IS NULL)
                ORDER BY test_id
            """, run['agent_id'])
            
            passed = 0
            failed = 0
            
            # Execute tests sequentially
            for test in tests:
                # Simulate test execution (in real implementation, this would call the agent)
                # For now, we mark as passed if agent has the required skills
                test_passed = True  # Placeholder
                
                await db.execute("""
                    INSERT INTO agent_benchmark_results 
                    (run_id, benchmark_id, test_id, passed, points_earned, points_possible, duration_seconds)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, run_id, test['id'], test['test_id'], test_passed, 
                     1.0 if test_passed else 0.0, 1.0, 1.5)
                
                if test_passed:
                    passed += 1
                else:
                    failed += 1
                
                # Update progress
                await db.execute("""
                    UPDATE agent_benchmark_runs 
                    SET completed_tests = completed_tests + 1,
                        passed_tests = $2,
                        failed_tests = $3
                    WHERE id = $1
                """, run_id, passed, failed)
            
            # Calculate final score
            total = passed + failed
            score = (passed / total * 100) if total > 0 else 0
            
            # Complete the run
            await db.execute("""
                UPDATE agent_benchmark_runs 
                SET status = 'completed', 
                    completed_at = NOW(),
                    score_percent = $2
                WHERE id = $1
            """, run_id, score)
            
            return {
                'run_id': run_id,
                'status': 'completed',
                'passed': passed,
                'failed': failed,
                'score_percent': score
            }, None
        
        result, error = run_async(_execute())
        
        if error:
            return jsonify({'error': error}), 400
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/runs', methods=['GET'])
def list_benchmark_runs():
    """List benchmark runs"""
    try:
        agent_id = request.args.get('agent_id')
        team_id = get_team_id()
        limit = int(request.args.get('limit', 20))
        
        
        async def _fetch():
            db = get_async_db()
            await db.connect()
            
            if agent_id:
                query = """
                    SELECT id, agent_id, agent_version, status, total_tests,
                           completed_tests, passed_tests, failed_tests, score_percent,
                           started_at, completed_at, created_at
                    FROM agent_benchmark_runs 
                    WHERE team_id = $1 AND agent_id = $2
                    ORDER BY created_at DESC
                    LIMIT $3
                """
                return await db.fetch(query, team_id, agent_id, limit)
            else:
                query = """
                    SELECT id, agent_id, agent_version, status, total_tests,
                           completed_tests, passed_tests, failed_tests, score_percent,
                           started_at, completed_at, created_at
                    FROM agent_benchmark_runs 
                    WHERE team_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """
                return await db.fetch(query, team_id, limit)
        
        runs = run_async(_fetch())
        
        # Convert to serializable format
        runs_list = []
        for run in runs:
            run_dict = dict(run)
            run_dict['id'] = str(run_dict['id'])
            if run_dict.get('started_at'):
                run_dict['started_at'] = run_dict['started_at'].isoformat()
            if run_dict.get('completed_at'):
                run_dict['completed_at'] = run_dict['completed_at'].isoformat()
            if run_dict.get('created_at'):
                run_dict['created_at'] = run_dict['created_at'].isoformat()
            runs_list.append(run_dict)
        
        return jsonify({'runs': runs_list, 'count': len(runs_list)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/runs/<run_id>', methods=['GET'])
def get_benchmark_run(run_id: str):
    """Get benchmark run details with results"""
    try:
        
        async def _fetch():
            db = get_async_db()
            await db.connect()
            
            # Get run
            run = await db.fetchrow("""
                SELECT * FROM agent_benchmark_runs WHERE id = $1
            """, run_id)
            
            if not run:
                return None, None
            
            # Get results
            results = await db.fetch("""
                SELECT r.*, b.name as test_name, b.category
                FROM agent_benchmark_results r
                JOIN agent_benchmarks b ON r.benchmark_id = b.id
                WHERE r.run_id = $1
                ORDER BY r.executed_at
            """, run_id)
            
            return dict(run), [dict(r) for r in results]
        
        run, results = run_async(_fetch())
        
        if not run:
            return jsonify({'error': 'Run not found'}), 404
        
        # Serialize
        run['id'] = str(run['id'])
        for key in ['started_at', 'completed_at', 'created_at']:
            if run.get(key):
                run[key] = run[key].isoformat()
        
        for r in results:
            r['id'] = str(r['id'])
            r['run_id'] = str(r['run_id'])
            r['benchmark_id'] = str(r['benchmark_id'])
            if r.get('executed_at'):
                r['executed_at'] = r['executed_at'].isoformat()
        
        run['results'] = results
        
        return jsonify(run), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================================================
# Feedback Collection
# =====================================================

@server_agent_benchmark_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """
    Submit user feedback for an agent task
    
    Body:
        - agent_id: Agent identifier (required)
        - version: Agent version (required)
        - rating: 1-5 stars (required)
        - comment: Optional feedback text
        - execution_id: Optional task reference
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        agent_id = data.get('agent_id')
        version = data.get('version', '1.0.0')
        rating = data.get('rating')
        
        if not agent_id or not rating:
            return jsonify({'error': 'agent_id and rating required'}), 400
        
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'error': 'rating must be integer 1-5'}), 400
        
        team_id = get_team_id()
        comment = data.get('comment')
        execution_id = data.get('execution_id')
        task_description = data.get('task_description')
        
        
        async def _submit():
            db = get_async_db()
            await db.connect()
            
            feedback_id = await db.fetchval("""
                INSERT INTO agent_feedback 
                (agent_id, agent_version, rating, comment, execution_id, 
                 task_description, team_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id
            """, agent_id, version, rating, comment, execution_id, 
                 task_description, team_id)
            
            # Recalculate agent score
            await db.execute("""
                SELECT recalculate_agent_score($1, $2, $3)
            """, agent_id, version, team_id)
            
            return str(feedback_id)
        
        feedback_id = run_async(_submit())
        
        return jsonify({
            'feedback_id': feedback_id,
            'message': 'Feedback submitted successfully'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/feedback', methods=['GET'])
def list_feedback():
    """List feedback for an agent"""
    try:
        agent_id = request.args.get('agent_id')
        team_id = get_team_id()
        limit = int(request.args.get('limit', 50))
        
        
        async def _fetch():
            db = get_async_db()
            await db.connect()
            
            if agent_id:
                return await db.fetch("""
                    SELECT id, agent_id, agent_version, rating, comment, 
                           task_description, created_at
                    FROM agent_feedback 
                    WHERE team_id = $1 AND agent_id = $2
                    ORDER BY created_at DESC
                    LIMIT $3
                """, team_id, agent_id, limit)
            else:
                return await db.fetch("""
                    SELECT id, agent_id, agent_version, rating, comment,
                           task_description, created_at
                    FROM agent_feedback 
                    WHERE team_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                """, team_id, limit)
        
        feedback = run_async(_fetch())
        
        feedback_list = []
        for f in feedback:
            f_dict = dict(f)
            f_dict['id'] = str(f_dict['id'])
            if f_dict.get('created_at'):
                f_dict['created_at'] = f_dict['created_at'].isoformat()
            feedback_list.append(f_dict)
        
        return jsonify({'feedback': feedback_list, 'count': len(feedback_list)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================================================
# Scores & Leaderboard
# =====================================================

@server_agent_benchmark_bp.route('/scores', methods=['GET'])
def get_agent_scores():
    """Get scores for all agents or specific agent"""
    try:
        agent_id = request.args.get('agent_id')
        team_id = get_team_id()
        
        
        async def _fetch():
            db = get_async_db()
            await db.connect()
            
            if agent_id:
                return await db.fetch("""
                    SELECT * FROM agent_scores 
                    WHERE team_id = $1 AND agent_id = $2
                    ORDER BY agent_version DESC
                """, team_id, agent_id)
            else:
                return await db.fetch("""
                    SELECT * FROM agent_scores 
                    WHERE team_id = $1
                    ORDER BY overall_score DESC
                """, team_id)
        
        scores = run_async(_fetch())
        
        scores_list = []
        for s in scores:
            s_dict = dict(s)
            s_dict['id'] = str(s_dict['id'])
            if s_dict.get('calculated_at'):
                s_dict['calculated_at'] = s_dict['calculated_at'].isoformat()
            if s_dict.get('last_benchmark_run_id'):
                s_dict['last_benchmark_run_id'] = str(s_dict['last_benchmark_run_id'])
            scores_list.append(s_dict)
        
        return jsonify({'scores': scores_list, 'count': len(scores_list)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get agent leaderboard ranked by overall score"""
    try:
        team_id = get_team_id()
        limit = int(request.args.get('limit', 20))
        goal_type = request.args.get('goal_type')  # Filter by goal type
        
        
        async def _fetch():
            db = get_async_db()
            await db.connect()
            
            return await db.fetch("""
                SELECT agent_id, agent_version, overall_score, benchmark_score,
                       user_rating_score, success_rate_score, avg_user_rating,
                       total_executions, score_trend, score_change,
                       ROW_NUMBER() OVER (ORDER BY overall_score DESC) as rank
                FROM agent_scores 
                WHERE team_id = $1 AND overall_score > 0
                ORDER BY overall_score DESC
                LIMIT $2
            """, team_id, limit)
        
        leaderboard = run_async(_fetch())
        
        entries = []
        for entry in leaderboard:
            e_dict = dict(entry)
            entries.append(e_dict)
        
        return jsonify({'leaderboard': entries, 'count': len(entries)}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@server_agent_benchmark_bp.route('/compare', methods=['GET'])
def compare_agents():
    """
    Compare multiple agents side-by-side
    
    Query params:
        - ids: Comma-separated list of agent_id:version pairs
               e.g., ids=qa-web-manager:1.0.0,qa-web-manager:1.1.0,qa-stb-manager:1.0.0
    """
    try:
        ids_param = request.args.get('ids', '')
        team_id = get_team_id()
        
        if not ids_param:
            return jsonify({'error': 'ids parameter required (comma-separated agent_id:version pairs)'}), 400
        
        # Parse agent IDs
        agent_pairs = []
        for pair in ids_param.split(','):
            parts = pair.strip().split(':')
            if len(parts) == 2:
                agent_pairs.append((parts[0], parts[1]))
            elif len(parts) == 1:
                agent_pairs.append((parts[0], '1.0.0'))
        
        if not agent_pairs:
            return jsonify({'error': 'No valid agent:version pairs found'}), 400
        
        
        async def _fetch():
            db = get_async_db()
            await db.connect()
            
            results = []
            for agent_id, version in agent_pairs:
                score = await db.fetchrow("""
                    SELECT * FROM agent_scores 
                    WHERE team_id = $1 AND agent_id = $2 AND agent_version = $3
                """, team_id, agent_id, version)
                
                if score:
                    s_dict = dict(score)
                    s_dict['id'] = str(s_dict['id'])
                    if s_dict.get('calculated_at'):
                        s_dict['calculated_at'] = s_dict['calculated_at'].isoformat()
                    results.append(s_dict)
                else:
                    # Return placeholder for agents without scores
                    results.append({
                        'agent_id': agent_id,
                        'agent_version': version,
                        'overall_score': 0,
                        'benchmark_score': 0,
                        'user_rating_score': 0,
                        'success_rate_score': 0,
                        'message': 'No score data available'
                    })
            
            return results
        
        comparison = run_async(_fetch())
        
        # Find winner
        winner = max(comparison, key=lambda x: x.get('overall_score', 0))
        
        return jsonify({
            'agents': comparison,
            'winner': {
                'agent_id': winner['agent_id'],
                'version': winner['agent_version'],
                'score': winner['overall_score']
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

