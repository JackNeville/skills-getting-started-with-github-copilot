"""Tests for state management and persistence."""

import pytest


class TestStatePersistence:
    """Tests for state persistence across requests."""

    def test_signup_persists_across_requests(self, client):
        """Test that signup persists when checking activity list."""
        # Add a participant
        response1 = client.post("/activities/Chess Club/signup?email=persist@mergington.edu")
        assert response1.status_code == 200
        
        # Immediately fetch the same activity
        response2 = client.get("/activities")
        activities = response2.json()
        
        # Verify the participant is still there
        assert "persist@mergington.edu" in activities["Chess Club"]["participants"]

    def test_unregister_persists_across_requests(self, client):
        """Test that unregister persists when checking activity list."""
        # Remove a participant
        response1 = client.delete("/activities/Chess Club/unregister?email=michael@mergington.edu")
        assert response1.status_code == 200
        
        # Immediately fetch the activity
        response2 = client.get("/activities")
        activities = response2.json()
        
        # Verify the participant is gone
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]

    def test_multiple_operations_persist(self, client):
        """Test that multiple operations persist cumulatively."""
        # Add first participant
        client.post("/activities/Chess Club/signup?email=alice@mergington.edu")
        
        # Add second participant
        client.post("/activities/Chess Club/signup?email=bob@mergington.edu")
        
        # Remove first participant
        client.delete("/activities/Chess Club/unregister?email=michael@mergington.edu")
        
        # Fetch and verify state
        response = client.get("/activities")
        participants = response.json()["Chess Club"]["participants"]
        
        assert "alice@mergington.edu" in participants
        assert "bob@mergington.edu" in participants
        assert "michael@mergington.edu" not in participants
        assert "daniel@mergington.edu" in participants  # Original participant

    def test_separate_activities_independent(self, client):
        """Test that changes to one activity don't affect others."""
        # Add to Chess Club
        client.post("/activities/Chess Club/signup?email=test1@mergington.edu")
        
        # Remove from Programming Class
        client.delete("/activities/Programming Class/unregister?email=emma@mergington.edu")
        
        # Verify changes are isolated
        response = client.get("/activities")
        activities = response.json()
        
        assert "test1@mergington.edu" in activities["Chess Club"]["participants"]
        assert "emma@mergington.edu" not in activities["Programming Class"]["participants"]
        
        # Other activities should be unaffected
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
        assert "sophia@mergington.edu" in activities["Programming Class"]["participants"]


class TestStateIsolation:
    """Tests for state isolation between test cases."""

    def test_first_test_clean_state(self, client):
        """Test that first test gets clean initial state."""
        response = client.get("/activities")
        activities = response.json()
        
        # Verify initial state is correct
        assert len(activities["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]

    def test_second_test_independent_state(self, client):
        """Test that second test also gets clean initial state."""
        response = client.get("/activities")
        activities = response.json()
        
        # Should have same initial state as first test
        assert len(activities["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]

    def test_modified_state_resets_between_tests(self, client):
        """Test that state resets between test functions."""
        # Modify state
        client.post("/activities/Chess Club/signup?email=modified@mergington.edu")
        client.delete("/activities/Programming Class/unregister?email=emma@mergington.edu")
        
        # This test modifies state, but next test should see clean state
        response = client.get("/activities")
        activities = response.json()
        
        # In this test, modifications are visible
        assert "modified@mergington.edu" in activities["Chess Club"]["participants"]
        assert "emma@mergington.edu" not in activities["Programming Class"]["participants"]

    def test_state_after_previous_modifications(self, client):
        """Test that state is clean even after previous test modified it."""
        # This test runs after test_modified_state_resets_between_tests
        # but should still see clean initial state due to reset_activities fixture
        response = client.get("/activities")
        activities = response.json()
        
        # Should be back to initial state
        assert len(activities["Chess Club"]["participants"]) == 2
        assert "modified@mergington.edu" not in activities["Chess Club"]["participants"]
        assert "emma@mergington.edu" in activities["Programming Class"]["participants"]


class TestComplexStateScenarios:
    """Tests for complex state management scenarios."""

    def test_long_operation_sequence(self, client):
        """Test a long sequence of operations maintains state correctly."""
        # Add 5 students to one activity
        for i in range(5):
            r = client.post(f"/activities/Basketball Team/signup?email=student{i}@mergington.edu")
            assert r.status_code == 200
        
        # Remove 2 of them
        client.delete("/activities/Basketball Team/unregister?email=student1@mergington.edu")
        client.delete("/activities/Basketball Team/unregister?email=student3@mergington.edu")
        
        # Add 3 to a different activity
        for i in range(3):
            r = client.post(f"/activities/Art Club/signup?email=artist{i}@mergington.edu")
            assert r.status_code == 200
        
        # Verify final state
        response = client.get("/activities")
        activities = response.json()
        
        basketball = activities["Basketball Team"]["participants"]
        art = activities["Art Club"]["participants"]
        
        # Basketball Team should have: original (1) + 5 new - 2 removed = 4 + alex
        assert "student0@mergington.edu" in basketball
        assert "student1@mergington.edu" not in basketball
        assert "student2@mergington.edu" in basketball
        assert "student3@mergington.edu" not in basketball
        assert "student4@mergington.edu" in basketball
        assert "alex@mergington.edu" in basketball  # Original
        
        # Art Club should have original + 3 new
        assert "isabella@mergington.edu" in art  # Original
        assert "artist0@mergington.edu" in art
        assert "artist1@mergington.edu" in art
        assert "artist2@mergington.edu" in art

    def test_interleaved_operations_maintain_consistency(self, client):
        """Test that interleaved operations across activities maintain consistency."""
        operations = [
            ("POST", "Chess Club", "person1@mergington.edu"),
            ("POST", "Programming Class", "person2@mergington.edu"),
            ("POST", "Chess Club", "person3@mergington.edu"),
            ("DELETE", "Programming Class", "emma@mergington.edu"),
            ("POST", "Programming Class", "person4@mergington.edu"),
            ("DELETE", "Chess Club", "michael@mergington.edu"),
        ]
        
        for method, activity, email in operations:
            if method == "POST":
                r = client.post(f"/activities/{activity}/signup?email={email}")
                assert r.status_code == 200
            else:
                r = client.delete(f"/activities/{activity}/unregister?email={email}")
                assert r.status_code == 200
        
        # Verify final state
        response = client.get("/activities")
        activities = response.json()
        
        chess = activities["Chess Club"]["participants"]
        prog = activities["Programming Class"]["participants"]
        
        # Chess Club: started with michael, daniel; added person1, person3; removed michael
        assert "michael@mergington.edu" not in chess
        assert "daniel@mergington.edu" in chess
        assert "person1@mergington.edu" in chess
        assert "person3@mergington.edu" in chess
        
        # Programming: started with emma, sophia; removed emma; added person2, person4
        assert "emma@mergington.edu" not in prog
        assert "sophia@mergington.edu" in prog
        assert "person2@mergington.edu" in prog
        assert "person4@mergington.edu" in prog

    def test_total_participant_count_consistency(self, client):
        """Test that total participant count across all activities remains consistent."""
        # Get initial total
        r1 = client.get("/activities")
        activities1 = r1.json()
        initial_total = sum(len(a["participants"]) for a in activities1.values())
        
        # Perform various operations
        client.post("/activities/Chess Club/signup?email=test1@mergington.edu")
        client.delete("/activities/Programming Class/unregister?email=emma@mergington.edu")
        client.post("/activities/Art Club/signup?email=test2@mergington.edu")
        client.delete("/activities/Gym Class/unregister?email=john@mergington.edu")
        
        # Get final total
        r2 = client.get("/activities")
        activities2 = r2.json()
        final_total = sum(len(a["participants"]) for a in activities2.values())
        
        # Should be equal: 1 add - 1 remove + 1 add - 1 remove = 0 net change
        assert initial_total == final_total
