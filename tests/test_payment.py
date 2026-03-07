"""
易支付全流程测试脚本
测试内容：
1. 签名算法验证
2. 创建订单
3. 支付查询
4. 回调处理
"""
import hashlib
import sys
import os
import time
import requests
import json

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from web.api.payment_api import generate_sign, verify_sign


# ============== 配置 ==============
# 易支付配置
PID = "2025082311011032"
KEY = "H9TEykkzChooxOXMeKX8KRn9e1hnjmPu"
API_URL = "https://zpayz.cn"

# 本地服务器配置
BASE_URL = "http://127.0.0.1:5000"


def test_sign_algorithm():
    """测试签名算法"""
    print("\n" + "="*60)
    print("【测试1】签名算法验证")
    print("="*60)
    
    # 测试数据（模拟真实请求参数）
    params = {
        "pid": PID,
        "type": "alipay",
        "out_trade_no": "TEST2025082311011032",
        "notify_url": "http://localhost/api/payment/notify",
        "return_url": "http://localhost/payment/success",
        "name": "充值100点",
        "money": "100.00",
        "param": "123"
    }
    
    # 生成签名
    sign = generate_sign(params, KEY)
    params['sign'] = sign
    params['sign_type'] = 'MD5'
    
    print(f"商户ID: {PID}")
    print(f"商户密钥: {KEY}")
    print(f"\n待签名参数:")
    for k, v in sorted(params.items()):
        if k not in ['sign', 'sign_type']:
            print(f"  {k}={v}")
    
    print(f"\n生成的签名: {sign}")
    
    # 验证签名
    is_valid = verify_sign(params, KEY)
    print(f"签名验证结果: {'✅ 通过' if is_valid else '❌ 失败'}")
    
    # 手动计算验证
    sorted_params = sorted([(k, v) for k, v in params.items() if k not in ['sign', 'sign_type']])
    sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
    sign_str += KEY
    manual_sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest().lower()
    
    print(f"\n手动计算验证:")
    print(f"  签名字符串: {sign_str}")
    print(f"  MD5结果: {manual_sign}")
    print(f"  与生成签名一致: {'✅ 是' if sign == manual_sign else '❌ 否'}")
    
    return is_valid


def test_create_order():
    """测试创建订单"""
    print("\n" + "="*60)
    print("【测试2】创建充值订单")
    print("="*60)
    
    # 首先登录获取session
    session = requests.Session()
    
    # 尝试登录（使用测试账号）
    login_data = {
        "username": "test",
        "password": "test123"
    }
    
    try:
        resp = session.post(f"{BASE_URL}/api/login", json=login_data, timeout=10)
        if resp.status_code == 200:
            print("✅ 登录成功")
        else:
            print(f"⚠️ 登录响应: {resp.status_code} - 可能用户不存在，继续测试...")
    except Exception as e:
        print(f"⚠️ 登录请求失败: {e}")
        print("提示: 请确保服务器已启动（运行 python web/app.py）")
        return None
    
    # 创建订单
    order_data = {
        "amount": 30  # 充值30元
    }
    
    try:
        resp = session.post(f"{BASE_URL}/api/payment/create_order", json=order_data, timeout=10)
        result = resp.json()
        
        if result.get('success'):
            data = result['data']
            print(f"✅ 订单创建成功!")
            print(f"  订单号: {data['order_id']}")
            print(f"  金额: ¥{data['amount']}")
            print(f"  赠送: {data['bonus']}点")
            print(f"  总计: {data['total_points']}点")
            print(f"  支付URL: {data['pay_url']}")
            return data['order_id']
        else:
            print(f"❌ 创建订单失败: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def test_pay_url(order_id):
    """测试获取支付URL"""
    print("\n" + "="*60)
    print("【测试3】获取支付URL")
    print("="*60)
    
    session = requests.Session()
    
    # 登录
    login_data = {"username": "test", "password": "test123"}
    try:
        session.post(f"{BASE_URL}/api/login", json=login_data, timeout=10)
    except:
        pass
    
    try:
        resp = session.get(f"{BASE_URL}/api/payment/pay?order_id={order_id}", timeout=10)
        result = resp.json()
        
        if result.get('success'):
            data = result['data']
            print(f"✅ 获取支付参数成功!")
            print(f"  支付网关: {data['pay_url']}")
            print(f"  请求方法: {data['method']}")
            print(f"\n  支付参数:")
            for k, v in data['pay_params'].items():
                print(f"    {k}: {v}")
            
            # 构造支付链接
            pay_params = data['pay_params']
            query_string = '&'.join([f"{k}={v}" for k, v in pay_params.items()])
            full_url = f"{data['pay_url']}?{query_string}"
            print(f"\n  完整支付URL(GET方式):")
            print(f"  {full_url[:150]}...")
            
            return data['pay_params']
        else:
            print(f"❌ 获取支付URL失败: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def test_query_order(order_id):
    """测试查询订单"""
    print("\n" + "="*60)
    print("【测试4】查询订单状态")
    print("="*60)
    
    session = requests.Session()
    
    # 登录
    login_data = {"username": "test", "password": "test123"}
    try:
        session.post(f"{BASE_URL}/api/login", json=login_data, timeout=10)
    except:
        pass
    
    try:
        resp = session.get(f"{BASE_URL}/api/payment/query?order_id={order_id}", timeout=10)
        result = resp.json()
        
        if result.get('success'):
            data = result['data']
            print(f"✅ 查询成功!")
            print(f"  订单号: {data['order_id']}")
            print(f"  金额: ¥{data['amount']}")
            print(f"  状态: {data['status']}")
            print(f"  创建时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['created_at']))}")
            return data
        else:
            print(f"❌ 查询失败: {result.get('error')}")
            return None
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None


def test_direct_api_order():
    """直接测试易支付API创建订单（不经过本地服务器）"""
    print("\n" + "="*60)
    print("【测试5】直接测试易支付API接口")
    print("="*60)
    
    out_trade_no = f"TEST{int(time.time())}"
    
    params = {
        "pid": PID,
        "type": "alipay",
        "out_trade_no": out_trade_no,
        "notify_url": "http://localhost/notify",
        "return_url": "http://localhost/return",
        "name": "测试商品",
        "money": "0.01",  # 测试金额0.01元
        "clientip": "127.0.0.1",
        "param": "test"
    }
    
    # 生成签名
    sign = generate_sign(params, KEY)
    params['sign'] = sign
    params['sign_type'] = 'MD5'
    
    print(f"请求参数:")
    for k, v in params.items():
        print(f"  {k}: {v}")
    
    try:
        # 使用API接口方式创建订单
        resp = requests.post(f"{API_URL}/mapi.php", data=params, timeout=30)
        print(f"\n响应状态码: {resp.status_code}")
        print(f"响应内容: {resp.text}")
        
        try:
            result = resp.json()
            if result.get('code') == 1:
                print(f"✅ API调用成功!")
                print(f"  订单号: {result.get('trade_no')}")
                print(f"  支付URL: {result.get('payurl')}")
                print(f"  二维码: {result.get('qrcode')}")
                return result
            else:
                print(f"❌ API调用失败: {result.get('msg')}")
        except:
            print("⚠️ 响应不是JSON格式")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    return None


def test_simulate_notify(order_id):
    """模拟支付回调"""
    print("\n" + "="*60)
    print("【测试6】模拟支付回调")
    print("="*60)
    
    # 构造回调参数
    notify_params = {
        "pid": PID,
        "name": f"充值订单",
        "money": "30.00",
        "out_trade_no": order_id,
        "trade_no": f"ZPAY{int(time.time())}",
        "param": "123",
        "trade_status": "TRADE_SUCCESS",
        "type": "alipay"
    }
    
    # 生成签名
    sign = generate_sign(notify_params, KEY)
    notify_params['sign'] = sign
    notify_params['sign_type'] = 'MD5'
    
    print(f"回调参数:")
    for k, v in notify_params.items():
        print(f"  {k}: {v}")
    
    try:
        resp = requests.post(f"{BASE_URL}/api/payment/notify", data=notify_params, timeout=10)
        print(f"\n响应状态码: {resp.status_code}")
        print(f"响应内容: {resp.text}")
        
        if resp.text == 'success':
            print("✅ 回调处理成功!")
        else:
            print(f"❌ 回调处理失败")
            
    except Exception as e:
        print(f"❌ 请求失败: {e}")


def main():
    """主测试流程"""
    print("\n" + "="*60)
    print("易支付接入测试")
    print("="*60)
    print(f"API地址: {API_URL}")
    print(f"商户ID: {PID}")
    print(f"本地服务器: {BASE_URL}")
    
    # 1. 测试签名算法
    if not test_sign_algorithm():
        print("\n❌ 签名算法测试失败，停止后续测试")
        return
    
    # 2. 直接测试易支付API
    test_direct_api_order()
    
    # 3. 测试本地订单创建
    order_id = test_create_order()
    if order_id:
        # 4. 测试获取支付URL
        test_pay_url(order_id)
        
        # 5. 测试查询订单
        test_query_order(order_id)
        
        # 6. 模拟回调
        test_simulate_notify(order_id)
        
        # 再次查询订单状态
        print("\n" + "-"*60)
        print("回调后再次查询订单状态:")
        test_query_order(order_id)
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)


if __name__ == "__main__":
    main()
