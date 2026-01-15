"""
Verify Video Delete Fix
Tests that the delete functionality works correctly after the fix
"""
import requests
import json


def print_section(title):
    """Print section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main():
    base_url = "http://127.0.0.1:5000/api/veo"
    
    print("\n" + "#" * 60)
    print("# Video Delete Fix Verification")
    print("#" * 60)
    
    # Test 1: Check task consistency
    print_section("Test 1: Check Task Consistency")
    
    try:
        response = requests.get(f"{base_url}/tasks?limit=100")
        if response.status_code == 200:
            data = response.json()
            tasks = data.get('data', [])
            print(f"\nTotal tasks in memory: {len(tasks)}")
            
            # Check disk
            import os
            storage_dir = "veo_video_generations"
            if os.path.exists(storage_dir):
                json_files = [f for f in os.listdir(storage_dir) if f.endswith('.json')]
                print(f"Total files on disk: {len(json_files)}")
                
                if len(tasks) == len(json_files):
                    print("[PASS] Memory and disk are consistent")
                else:
                    print(f"[FAIL] Inconsistency: memory={len(tasks)}, disk={len(json_files)}")
            else:
                print(f"[ERROR] Storage directory not found: {storage_dir}")
        else:
            print(f"[FAIL] Failed to list tasks: HTTP {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {str(e)}")
    
    # Test 2: Try deleting first completed task
    print_section("Test 2: Delete First Completed Task")
    
    try:
        response = requests.get(f"{base_url}/tasks?limit=100")
        if response.status_code == 200:
            data = response.json()
            tasks = data.get('data', [])
            
            # Find first completed task
            completed_tasks = [t for t in tasks if t.get('status') == 'completed']
            
            if completed_tasks:
                test_task = completed_tasks[0]
                task_id = test_task.get('id')
                
                print(f"\nDeleting task: {task_id}")
                print(f"Status: {test_task.get('status')}")
                
                # Delete
                delete_response = requests.delete(f"{base_url}/tasks/{task_id}")
                print(f"Delete response: HTTP {delete_response.status_code}")
                
                if delete_response.status_code == 200:
                    print("[PASS] Task deleted successfully")
                    
                    # Verify it's gone
                    verify_response = requests.get(f"{base_url}/tasks?limit=100")
                    verify_data = verify_response.json()
                    remaining_tasks = verify_data.get('data', [])
                    remaining_ids = [t.get('id') for t in remaining_tasks]
                    
                    if task_id not in remaining_ids:
                        print("[PASS] Task removed from list")
                    else:
                        print("[FAIL] Task still in list")
                else:
                    error_data = delete_response.json()
                    error_msg = error_data.get('error', {}).get('message', 'unknown')
                    print(f"[FAIL] Delete failed: {error_msg}")
            else:
                print("[SKIP] No completed tasks to test")
    except Exception as e:
        print(f"[ERROR] {str(e)}")
    
    # Test 3: Try deleting non-existent task
    print_section("Test 3: Delete Non-existent Task")
    
    try:
        fake_id = "veo_faketask123"
        print(f"\nDeleting non-existent task: {fake_id}")
        
        delete_response = requests.delete(f"{base_url}/tasks/{fake_id}")
        print(f"Delete response: HTTP {delete_response.status_code}")
        
        if delete_response.status_code == 400:
            print("[PASS] Correctly returned 400 for non-existent task")
        else:
            print(f"[FAIL] Expected 400, got {delete_response.status_code}")
    except Exception as e:
        print(f"[ERROR] {str(e)}")
    
    # Summary
    print_section("Summary")
    print("\nExpected behavior after fix:")
    print("1. Memory and disk should be consistent")
    print("2. Deleting existing tasks should succeed")
    print("3. Deleting non-existent tasks should return 400")
    print("4. Frontend should show correct error messages")
    print("\nNext steps:")
    print("- Refresh browser page")
    print("- Try deleting from UI")
    print("- Check browser console for errors")


if __name__ == '__main__':
    main()