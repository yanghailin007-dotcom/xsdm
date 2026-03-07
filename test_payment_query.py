"""
测试订单查询功能（主动查询易支付平台）
"""
import requests
import sys

sys.path.insert(0, '.')

BASE_URL = 'http://127.0.0.1:5000'

print("="*60)
print("测试订单查询功能（主动查询易支付平台）")
print("="*60)

session = requests.Session()

# 1. 登录
print("\n【1】登录...")
resp = session.post(f'{BASE_URL}/login', 
    json={'username': 'test', 'password': 'test123'},
    timeout=10)
print(f"登录: {resp.status_code}")

# 2. 创建订单
print("\n【2】创建订单...")
resp = session.post(f'{BASE_URL}/api/payment/create_order',
    json={'amount': 0.01},
    timeout=10)
result = resp.json()

if not result.get('success'):
    print(f"❌ 创建订单失败: {result}")
    sys.exit(1)

order_id = result['data']['order_id']
print(f"✅ 订单创建成功: {order_id}")

# 3. 查询订单（未支付状态）
print("\n【3】查询订单状态（未支付）...")
resp = session.get(f'{BASE_URL}/api/payment/query?order_id={order_id}', timeout=10)
result = resp.json()
print(f"查询结果: {result}")

if result.get('success'):
    print(f"订单状态: {result['data']['status']}")
    print("这是正常的，因为还没有支付")
else:
    print(f"查询失败: {result}")

print("\n" + "="*60)
print("测试说明")
print("="*60)
print(f"""
订单已创建: {order_id}

现在你可以：
1. 在浏览器中访问 http://127.0.0.1:5000/recharge
2. 点击充值选项弹出支付二维码
3. 用支付宝扫码支付 0.01 元
4. 支付完成后，点击"已完成支付"按钮
5. 系统会查询易支付平台，如果已支付会显示成功

或者运行 test_payment_notify.py 手动模拟回调。
""")
