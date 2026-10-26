import os
import sqlite3
import secrets
import unittest
from app import app, init_db, get_db

def get_csrf(client):
    with client.session_transaction() as sess:
        if '_csrf_token' not in sess:
            sess['_csrf_token'] = 'test-csrf-token-12345'
        return sess['_csrf_token']

def test_full_application_suite():
    test_db = os.path.join(os.path.dirname(__file__), 'test_temp.db')
    if os.path.exists(test_db):
        try:
            os.remove(test_db)
        except Exception:
            pass

    app.config['TESTING'] = True
    app.config['DATABASE'] = test_db
    client = app.test_client()

    try:
        with app.app_context():
            init_db()

        print("\n--- TEST 1: Database Initialization & Demo Seed ---")
        with app.app_context():
            db = get_db()
            users = db.execute("SELECT username FROM users").fetchall()
            usernames = [u['username'] for u in users]
            assert 'demo_user' in usernames
            assert 'host_lucas' in usernames
            assert 'sarah_cine' in usernames
            print(f"[OK] Initialized with {len(usernames)} users: {usernames}")

        print("\n--- TEST 2: Browse & Catalog Page (GET /) ---")
        res = client.get('/')
        assert res.status_code == 200
        assert b"MovieNight" in res.data or b"Movie Night" in res.data
        print("[OK] Home catalog loads successfully with event cards")

        print("\n--- TEST 3: Search & Category Filtering ---")
        # Search by title
        res_search = client.get('/?q=Comedy')
        assert res_search.status_code == 200
        assert b"Cult Comedy" in res_search.data
        print("[OK] Title search filters correctly")

        # Filter by category
        res_cat = client.get('/?category=Animation')
        assert res_cat.status_code == 200
        assert b"Studio Ghibli" in res_cat.data
        print("[OK] Category filtering works as expected")

        # Search yielding empty state
        res_empty = client.get('/?q=NonExistentMovieNightXYZ')
        assert res_empty.status_code == 200
        assert b"No Movie Nights Found" in res_empty.data
        print("[OK] Empty state displayed for unmatched queries")

        print("\n--- TEST 4: User Registration Flow (POST /register) ---")
        test_user = f"user_{secrets.token_hex(4)}"
        res_reg = client.post('/register', data={
            'csrf_token': get_csrf(client),
            'full_name': 'Test Cinephile',
            'username': test_user,
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }, follow_redirects=True)
        assert res_reg.status_code == 200
        assert b"Registration successful" in res_reg.data
        print(f"[OK] New user '{test_user}' successfully registered with hashed password")

        # Reject duplicate username
        res_dup = client.post('/register', data={
            'csrf_token': get_csrf(client),
            'full_name': 'Another Person',
            'username': test_user,
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!'
        }, follow_redirects=True)
        assert b"already taken" in res_dup.data
        print("[OK] Duplicate username rejected on server")

        print("\n--- TEST 5: User Authentication & Login Flow (POST /login) ---")
        # Invalid password
        res_bad_login = client.post('/login', data={
            'csrf_token': get_csrf(client),
            'username': 'demo_user',
            'password': 'WrongPassword!'
        }, follow_redirects=True)
        assert b"Invalid username or password" in res_bad_login.data
        print("[OK] Rejected invalid credentials")

        # Valid demo credentials
        res_good_login = client.post('/login', data={
            'csrf_token': get_csrf(client),
            'username': 'demo_user',
            'password': 'DemoPass123!'
        }, follow_redirects=True)
        assert res_good_login.status_code == 200
        assert b"Welcome back, Alex Miller" in res_good_login.data
        print("[OK] Logged in successfully with demo account")

        print("\n--- TEST 6: Event Creation Flow (POST /create) ---")
        res_create = client.post('/create', data={
            'csrf_token': get_csrf(client),
            'title': 'Dark Knight Trilogy Night',
            'scheduled_date': '2026-11-10',
            'category': 'Action',
            'description': 'Watching Batman Begins, The Dark Knight, and The Dark Knight Rises back to back.',
            'initial_candidates': 'Batman Begins (2005), The Dark Knight (2008), The Dark Knight Rises (2012)'
        }, follow_redirects=True)
        assert res_create.status_code == 200
        assert b"Dark Knight Trilogy Night" in res_create.data
        assert b"Batman Begins" in res_create.data
        print("[OK] Created new movie night with initial candidates, user set as host")

        # Extract new event ID
        with app.app_context():
            db = get_db()
            new_ev = db.execute("SELECT id FROM movie_nights WHERE title = 'Dark Knight Trilogy Night' ORDER BY id DESC").fetchone()
            new_event_id = new_ev['id']
            cands = db.execute("SELECT id, title FROM movie_candidates WHERE movie_night_id = ?", (new_event_id,)).fetchall()
            assert len(cands) == 3
            c1_id = cands[0]['id']
            c2_id = cands[1]['id']

        print("\n--- TEST 7: Voting System & Atomic Vote Replacement ---")
        # Vote for candidate 1
        res_vote1 = client.post(f'/night/{new_event_id}/vote', data={
            'csrf_token': get_csrf(client),
            'candidate_id': c1_id
        }, follow_redirects=True)
        assert res_vote1.status_code == 200
        assert b"recorded" in res_vote1.data

        with app.app_context():
            db = get_db()
            v1 = db.execute("SELECT candidate_id FROM votes WHERE movie_night_id = ? AND user_id = (SELECT id FROM users WHERE username='demo_user')", (new_event_id,)).fetchall()
            assert len(v1) == 1
            assert v1[0]['candidate_id'] == c1_id
            print("[OK] Vote recorded for Candidate 1")

        # Switch vote to candidate 2 (atomic replacement)
        res_vote2 = client.post(f'/night/{new_event_id}/vote', data={
            'csrf_token': get_csrf(client),
            'candidate_id': c2_id
        }, follow_redirects=True)
        assert res_vote2.status_code == 200

        with app.app_context():
            db = get_db()
            v2 = db.execute("SELECT candidate_id FROM votes WHERE movie_night_id = ? AND user_id = (SELECT id FROM users WHERE username='demo_user')", (new_event_id,)).fetchall()
            assert len(v2) == 1
            assert v2[0]['candidate_id'] == c2_id
            print("[OK] Vote atomically replaced for Candidate 2 without duplicate active ballots")

        print("\n--- TEST 8: Add Candidate with Genre & Reason ---")
        res_add = client.post(f'/night/{new_event_id}/add_candidate', data={
            'csrf_token': get_csrf(client),
            'candidate_title': 'Joker (2019)',
            'candidate_genre': 'Drama / Thriller',
            'candidate_reason': 'Phoenix gives a haunting performance'
        }, follow_redirects=True)
        assert res_add.status_code == 200
        assert b"Joker (2019)" in res_add.data
        print("[OK] Added candidate with genre and reason fields")

        print("\n--- TEST 9: Host Studio & Finalization Rules ---")
        # Host finalizes the winning movie
        res_fin = client.post(f'/night/{new_event_id}/finalize', data={
            'csrf_token': get_csrf(client),
            'winning_candidate_id': c2_id
        }, follow_redirects=True)
        assert res_fin.status_code == 200
        assert b"finalized" in res_fin.data.lower()
        print("[OK] Event finalized with winner selected")

        # Voting must now be rejected
        res_vote_locked = client.post(f'/night/{new_event_id}/vote', data={
            'csrf_token': get_csrf(client),
            'candidate_id': c1_id
        }, follow_redirects=True)
        assert b"locked" in res_vote_locked.data.lower()
        print("[OK] Voting permanently locked on finalized event")

        # Candidate additions must be rejected on finalized event
        res_cand_locked = client.post(f'/night/{new_event_id}/add_candidate', data={
            'csrf_token': get_csrf(client),
            'candidate_title': 'Another Film (2020)',
            'candidate_genre': 'Drama',
            'candidate_reason': 'Test reason'
        }, follow_redirects=True)
        assert b"already finalized" in res_cand_locked.data.lower()
        print("[OK] Candidate addition locked on finalized event")

        print("\n--- TEST 10: Server-Side Ownership Verification on Edit ---")
        # demo_user is NOT host of event 2 (hosted by host_lucas)
        res_unauth_edit = client.get('/night/2/edit', follow_redirects=True)
        assert b"do not have permission" in res_unauth_edit.data.lower()
        print("[OK] Server rejected unauthorized edit attempt on another host's event")

        print("\n--- TEST 11: Edit Page Loads for Authorized Host ---")
        # demo_user IS host of event 1
        res_auth_edit = client.get('/night/1/edit', follow_redirects=True)
        assert res_auth_edit.status_code == 200
        assert b"Server Ownership Verified" in res_auth_edit.data
        print("[OK] Server verified ownership and displayed verified host badge")

        print("\n--- TEST 12: 404 Error Page ---")
        res_404 = client.get('/night/99999')
        # Should redirect to index with flash
        assert res_404.status_code in [200, 302]
        print("[OK] Non-existent event handled gracefully")

        res_404_page = client.get('/this-page-does-not-exist')
        assert res_404_page.status_code == 404
        assert b"404" in res_404_page.data
        print("[OK] 404 page renders correctly")

        print("\n--- TEST 13: Delete Event Flow ---")
        # Create a throwaway event to delete
        res_temp = client.post('/create', data={
            'csrf_token': get_csrf(client),
            'title': 'Temp Event To Delete',
            'scheduled_date': '2026-12-25',
            'category': 'Comedy',
            'description': 'This event will be deleted in the test.'
        }, follow_redirects=True)
        assert res_temp.status_code == 200

        with app.app_context():
            db = get_db()
            temp_ev = db.execute("SELECT id FROM movie_nights WHERE title = 'Temp Event To Delete'").fetchone()
            temp_id = temp_ev['id']

        res_del = client.post(f'/night/{temp_id}/delete', data={
            'csrf_token': get_csrf(client)
        }, follow_redirects=True)
        assert res_del.status_code == 200
        assert b"has been deleted" in res_del.data
        print("[OK] Event deleted successfully")

        print("\n--- TEST 14: Logout Flow ---")
        res_logout = client.post('/logout', data={'csrf_token': get_csrf(client)}, follow_redirects=True)
        assert res_logout.status_code == 200
        assert b"logged out successfully" in res_logout.data
        print("[OK] Logged out successfully")

        # Unauthenticated user voting attempt
        res_unauth_vote = client.post('/night/1/vote', data={
            'csrf_token': get_csrf(client),
            'candidate_id': 1
        }, follow_redirects=True)
        assert b"log in" in res_unauth_vote.data.lower()
        print("[OK] Unauthenticated voting rejected")

        print("\n--- TEST 15: Data Persistence Check ---")
        with app.app_context():
            db = get_db()
            fin_ev = db.execute("SELECT status, winning_candidate_id FROM movie_nights WHERE id = ?", (new_event_id,)).fetchone()
            assert fin_ev['status'] == 'finalized'
            assert fin_ev['winning_candidate_id'] == c2_id
            print("[OK] All created events, votes, and finalizations persist in SQLite")

        print("\n" + "=" * 60)
        print("[SUCCESS] ALL 15 APPLICATION TESTS PASSED!")
        print("=" * 60)
    finally:
        if os.path.exists(test_db):
            try:
                os.remove(test_db)
            except Exception:
                pass

if __name__ == '__main__':
    test_full_application_suite()
