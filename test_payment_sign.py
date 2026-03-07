"""
易支付签名算法测试
"""
import hashlib
import sys
sys.path.insert(0, '.')
from web.api.payment_api import generate_sign, verify_sign

# 测试配置
PID = '2025082311011032'
KEY = 'H9TEykkzChooxOXMeKX8KRn9e1hnjmPu'

# 测试参数（按照易支付文档格式）
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

print('='*60)
print('易支付签名算法测试')
print('='*60)
print(f'商户ID: {PID}')
print(f'商户密钥: {KEY}')

print('\n待签名参数（按ASCII排序）:')
sorted_params = sorted([(k, v) for k, v in params.items() if k not in ['sign', 'sign_type']])
for k, v in sorted_params:
    print(f'  {k}={v}')

# 生成签名
sign = generate_sign(params, KEY)
print(f'\n生成的签名: {sign}')

# 手动验证
sign_str = '&'.join([f'{k}={v}' for k, v in sorted_params])
print(f'\n签名字符串: {sign_str}')
print(f'拼接密钥后: {sign_str}{KEY}')
manual_sign = hashlib.md5(f'{sign_str}{KEY}'.encode('utf-8')).hexdigest().lower()
print(f'手动MD5结果: {manual_sign}')
print(f'签名一致: {"✅ 是" if sign == manual_sign else "❌ 否"}')

# 验证签名
params['sign'] = sign
params['sign_type'] = 'MD5'
is_valid = verify_sign(params, KEY)
print(f'签名验证: {"✅ 通过" if is_valid else "❌ 失败"}')

print('\n' + '='*60)
print("测试完成！")
print('='*60)
