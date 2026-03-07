"""
模拟支付回调测试
用于测试支付回调功能是否正常工作
"""
import requests
import hashlib
import sys
import time

sys.path.insert(0, '.')
from web.api.payment_api import generate_sign

# 配置
PID = '2025082311011032'
KEY = 'H9TEykkzChooxOXMeKX8KRn9e1hnjmPu'
BASE_URL = 'http://127.0.0.1:5000'

print("="*60)
print("支付回调模拟测试")
print("="*60)

# 1. 先创建一个订单
print("\n【步骤1】创建测试订单...")
session = requests.Session()

# 登录
resp = session.post(f'{BASE_URL}/login', 
    json={'username': 'test', 'password': 'test123'},
    timeout=10)
print(f"登录: {resp.status_code}")

# 创建订单
resp = session.post(f'{BASE_URL}/api/payment/create_order',
    json={'amount': 0.01},
    timeout=10)
result = resp.json()

if not result.get('success'):
    print(f"❌ 创建订单失败: {result}")
    sys.exit(1)

order_id = result['data']['order_id']
print(f"✅ 订单创建成功: {order_id}")
print(f"   回调地址: {BASE_URL}/api/payment/notify")

# 2. 模拟回调
print("\n【步骤2】模拟支付回调...")

# 构造回调参数
callback_params = {
    'pid': PID,
    'name': '充值0.01点',
    'money': '0.01',
    'out_trade_no': order_id,
    'trade_no': f'ZPAY{int(time.time())}',
    'param': '22',
    'trade_status': 'TRADE_SUCCESS',
    'type': 'alipay'
}

# 生成签名
sign = generate_sign(callback_params, KEY)
callback_params['sign'] = sign
callback_params['sign_type'] = 'MD5'

print(f"回调参数: {callback_params}")

# 发送回调
resp = requests.post(f'{BASE_URL}/api/payment/notify', 
    data=callback_params,
    timeout=10)

print(f"\n回调响应状态码: {resp.status_code}")
print(f"回调响应内容: {resp.text}")

if resp.text == 'success':
    print("\n✅ 回调处理成功！")
else:
    print(f"\n❌ 回调处理失败")

# 3. 查询订单状态
print("\n【步骤3】查询订单状态...")
resp = session.get(f'{BASE_URL}/api/payment/query?order_id={order_id}', timeout=10)
result = resp.json()

if result.get('success'):
    print(f"订单状态: {result['data']['status']}")
    if result['data']['status'] == 'completed':
        print("✅ 订单已支付完成！")
    else:
        print("⚠️ 订单尚未支付")
else:
    print(f"查询失败: {result}")

# 4. 检查余额
print("\n【步骤4】检查余额...")
resp = session.get(f'{BASE_URL}/api/points/balance', timeout=10)
result = resp.json()

if result.get('success'):
    print(f"当前余额: {result['data']['balance']}点")
else:
    print(f"查询余额失败: {result}")

print("\n" + "="*60)
print("测试完成")
print("="*60)
print("\n说明:")
print("1. 如果回调返回 'success'，说明回调处理逻辑正常")
print("2. 如果订单状态为 'completed'，说明订单更新成功")
print("3. 如果余额增加了0.01，说明点数发放成功")
print("\n注意：实际支付时，易支付会向你的服务器发送回调请求。")
print("      但由于 localhost 是内网地址，易支付无法访问。")
print("      生产环境需要使用外网可访问的地址！")
