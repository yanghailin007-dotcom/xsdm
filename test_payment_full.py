"""
支付系统全流程测试
包含：签名测试、API测试、本地服务器测试
"""
import hashlib
import sys
import time
import requests
import json

sys.path.insert(0, '.')
from web.api.payment_api import generate_sign, verify_sign

# 配置
PID = '2025082311011032'
KEY = 'H9TEykkzChooxOXMeKX8KRn9e1hnjmPu'
API_URL = 'https://zpayz.cn'
BASE_URL = 'http://127.0.0.1:5000'


def print_section(title):
    print('\n' + '='*60)
    print(f'【{title}】')
    print('='*60)


def test_sign():
    """测试签名算法"""
    print_section('签名算法验证')
    
    params = {
        'pid': PID,
        'type': 'alipay',
        'out_trade_no': 'TEST2025082311011032',
        'notify_url': 'http://localhost/api/payment/notify',
        'return_url': 'http://localhost/payment/success',
        'name': '充值100点',
        'money': '100.00',
        'param': '123'
    }
    
    sign = generate_sign(params, KEY)
    params['sign'] = sign
    params['sign_type'] = 'MD5'
    
    # 手动验证
    sorted_params = sorted([(k, v) for k, v in params.items() if k not in ['sign', 'sign_type']])
    sign_str = '&'.join([f'{k}={v}' for k, v in sorted_params])
    manual_sign = hashlib.md5(f'{sign_str}{KEY}'.encode('utf-8')).hexdigest().lower()
    
    is_valid = sign == manual_sign and verify_sign(params, KEY)
    
    print(f'签名生成: {sign}')
    print(f'手动验证: {manual_sign}')
    print(f'签名验证: {"✅ 通过" if is_valid else "❌ 失败"}')
    
    return is_valid


def test_yipay_api():
    """测试易支付API接口"""
    print_section('易支付API接口测试')
    
    out_trade_no = f'TEST{int(time.time())}'
    params = {
        'pid': PID,
        'type': 'alipay',
        'out_trade_no': out_trade_no,
        'notify_url': f'{BASE_URL}/api/payment/notify',
        'return_url': f'{BASE_URL}/payment/success',
        'name': '测试充值',
        'money': '0.01',
        'clientip': '127.0.0.1',
        'param': 'test'
    }
    
    params['sign'] = generate_sign(params, KEY)
    params['sign_type'] = 'MD5'
    
    try:
        resp = requests.post(f'{API_URL}/mapi.php', data=params, timeout=30)
        result = resp.json()
        
        if result.get('code') == 1:
            print(f'✅ API接口调用成功')
            print(f'  支付URL: {result.get("payurl")}')
            print(f'  二维码: {result.get("img")}')
            return True
        else:
            print(f'❌ API调用失败: {result.get("msg")}')
            return False
    except Exception as e:
        print(f'❌ 请求失败: {e}')
        return False


def test_local_server():
    """测试本地服务器支付流程"""
    print_section('本地服务器支付流程测试')
    
    session = requests.Session()
    
    # 1. 登录
    print('\n1. 用户登录...')
    try:
        resp = session.post(f'{BASE_URL}/api/login', 
                          json={'username': 'test', 'password': 'test123'},
                          timeout=10)
        if resp.status_code == 200:
            print('   ✅ 登录成功')
        else:
            print(f'   ⚠️ 登录失败，尝试注册...')
            # 尝试注册
            reg_resp = session.post(f'{BASE_URL}/api/register',
                                   json={'username': 'test', 'password': 'test123'},
                                   timeout=10)
            if reg_resp.status_code == 200:
                print('   ✅ 注册成功，重新登录...')
                session.post(f'{BASE_URL}/api/login',
                           json={'username': 'test', 'password': 'test123'},
                           timeout=10)
    except Exception as e:
        print(f'   ❌ 登录失败: {e}')
        return False
    
    # 2. 获取支付配置
    print('\n2. 获取支付配置...')
    try:
        resp = session.get(f'{BASE_URL}/api/payment/config', timeout=10)
        result = resp.json()
        if result.get('success'):
            print(f'   ✅ 配置获取成功')
            print(f'   充值选项: {len(result["data"]["recharge_options"])}个')
        else:
            print(f'   ❌ 配置获取失败: {result.get("error")}')
    except Exception as e:
        print(f'   ❌ 请求失败: {e}')
    
    # 3. 创建订单
    print('\n3. 创建充值订单...')
    order_id = None
    try:
        resp = session.post(f'{BASE_URL}/api/payment/create_order',
                          json={'amount': 30},
                          timeout=10)
        result = resp.json()
        if result.get('success'):
            order_id = result['data']['order_id']
            print(f'   ✅ 订单创建成功')
            print(f'   订单号: {order_id}')
            print(f'   金额: ¥{result["data"]["amount"]}')
            print(f'   获得点数: {result["data"]["total_points"]}点')
        else:
            print(f'   ❌ 创建订单失败: {result.get("error")}')
    except Exception as e:
        print(f'   ❌ 请求失败: {e}')
    
    if not order_id:
        return False
    
    # 4. 获取支付URL
    print('\n4. 获取支付URL...')
    pay_params = None
    try:
        resp = session.get(f'{BASE_URL}/api/payment/pay?order_id={order_id}', timeout=10)
        result = resp.json()
        if result.get('success'):
            pay_params = result['data']['pay_params']
            print(f'   ✅ 支付参数获取成功')
            print(f'   支付网关: {result["data"]["pay_url"]}')
            print(f'   商户订单号: {pay_params["out_trade_no"]}')
        else:
            print(f'   ❌ 获取支付URL失败: {result.get("error")}')
    except Exception as e:
        print(f'   ❌ 请求失败: {e}')
    
    # 5. 查询订单
    print('\n5. 查询订单状态...')
    try:
        resp = session.get(f'{BASE_URL}/api/payment/query?order_id={order_id}', timeout=10)
        result = resp.json()
        if result.get('success'):
            print(f'   ✅ 查询成功')
            print(f'   订单状态: {result["data"]["status"]}')
        else:
            print(f'   ❌ 查询失败: {result.get("error")}')
    except Exception as e:
        print(f'   ❌ 请求失败: {e}')
    
    # 6. 模拟支付回调
    print('\n6. 模拟支付回调...')
    try:
        notify_data = {
            'pid': PID,
            'name': '充值订单',
            'money': '30.00',
            'out_trade_no': order_id,
            'trade_no': f'ZPAY{int(time.time())}',
            'param': '123',
            'trade_status': 'TRADE_SUCCESS',
            'type': 'alipay'
        }
        notify_data['sign'] = generate_sign(notify_data, KEY)
        notify_data['sign_type'] = 'MD5'
        
        resp = session.post(f'{BASE_URL}/api/payment/notify', 
                          data=notify_data,
                          timeout=10)
        print(f'   回调响应: {resp.text}')
        if resp.text == 'success':
            print('   ✅ 回调处理成功')
        else:
            print('   ❌ 回调处理失败')
    except Exception as e:
        print(f'   ❌ 请求失败: {e}')
    
    # 7. 再次查询订单
    print('\n7. 再次查询订单状态...')
    try:
        resp = session.get(f'{BASE_URL}/api/payment/query?order_id={order_id}', timeout=10)
        result = resp.json()
        if result.get('success'):
            print(f'   ✅ 查询成功')
            print(f'   订单状态: {result["data"]["status"]}')
            if result['data']['status'] == 'completed':
                print('   ✅ 订单已支付完成')
        else:
            print(f'   ❌ 查询失败: {result.get("error")}')
    except Exception as e:
        print(f'   ❌ 请求失败: {e}')
    
    # 8. 检查余额
    print('\n8. 检查余额...')
    try:
        resp = session.get(f'{BASE_URL}/api/points/balance', timeout=10)
        result = resp.json()
        if result.get('success'):
            print(f'   ✅ 余额获取成功')
            print(f'   当前余额: {result["data"]["balance"]}点')
        else:
            print(f'   ❌ 获取余额失败')
    except Exception as e:
        print(f'   ❌ 请求失败: {e}')
    
    return True


def main():
    print('\n' + '='*60)
    print('易支付全流程测试')
    print('='*60)
    print(f'商户ID: {PID}')
    print(f'API地址: {API_URL}')
    print(f'本地服务器: {BASE_URL}')
    
    # 测试1: 签名算法
    if not test_sign():
        print('\n❌ 签名算法测试失败，停止测试')
        return
    
    # 测试2: 易支付API
    print('\n是否测试易支付API? (y/n): ', end='')
    choice = input().strip().lower()
    if choice == 'y':
        test_yipay_api()
    
    # 测试3: 本地服务器流程
    print('\n是否测试本地服务器流程? (需要服务器已启动) (y/n): ', end='')
    choice = input().strip().lower()
    if choice == 'y':
        test_local_server()
    
    print('\n' + '='*60)
    print('测试完成')
    print('='*60)
    print('\n使用说明:')
    print('1. 在浏览器中访问 http://127.0.0.1:5000/recharge')
    print('2. 登录后选择充值金额，点击充值')
    print('3. 使用支付宝扫码支付（测试金额0.01元）')
    print('4. 支付完成后会跳转到成功页面')


if __name__ == '__main__':
    main()
