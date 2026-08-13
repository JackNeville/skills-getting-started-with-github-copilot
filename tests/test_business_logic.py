"""Unit tests for business logic and validation."""

import pytest


class TestActivityValidation:
    """Tests for activity validation logic."""

    def test_activity_exists_in_data(self, client):
        """Test that activities are initialized correctly."""
        response = client.get("/activities")
        activities = response.json()
        
        required_activities = [
            "Chess Club",
            "Programming Class",
            "Gym Class",
            "Basketball Team",
            "Track and Field",
            "Art Club",
            "Drama Club",
            "Science Club",
            "Debate Team"
        ]
        
        for activity in required_activities:
            assert activity in activities

    def test_activity_data_structure_valid(self, client):
        """Test that each activity has valid structure."""
        response = client.get("/activities")
        activities = response.json()
        
        for name, data in activities.items():
            # Check required fields
            assert "description" in data, f"{name} missing description"
            assert "schedule" in data, f"{name} missing schedule"
            assert "max_participants" in data, f"{name} missing max_participants"
            assert "participants" in data, f"{name} missing participants"
            
            # Check types
            assert isinstance(data["description"], str)
            assert isinstance(data["schedule"], str)
            assert isinstance(data["max_participants"], int)
            assert isinstance(data["participants"], list)
            
            # Check valid values
            assert len(data["description"]) > 0
            assert len(data["schedule"]) > 0
            assert data["max_participants"] > 0


class TestDuplicateDetection:
    """Tests for duplicate signup prevention."""

    def test_duplicate_detection_same_email(self, client):
        """Test that signup fails for already registered email."""
        email = "existing@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response2.status_code == 400

    def test_duplicate_check_case_sensitive(self, client):
        """Test whether duplicate check is case-sensitive."""
        email = "student@mergington.edu"
        
        # Sign up with lowercase
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Try signup with uppercase (may or may not be case-sensitive)
        response2 = client.post(f"/activities/Chess Club/signup?email={email.upper()}")
        
        # Document behavior - currently case-sensitive in Python
        # In production, might want case-insensitive comparison
        response_obj = client.get("/activities")
        activities = response_obj.json()
        
        if response2.status_code == 400:
            # Case-insensitive validation
            assert email.upper() not in activities["Chess Club"]["participants"]
        else:
            # Case-sensitive validation (current behavior)
            assert email.upper() in activities["Chess Club"]["participants"]

    def test_duplicate_across_activities_allowed(self, client):
        """Test that same email can register for multiple activities."""
        email = "multiactivity@mergington.edu"
        
        response1 = client.post(f"/activities/Chess Club/signup?email={email}")
        assert response1.status_code == 200
        
        response2 = client.post(f"/activities/Programming Class/signup?email={email}")
        assert response2.status_code == 200
        
        # Verify in both
        response = client.get("/activities")
        activities = response.json()
        
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]


class TestParticipantListOperations:
    """Tests for participant list operations."""

    def test_initial_participants_preserved(self, client):
        """Test that initial participants are in the list."""
        response = client.get("/activities")
        activities = response.json()
        
        # Chess Club starts with 2 participants
        assert len(activities["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in activities["Chess Club"]["participants"]

    def test_add_participant_increases_count(self, client):
        """Test that adding participant increases count."""
        response1 = client.get("/activities")
        initial_count = len(response1.json()["Chess Club"]["participants"])
        
        client.post("/activities/Chess Club/signup?email=newperson@mergington.edu")
        
        response2 = client.get("/activities")
        new_count = len(response2.json()["Chess Club"]["participants"])
        
        assert new_count == initial_count + 1

    def test_remove_participant_decreases_count(self, client):
        """Test that removing participant decreases count."""
        response1 = client.get("/activities")
        initial_count = len(response1.json()["Chess Club"]["participants"])
        
        client.delete("/activities/Chess Club/unregister?email=michael@mergington.edu")
        
        response2 = client.get("/activities")
        new_count = len(response2.json()["Chess Club"]["participants"])
        
        assert new_count == initial_count - 1

    def test_participant_list_order_preserved_on_removal(self, client):
        """Test that removing a participant doesn't corrupt the list."""
        # First get the list
        response1 = client.get("/activities")
        initial_participants = response1.json()["Track and Field"]["participants"].copy()
        
        # Remove the first one
        client.delete(f"/activities/Track and Field/unregister?email={initial_participants[0]}")
        
        # Check remaining participants are intact
        response2 = client.get("/activities")
        remaining = response2.json()["Track and Field"]["participants"]
        
        for participant in initial_participants[1:]:
            assert participant in remaining


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_activity_name_case_sensitivity(self, client):
        """Test that activity names are case-sensitive."""
        # Try different case
        response = client.post("/activities/chess club/signup?email=test@mergington.edu")
        assert response.status_code == 404

    def test_special_characters_in_email(self, client):
        """Test handling of special characters in email."""
        email = "user+tag@mergington.edu"
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Should succeed or fail based on email validation
        assert response.status_code in [200, 422, 400]

    def test_very_long_email(self, client):
        """Test handling of very long email."""
        email = "a" * 100 + "@mergington.edu"
        response = client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]

    def test_missing_email_parameter(self, client):
        """Test signup without email parameter."""
        response = client.post("/activities/Chess Club/signup")
        
        # Should fail (missing required parameter)
        assert response.status_code in [422, 400]

    def test_missing_activity_parameter(self, client):
        """Test with missing activity parameter."""
        response = client.post("/activities//signup?email=test@mergington.edu")
        
        # Should fail
        assert response.status_code == 404


class TestDataConsistency:
    """Tests for data consistency across requests."""

    def test_participant_list_consistent_across_requests(self, client):
        """Test that participant list doesn't change unexpectedly."""
        # Get initial state
        r1 = client.get("/activities")
        initial = r1.json()
        
        # Make multiple requests without changes
        r2 = client.get("/activities")
        r3 = client.get("/activities")
        
        unchanged1 = r2.json()
        unchanged2 = r3.json()
        
        assert initial == unchanged1 == unchanged2

    def test_activity_max_participants_constant(self, client):
        """Test that max_participants doesn't change."""
        # Get initial max
        r1 = client.get("/activities")
        initial_max = r1.json()["Chess Club"]["max_participants"]
        
        # Add participant
        client.post("/activities/Chess Club/signup?email=test@mergington.edu")
        
        # Check max is unchanged
        r2 = client.get("/activities")
        new_max = r2.json()["Chess Club"]["max_participants"]
        
        assert initial_max == new_max
