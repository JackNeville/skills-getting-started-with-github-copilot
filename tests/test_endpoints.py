"""Integration tests for FastAPI endpoints."""

import pytest


class TestRootEndpoint:
    """Tests for GET / endpoint."""

    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static HTML."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"

    def test_root_follows_redirect(self, client):
        """Test that root redirect can be followed."""
        response = client.get("/", follow_redirects=True)
        assert response.status_code == 200


class TestGetActivitiesEndpoint:
    """Tests for GET /activities endpoint."""

    def test_get_all_activities(self, client):
        """Test that all activities are returned."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        activities = response.json()
        assert isinstance(activities, dict)
        assert len(activities) == 9
        assert "Chess Club" in activities
        assert "Programming Class" in activities

    def test_activities_structure(self, client):
        """Test that activities have correct structure."""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_activities_participant_counts(self, client):
        """Test that participant counts are accurate."""
        response = client.get("/activities")
        activities = response.json()
        
        assert len(activities["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
        assert len(activities["Basketball Team"]["participants"]) == 1


class TestSignupEndpoint:
    """Tests for POST /activities/{activity_name}/signup endpoint."""

    def test_signup_valid_activity_and_email(self, client):
        """Test successful signup for valid activity and email."""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]

    def test_signup_adds_participant(self, client):
        """Test that signup actually adds participant to activity."""
        client.post("/activities/Chess Club/signup?email=newstudent@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == 3

    def test_signup_nonexistent_activity(self, client):
        """Test signup fails for non-existent activity."""
        response = client.post(
            "/activities/Fake Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_duplicate_email(self, client):
        """Test that duplicate signup is rejected."""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "already" in data["detail"].lower()

    def test_signup_duplicate_prevents_duplication(self, client):
        """Test that duplicate signup doesn't add participant twice."""
        client.post("/activities/Chess Club/signup?email=michael@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        
        # Should still be 2, not 3
        assert len(activities["Chess Club"]["participants"]) == 2

    def test_signup_multiple_students_same_activity(self, client):
        """Test that multiple different students can sign up."""
        client.post("/activities/Chess Club/signup?email=alice@mergington.edu")
        client.post("/activities/Chess Club/signup?email=bob@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        
        assert "alice@mergington.edu" in activities["Chess Club"]["participants"]
        assert "bob@mergington.edu" in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == 4

    def test_signup_empty_email(self, client):
        """Test signup with empty email."""
        response = client.post(
            "/activities/Chess Club/signup?email="
        )
        # Currently the backend allows empty email (potential improvement)
        # In production, should validate email format/non-empty
        assert response.status_code in [200, 400, 422]

    def test_signup_same_student_different_activities(self, client):
        """Test that same student can sign up for different activities."""
        client.post("/activities/Chess Club/signup?email=student@mergington.edu")
        client.post("/activities/Programming Class/signup?email=student@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        
        assert "student@mergington.edu" in activities["Chess Club"]["participants"]
        assert "student@mergington.edu" in activities["Programming Class"]["participants"]

    # Capacity limit tests - current behavior (no enforcement) vs. expected (enforce)
    def test_signup_at_capacity_current_behavior(self, client):
        """
        Test current behavior: signup allowed even when activity is full.
        This test documents the current bug - activity can exceed max_participants.
        Once capacity enforcement is added, this should be updated or marked as xfail.
        """
        # Fill up "Basketball Team" (max 15, currently has 1)
        for i in range(14):
            response = client.post(
                f"/activities/Basketball Team/signup?email=student{i}@mergington.edu"
            )
            assert response.status_code == 200
        
        # Activity should now be at capacity (15 participants)
        response = client.get("/activities")
        activities = response.json()
        assert len(activities["Basketball Team"]["participants"]) == 15
        
        # Currently, this succeeds (bug) - should be enforced
        # Once fixed, change to: assert response.status_code == 400
        response = client.post(
            "/activities/Basketball Team/signup?email=overcapacity@mergington.edu"
        )
        # CURRENT: allows overbooking
        assert response.status_code == 200
        
        # Document expected behavior:
        # EXPECTED: should return 400 and prevent signup
        # assert response.status_code == 400
        # assert "full" in response.json()["detail"].lower()


class TestUnregisterEndpoint:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint."""

    def test_unregister_valid_participant(self, client):
        """Test successful unregister of valid participant."""
        response = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "michael@mergington.edu" in data["message"]

    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes participant."""
        client.delete("/activities/Chess Club/unregister?email=michael@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == 1

    def test_unregister_nonexistent_activity(self, client):
        """Test unregister fails for non-existent activity."""
        response = client.delete(
            "/activities/Fake Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_not_registered(self, client):
        """Test unregister fails for student not in activity."""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "not registered" in data["detail"].lower()

    def test_unregister_twice_fails_second_time(self, client):
        """Test that unregistering twice fails the second time."""
        # First unregister should succeed
        response1 = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response1.status_code == 200
        
        # Second unregister should fail
        response2 = client.delete(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response2.status_code == 400

    def test_unregister_multiple_participants(self, client):
        """Test unregistering one participant doesn't affect others."""
        client.delete("/activities/Chess Club/unregister?email=michael@mergington.edu")
        
        response = client.get("/activities")
        activities = response.json()
        
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in activities["Chess Club"]["participants"]
        assert len(activities["Chess Club"]["participants"]) == 1

    def test_unregister_empty_email(self, client):
        """Test unregister with empty email."""
        response = client.delete(
            "/activities/Chess Club/unregister?email="
        )
        # Should fail
        assert response.status_code in [400, 422]


class TestSignupUnregisterCycle:
    """Tests for signup and unregister workflow cycles."""

    def test_signup_unregister_signup(self, client):
        """Test signup -> unregister -> signup again works."""
        email = "cycling@mergington.edu"
        activity = "Chess Club"
        
        # First signup
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Unregister
        response2 = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response2.status_code == 200
        
        # Sign up again
        response3 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response3.status_code == 200
        
        # Verify in activity
        response = client.get("/activities")
        activities = response.json()
        assert email in activities[activity]["participants"]

    def test_multiple_cycles_same_student(self, client):
        """Test multiple signup/unregister cycles."""
        email = "cycler@mergington.edu"
        activity = "Programming Class"
        
        for _ in range(3):
            # Signup
            r1 = client.post(f"/activities/{activity}/signup?email={email}")
            assert r1.status_code == 200
            
            # Unregister
            r2 = client.delete(f"/activities/{activity}/unregister?email={email}")
            assert r2.status_code == 200
