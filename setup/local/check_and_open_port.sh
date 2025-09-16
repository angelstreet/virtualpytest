#!/bin/bash

# VirtualPyTest - Port Checking and UFW Configuration
# This function checks if a port is accessible and opens it via UFW if needed
# Usage: check_and_open_port <port> <service_name> [protocol]

check_and_open_port() {
    local port="$1"
    local service_name="$2"
    local protocol="${3:-tcp}"
    
    if [ -z "$port" ] || [ -z "$service_name" ]; then
        echo "❌ Usage: check_and_open_port <port> <service_name> [protocol]"
        return 1
    fi
    
    echo "🔍 Checking port $port for $service_name..."
    
    # Check if UFW is installed
    if ! command -v ufw &> /dev/null; then
        echo "⚠️ UFW not installed. Port $port may be blocked by firewall."
        echo "   Install UFW: sudo apt-get install ufw"
        return 0
    fi
    
    # Check if UFW is active
    local ufw_status
    ufw_status=$(sudo ufw status 2>/dev/null | head -n1)
    
    if [[ "$ufw_status" == *"inactive"* ]]; then
        echo "ℹ️ UFW is inactive. Port $port should be accessible."
        return 0
    fi
    
    # Check if port is already allowed in UFW
    local port_allowed
    port_allowed=$(sudo ufw status numbered 2>/dev/null | grep -E "^\\[.*\\].*$port($protocol|/tcp|/udp)" || true)
    
    if [ -n "$port_allowed" ]; then
        echo "✅ Port $port/$protocol is already allowed in UFW for $service_name"
        return 0
    fi
    
    # Port is not allowed, ask user to open it
    echo "🚫 Port $port/$protocol is not allowed in UFW"
    echo "   This may prevent $service_name from being accessible"
    echo ""
    
    # Check if running interactively
    if [ -t 0 ]; then
        read -p "🔓 Open port $port/$protocol in UFW? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo "⚠️ Port $port not opened. $service_name may not be accessible from other devices."
            return 0
        fi
    else
        echo "🔓 Non-interactive mode: Opening port $port/$protocol automatically..."
    fi
    
    # Open the port
    echo "🔓 Opening port $port/$protocol for $service_name..."
    if sudo ufw allow "$port/$protocol" 2>/dev/null; then
        echo "✅ Port $port/$protocol opened successfully"
        
        # Show updated UFW status
        echo "📋 Updated UFW status:"
        sudo ufw status numbered | grep -E "(Status:|$port)" || true
    else
        echo "❌ Failed to open port $port/$protocol"
        echo "   You may need to open it manually: sudo ufw allow $port/$protocol"
        return 1
    fi
    
    return 0
}

# Function to check if a port is in use by another process
check_port_availability() {
    local port="$1"
    local service_name="$2"
    
    if [ -z "$port" ] || [ -z "$service_name" ]; then
        echo "❌ Usage: check_port_availability <port> <service_name>"
        return 1
    fi
    
    echo "🔍 Checking if port $port is available for $service_name..."
    
    # Check if port is in use
    if command -v lsof &> /dev/null; then
        local port_usage
        port_usage=$(lsof -ti:$port 2>/dev/null || true)
        
        if [ -n "$port_usage" ]; then
            echo "⚠️ Port $port is already in use by process(es): $port_usage"
            echo "🛑 Killing processes on port $port..."
            echo "$port_usage" | xargs kill -9 2>/dev/null || true
            sleep 1
            
            # Verify port is now free
            port_usage=$(lsof -ti:$port 2>/dev/null || true)
            if [ -n "$port_usage" ]; then
                echo "❌ Failed to free port $port. Process(es) still running: $port_usage"
                return 1
            fi
        fi
    elif command -v netstat &> /dev/null; then
        local port_usage
        port_usage=$(netstat -tlnp 2>/dev/null | grep ":$port " || true)
        
        if [ -n "$port_usage" ]; then
            echo "⚠️ Port $port appears to be in use:"
            echo "$port_usage"
            echo "   You may need to manually stop the conflicting service"
        fi
    else
        echo "⚠️ Cannot check port usage (lsof and netstat not available)"
    fi
    
    echo "✅ Port $port is available for $service_name"
    return 0
}

# Function to get port from environment file
get_port_from_env() {
    local env_file="$1"
    local port_var="$2"
    local default_port="$3"
    
    if [ -f "$env_file" ]; then
        # Source the env file and get the port
        local port_value
        port_value=$(grep "^$port_var=" "$env_file" 2>/dev/null | cut -d'=' -f2 | tr -d '"' || echo "$default_port")
        echo "${port_value:-$default_port}"
    else
        echo "$default_port"
    fi
}

# Export functions for use in other scripts
export -f check_and_open_port
export -f check_port_availability  
export -f get_port_from_env
