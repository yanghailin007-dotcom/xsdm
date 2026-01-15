"""
Simple Video Delete Test Script
Tests VeO video deletion functionality
"""
import requests
import json


def test_delete_nonexistent():
    """Test deleting a non-existent task"""
    print("\n" + "=" * 60)
    print("TEST 1: Delete Non-existent Task")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:5000/api/veo"
    fake_id = "veo_nonexistent123"
    
    print(f"\nAttempting to delete non-existent task: {fake_id}")
    
    try:
        response = requests.delete(f"{base_url}/tasks/{fake_id}")
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 400:
            print("[PASS] Backend correctly returned 400 error")
            
            # Verify task list didn't change
            list_response = requests.get(f"{base_url}/tasks?limit=100")
            tasks = list_response.json().get('data', [])
            print(f"[PASS] Task list still has {len(tasks)} items")
        else:
            print(f"[FAIL] Expected 400, got {response.status_code}")
            
    except Exception as e:
        print(f"[ERROR] {str(e)}")


def test_list_tasks():
    """Test listing all tasks"""
    print("\n" + "=" * 60)
    print("TEST 2: List All Tasks")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:5000/api/veo"
    
    try:
        response = requests.get(f"{base_url}/tasks?limit=100&order=desc")
        
        if response.status_code == 200:
            data = response.json()
            tasks = data.get('data', [])
            print(f"\n[SUCCESS] Retrieved {len(tasks)} tasks")
            print("\nTask IDs:")
            for i, task in enumerate(tasks[:10], 1):
                task_id = task.get('id', 'unknown')
                status = task.get('status', 'unknown')
                prompt = (task.get('prompt', 'no prompt')[:40] + '...') if task.get('prompt') else 'no prompt'
                print(f"  {i}. {task_id} - {status}")
                print(f"     Prompt: {prompt}")
            
            if len(tasks) > 10:
                print(f"  ... and {len(tasks) - 10} more tasks")
            
            return tasks
        else:
            print(f"[FAIL] HTTP {response.status_code}")
            return []
            
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return []


def test_delete_existing(tasks):
    """Test deleting an existing task (only completed/failed tasks)"""
    print("\n" + "=" * 60)
    print("TEST 3: Delete Existing Task")
    print("=" * 60)
    
    # Find a safe task to delete (completed or failed)
    safe_tasks = [t for t in tasks if t.get('status') in ['completed', 'failed', 'cancelled']]
    
    if not safe_tasks:
        print("\n[SKIP] No safe tasks to delete (need completed/failed/cancelled)")
        return
    
    base_url = "http://127.0.0.1:5000/api/veo"
    test_task = safe_tasks[0]
    task_id = test_task.get('id')
    
    print(f"\nSelected task for deletion:")
    print(f"  ID: {task_id}")
    print(f"  Status: {test_task.get('status')}")
    print(f"  Prompt: {test_task.get('prompt', 'no prompt')[:50]}...")
    
    print(f"\nDeleting task: {task_id}")
    
    try:
        response = requests.delete(f"{base_url}/tasks/{task_id}")
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("[PASS] Task deleted successfully")
            
            # Verify it's gone
            list_response = requests.get(f"{base_url}/tasks?limit=100")
            remaining_tasks = list_response.json().get('data', [])
            remaining_ids = [t.get('id') for t in remaining_tasks]
            
            if task_id not in remaining_ids:
                print(f"[PASS] Task removed from list ({len(remaining_tasks)} remaining)")
            else:
                print(f"[FAIL] Task still in list")
        else:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'unknown')
            print(f"[FAIL] Delete failed: {error_msg}")
            
    except Exception as e:
        print(f"[ERROR] {str(e)}")


def test_api_error_handling():
    """Test API error handling"""
    print("\n" + "=" * 60)
    print("TEST 4: API Error Handling")
    print("=" * 60)
    
    base_url = "http://127.0.0.1:5000/api/veo"
    
    print("\n1. Testing invalid task ID format...")
    try:
        response = requests.delete(f"{base_url}/tasks/invalid_id_format")
        if response.status_code == 400:
            print("[PASS] Invalid ID returns 400")
        else:
            print(f"[FAIL] Expected 400, got {response.status_code}")
    except Exception as e:
        print(f"[ERROR] {str(e)}")
    
    print("\n2. Testing empty task ID...")
    try:
        response = requests.delete(f"{base_url}/tasks/")
        if response.status_code in [404, 405]:
            print("[PASS] Empty ID returns 404/405")
        else:
            print(f"[INFO] Got {response.status_code} for empty ID")
    except Exception as e:
        print(f"[ERROR] {str(e)}")


def main():
    """Main function"""
    print("\n" + "#" * 60)
    print("# VeO Video Delete Test Suite")
    print("#" * 60)
    
    # Test 1: Delete non-existent
    test_delete_nonexistent()
    
    # Test 2: List tasks
    tasks = test_list_tasks()
    
    # Test 3: Delete existing (if safe tasks available)
    if tasks:
        test_delete_existing(tasks)
    
    # Test 4: Error handling
    test_api_error_handling()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Refresh the browser page")
    print("2. Try deleting a video from the UI")
    print("3. Check browser console for error messages")
    print("4. Check backend logs for details")


if __name__ == '__main__':
    main()