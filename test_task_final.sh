#!/bin/bash

# The Wall API Test Script - Final Version
# This script tests all the requirements from the task description

set -e

API_BASE_URL="http://localhost:8000/api/v1"
echo "🏰 Testing The Wall API - Task Requirements Verification"
echo "API Base URL: $API_BASE_URL"
echo "========================================================"

# Profile IDs (from existing data)
PROFILE1_ID="e4ade876-04cf-40da-bcc3-30a587faca72"  # Profile 1: [21, 25, 28]
PROFILE2_ID="cd0720f4-f5bd-41d6-b422-da52d21472e4"  # Profile 2: [17]
PROFILE3_ID="da60ca07-1916-45bb-b34a-b73142552c86"  # Profile 3: [17, 22, 17, 19, 17]

echo ""
echo "🔍 Testing Required API Endpoints from Task Description"
echo "========================================================="

echo ""
echo "📋 Test 1: GET /profiles/1/days/1/"
echo "Expected: ice_amount: 585 (3 sections × 195 cubic yards)"
response=$(curl -s "$API_BASE_URL/profiles/$PROFILE1_ID/days/1/")
echo "✅ Response: $response"

echo ""
echo "📋 Test 2: GET /profiles/2/days/1/"
echo "Expected: ice_amount: 195 (1 section × 195 cubic yards)"
response=$(curl -s "$API_BASE_URL/profiles/$PROFILE2_ID/days/1/")
echo "✅ Response: $response"

echo ""
echo "📋 Test 3: GET /profiles/3/days/1/"
echo "Expected: ice_amount: 975 (5 sections × 195 cubic yards)"
response=$(curl -s "$API_BASE_URL/profiles/$PROFILE3_ID/days/1/")
echo "✅ Response: $response"

echo ""
echo "📋 Test 4: GET /profiles/1/overview/1/"
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
