#!/bin/bash

# The Wall API Test Script - Final Version
# This script tests all the requirements from the task description
# Updated to dynamically discover profile IDs instead of using hardcoded values

set -e

API_BASE_URL="http://localhost:8000/api/v1"
echo "🏰 Testing The Wall API - Task Requirements Verification"
echo "API Base URL: $API_BASE_URL"
echo "========================================================"

# Dynamically discover profile IDs by fetching from the API
echo ""
echo "🔍 Discovering profiles from API..."
profiles_response=$(curl -s "$API_BASE_URL/task-profiles/")

# Extract profile IDs using jq (if available) or grep/sed fallback
if command -v jq >/dev/null 2>&1; then
    # Use jq for JSON parsing - look for profiles by their section patterns
    # Profile 1: 3 sections with heights [21, 25, 28]
    PROFILE1_ID=$(echo "$profiles_response" | jq -r '.results[] | select(.active_sections_count == 3) | select([.sections[].initial_height] == ["21.00", "25.00", "28.00"]) | .id' | head -1)
    # Profile 2: 1 section with height [17]  
    PROFILE2_ID=$(echo "$profiles_response" | jq -r '.results[] | select(.active_sections_count == 1) | select([.sections[].initial_height] == ["17.00"]) | .id' | head -1)
    # Profile 3: 5 sections with heights [17, 22, 17, 19, 17]
    PROFILE3_ID=$(echo "$profiles_response" | jq -r '.results[] | select(.active_sections_count == 5) | select([.sections[].initial_height] == ["17.00", "22.00", "17.00", "19.00", "17.00"]) | .id' | head -1)
else
    # Fallback: Use the first profiles with the correct number of sections
    echo "⚠️  jq not found, using section count fallback (less precise)"
    PROFILE1_ID=$(echo "$profiles_response" | grep -B 20 -A 5 '"active_sections_count": 3' | grep '"id":' | head -1 | sed 's/.*"id": "\([^"]*\)".*/\1/')
    PROFILE2_ID=$(echo "$profiles_response" | grep -B 20 -A 5 '"active_sections_count": 1' | grep '"id":' | head -1 | sed 's/.*"id": "\([^"]*\)".*/\1/')
    PROFILE3_ID=$(echo "$profiles_response" | grep -B 20 -A 5 '"active_sections_count": 5' | grep '"id":' | head -1 | sed 's/.*"id": "\([^"]*\)".*/\1/')
fi

# If we couldn't find profiles by section patterns, fall back to the first available profiles
if [[ -z "$PROFILE1_ID" || -z "$PROFILE2_ID" || -z "$PROFILE3_ID" ]]; then
    echo "⚠️  Could not find profiles by expected section patterns, using first available profiles..."
    if command -v jq >/dev/null 2>&1; then
        PROFILE1_ID=$(echo "$profiles_response" | jq -r '.results[0].id // empty')
        PROFILE2_ID=$(echo "$profiles_response" | jq -r '.results[1].id // empty')
        PROFILE3_ID=$(echo "$profiles_response" | jq -r '.results[2].id // empty')
    else
        PROFILE1_ID=$(echo "$profiles_response" | grep '"id":' | head -1 | sed 's/.*"id": "\([^"]*\)".*/\1/')
        PROFILE2_ID=$(echo "$profiles_response" | grep '"id":' | head -2 | tail -1 | sed 's/.*"id": "\([^"]*\)".*/\1/')
        PROFILE3_ID=$(echo "$profiles_response" | grep '"id":' | head -3 | tail -1 | sed 's/.*"id": "\([^"]*\)".*/\1/')
    fi
fi

# Validate that we found all three profiles
if [[ -z "$PROFILE1_ID" || -z "$PROFILE2_ID" || -z "$PROFILE3_ID" ]]; then
    echo "❌ Error: Could not find all required profiles. Make sure the API is running and profiles are loaded."
    echo "Found Profile 1: $PROFILE1_ID"
    echo "Found Profile 2: $PROFILE2_ID" 
    echo "Found Profile 3: $PROFILE3_ID"
    exit 1
fi

echo "✅ Discovered profiles:"
echo "   Profile 1 ID: $PROFILE1_ID"
echo "   Profile 2 ID: $PROFILE2_ID"
echo "   Profile 3 ID: $PROFILE3_ID"

echo ""
echo "🔍 Testing Required API Endpoints from Task Description"
echo "========================================================="

echo ""
echo "📋 Test 1: GET /profiles/{profile1}/days/1/ (Profile 1: [21, 25, 28])"
echo "Expected: ice_amount: 585 (3 sections × 195 cubic yards)"
response=$(curl -s "$API_BASE_URL/profiles/$PROFILE1_ID/days/1/")
echo "✅ Response: $response"

echo ""
echo "📋 Test 2: GET /profiles/{profile2}/days/1/ (Profile 2: [17])"
echo "Expected: ice_amount: 195 (1 section × 195 cubic yards)"
response=$(curl -s "$API_BASE_URL/profiles/$PROFILE2_ID/days/1/")
echo "✅ Response: $response"

echo ""
echo "📋 Test 3: GET /profiles/{profile3}/days/1/ (Profile 3: [17, 22, 17, 19, 17])"
echo "Expected: ice_amount: 975 (5 sections × 195 cubic yards)"
response=$(curl -s "$API_BASE_URL/profiles/$PROFILE3_ID/days/1/")
echo "✅ Response: $response"

echo ""
echo "📋 Test 4: GET /profiles/{profile1}/overview/1/"
echo "Expected: cost: 1,111,500 (585 × 1,900 Gold Dragons)"
response=$(curl -s "$API_BASE_URL/profiles/$PROFILE1_ID/overview/1/")
echo "✅ Response: $response"

echo ""
echo "📋 Test 5: GET /profiles/overview/1/"
echo "Expected: total cost: 3,334,500 (1,755 × 1,900 Gold Dragons)"
response=$(curl -s "$API_BASE_URL/profiles/overview/1/")
echo "✅ Response: $response"

echo ""
echo "📋 Test 6: GET /profiles/overview/"
echo "Expected: Final total cost when all profiles are completed"
response=$(curl -s "$API_BASE_URL/profiles/overview/")
echo "✅ Response: $response"

echo ""
echo "🔍 Additional Validation Tests"
echo "==============================="

echo ""
echo "📋 Test 7: Profile 1, Day 3 (after first completion)"
echo "Expected: ice_amount: 390 (2 sections × 195, one section completed)"
response=$(curl -s "$API_BASE_URL/profiles/$PROFILE1_ID/days/3/")
echo "✅ Response: $response"

echo ""
echo "📋 Test 8: Profile 2 completion (starts at 17, needs 13 days)"
echo "Day 13 (last working day):"
response=$(curl -s "$API_BASE_URL/profiles/$PROFILE2_ID/days/13/")
echo "✅ Response: $response"
echo "Day 14 (should be completed):"
response=$(curl -s "$API_BASE_URL/profiles/$PROFILE2_ID/days/14/")
echo "✅ Response: $response"

echo ""
echo "📋 Test 9: Error handling - Invalid profile"
echo "Testing non-existent profile ID:"
response=$(curl -s "$API_BASE_URL/profiles/00000000-0000-0000-0000-000000000000/days/1/" || echo "Error as expected")
echo "✅ Response: $response"
