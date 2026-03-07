"""
直接测试易支付API接口
"""
import hashlib
import sys
import time
import requests
sys.path.insert(0, '.')
from web.api.payment_api import generate_sign

# 测试配置
PID = '2025082311011032'
KEY = 'H9TEykkzChooxOXMeKX8KRn9e1hnjmPu'
API_URL = 'https://zpayz.cn'

print('='*60)
print('易支付API接口测试')
print('='*60)
print(f'API地址: {API_URL}')
print(f'商户ID: {PID}')

# 测试1: API接口支付（mapi.php）
print('\n' + '-'*60)
print('【测试1】API接口支付 (mapi.php)')
print('-'*60)

out_trade_no = f'TEST{int(time.time())}'
params = {
    'pid': PID,
    'type': 'alipay',
    'out_trade_no': out_trade_no,
    'notify_url': 'http://localhost/notify',
    'return_url': 'http://localhost/return',
    'name': '测试商品-API接口',
    'money': '0.01',  # 测试金额0.01元
    'clientip': '127.0.0.1',
    'device': 'pc',
    'param': 'test'
}

# 生成签名
sign = generate_sign(params, KEY)
params['sign'] = sign
params['sign_type'] = 'MD5'

print(f'订单号: {out_trade_no}')
print(f'请求参数:')
for k, v in params.items():
    print(f'  {k}: {v}')

try:
    resp = requests.post(f'{API_URL}/mapi.php', data=params, timeout=30)
    print(f'\n响应状态码: {resp.status_code}')
    print(f'响应内容: {resp.text}')
    
    try:
        result = resp.json()
        if result.get('code') == 1:
            print(f'\n✅ API调用成功!')
            print(f'  易支付订单号: {result.get("trade_no")}')
            print(f'  内部订单号: {result.get("O_id")}')
            print(f'  支付URL: {result.get("payurl")}')
            print(f'  二维码链接: {result.get("qrcode")}')
            
            # 测试订单查询
            print('\n' + '-'*60)
            print('【测试2】查询订单状态')
            print('-'*60)
            
            query_url = f'{API_URL}/api.php?act=order&pid={PID}&key={KEY}&out_trade_no={out_trade_no}'
            print(f'查询URL: {query_url}')
            
            query_resp = requests.get(query_url, timeout=10)
            print(f'查询响应: {query_resp.text}')
            
            try:
                query_result = query_resp.json()
                if query_result.get('code') == 1:
                    print(f'\n✅ 查询成功!')
                    print(f'  订单状态: {"已支付" if query_result.get("status") == 1 else "未支付"}')
                    print(f'  商品名称: {query_result.get("name")}')
                    print(f'  订单金额: {query_result.get("money")}')
                else:
                    print(f'\n❌ 查询失败: {query_result.get("msg")}')
            except:
                print('查询响应解析失败')
        else:
            print(f'\n❌ API调用失败: {result.get("msg")}')
    except Exception as e:
        print(f'\n⚠️ 响应解析失败: {e}')
        
except Exception as e:
    print(f'\n❌ 请求失败: {e}')

# 测试2: 页面跳转支付（submit.php）
print('\n' + '-'*60)
print('【测试3】页面跳转支付URL (submit.php)')
print('-'*60)

out_trade_no2 = f'TEST{int(time.time())}_PAGE'
params2 = {
    'pid': PID,
    'type': 'alipay',
    'out_trade_no': out_trade_no2,
    'notify_url': 'http://localhost/notify',
    'return_url': 'http://localhost/return',
    'name': '测试商品-页面跳转',
    'money': '0.01',
    'param': 'test'
}

sign2 = generate_sign(params2, KEY)
params2['sign'] = sign2
params2['sign_type'] = 'MD5'

# 构建支付URL
query_string = '&'.join([f'{k}={v}' for k, v in params2.items()])
pay_url = f'{API_URL}/submit.php?{query_string}'

print(f'订单号: {out_trade_no2}')
print(f'支付URL:')
print(f'{pay_url}')

print('\n' + '='*60)
print('测试完成！')
print('='*60)
print('\n说明:')
print('1. API接口返回的 payurl 可以直接跳转支付')
print('2. 页面跳转URL可以直接在浏览器打开')
print('3. 支付完成后，平台会向 notify_url 发送回调通知')
print('4. 用户支付完成后会跳转到 return_url')
