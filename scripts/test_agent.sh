#!/bin/bash
# Agent Testing Script (Shell version)
# Quick testing utilities using curl - no Python required

SERVER_URL=${SERVER_URL:-"http://localhost:5109"}

echo "🧪 Agent Testing Script"
echo "Server: $SERVER_URL"
echo

# Function to make API calls
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ "$method" = "POST" ]; then
        if [ -n "$data" ]; then
            curl -s -X POST "$SERVER_URL$endpoint" \
                 -H "Content-Type: application/json" \
                 -d "$data"
        else
            curl -s -X POST "$SERVER_URL$endpoint"
        fi
    else
        curl -s "$SERVER_URL$endpoint"
    fi
}

# Reload both skills and agents, and restart agent sessions
reload() {
    echo "🔄 Reloading skills and agents..."
    echo "Skills:"
    response=$(api_call POST "/server/skills/reload")
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    echo
    echo "Agents:"
    response=$(api_call POST "/server/agents/reload")
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    echo
    echo "🔄 Restarting agent sessions..."
    response=$(api_call GET "/server/sessions")
    sessions=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    sessions = data.get('sessions', [])
    print(' '.join([s.get('id', '') for s in sessions if s.get('id')]))
except:
    print('')
" 2>/dev/null)

    if [ -z "$sessions" ]; then
        echo "No active sessions to restart"
    else
        echo "Restarting sessions: $sessions"
        for session_id in $sessions; do
            response=$(api_call DELETE "/server/sessions/$session_id")
            success=$(echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('true' if data.get('success') else 'false')
except:
    print('false')
" 2>/dev/null)

            if [ "$success" = "true" ]; then
                echo "  ✅ Deleted session: $session_id"
            else
                echo "  ⚠️  Session not found: $session_id (already deleted)"
            fi
        done
        echo "✅ Agent sessions restarted - configs updated!"
    fi
}

# List skills
list_skills() {
    echo "📋 Listing skills..."
    response=$(api_call GET "/server/skills")
    echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    skills = data.get('skills', [])
    print(f'Found {len(skills)} skills:')
    for skill in skills:
        device_icon = '🔌' if skill.get('requires_device') else '📝'
        platform = skill.get('platform') or 'all'
        name = skill['name'][:20].ljust(20)
        desc = skill['description'][:50]
        print(f'{device_icon} {name} ({platform:6}) - {desc}')
except:
    print('Raw response:')
    print(sys.stdin.read())
" 2>/dev/null || echo "$response"
}

# Test specific skill
test_skill() {
    local skill_name=$1
    echo "🧪 Testing skill: $skill_name"
    response=$(api_call POST "/server/skills/test/$skill_name")
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
}

# Match skill against message
match_skill() {
    local message="$*"
    echo "🎯 Testing skill matching for: '$message'"
    data="{\"message\": \"$message\"}"
    response=$(api_call POST "/server/skills/match" "$data")
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
}

# Show usage
usage() {
    echo "Usage: $0 <command> [args]"
    echo
    echo "Commands:"
    echo "  reload         Reload skills/agents + restart sessions (full refresh)"
    echo "  list           List all available skills"
    echo "  test <skill>   Test specific skill validity"
    echo "  match <msg>    Test skill matching against message"
    echo
    echo "Examples:"
    echo "  $0 reload"
    echo "  $0 list"
    echo "  $0 test device-control"
    echo "  $0 match 'swipe down on device1'"
    echo
    echo "Environment variables:"
    echo "  SERVER_URL     Server URL (default: http://localhost:5109)"
}

# Main command handling
case "$1" in
    reload)
        reload
        ;;
    list)
        list_skills
        ;;
    test)
        if [ -z "$2" ]; then
            echo "❌ Skill name required"
            usage
            exit 1
        fi
        test_skill "$2"
        ;;
    match)
        if [ -z "$2" ]; then
            echo "❌ Message required"
            usage
            exit 1
        fi
        shift
        match_skill "$@"
        ;;
    *)
        usage
        exit 1
        ;;
esac
