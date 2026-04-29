from app import app
from flask import render_template, session
import datetime

def test_dashboard_render():
    with app.app_context():
        # Setup mock data
        class MockUser:
            username = "TestUser"
            id = 1
            about = "About me"
        
        user = MockUser()
        
        # Mock activities
        # We need objects that have timestamp and action_type
        class MockActivity:
            def __init__(self, ts, action):
                self.timestamp = ts
                self.action_type = action

        activities = [
            MockActivity(datetime.datetime(2023, 10, 26), 'Post'),
            MockActivity(datetime.datetime(2023, 10, 27), 'Quiz'),
        ]
        
        metrics = {"total_posts": 10, "total_quizzes_taken": 5, "total_quizzes": 20}
        
        chart_data = {
            "labels": [a.timestamp.strftime("%Y-%m-%d") for a in activities],
            "post_counts": [1 if a.action_type=="Post" else 0 for a in activities],
            "quiz_counts": [1 if a.action_type=="Quiz" else 0 for a in activities]
        }
        
        # We need to mock session for base.html checks maybe? 
        # base.html checks 'user_id' in session
        
        try:
            # We need to inject session data roughly or just mock the template context?
            # session is a proxy, strictly speaking we should set it in a request context, 
            # but render_template might access it.
            # However, 'session' in jinja is global.
            
            with app.test_request_context('/dashboard'):
                session['user_id'] = 1
                session['username'] = 'TestUser'
                
                rendered = render_template('dashboard.html', username=user.username, metrics=metrics, activities=activities, chart_data=chart_data)
                print("Render successful!")
                
                # Check for chart JS data
                if 'labels: ["2023-10-26", "2023-10-27"]' in rendered:
                    print("Chart labels found.")
                else:
                    print("Chart labels mismatch or formatting issue.")
                    # print snippet
                    start = rendered.find('labels: [')
                    print(f"Snippet around labels: {rendered[start:start+50]}")

        except Exception as e:
            print(f"Render failed: {e}")
            import traceback
            traceback.print_exc()

        if 'rendered' in locals():
            start_script = rendered.find('const ctx = document.getElementById')
            end_script = rendered.find('</script>', start_script)
            print("-" * 20)
            print("Rendered Script Snippet:")
            print(rendered[start_script:end_script])
            print("-" * 20)

if __name__ == "__main__":
    test_dashboard_render()
