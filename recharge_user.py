#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""给用户充值创造点"""

import sys
sys.path.insert(0, '.')

from web.models.user_model import user_model
from web.models.point_model import point_model

def recharge_user(username, amount):
    """给用户充值创造点"""
    # 获取用户信息
    user = user_model.get_user_by_username(username)
    if not user:
        print(f'未找到用户: {username}')
        return False
    
    user_id = user['id']
    print(f'找到用户: {username}, ID: {user_id}')
    
    # 查询当前余额
    points = point_model.get_user_points(user_id)
    old_balance = points['balance']
    print(f'当前余额: {old_balance} 点')
    
    # 充值
    result = point_model.add_points(user_id, amount, 'admin_grant', '管理员充值')
    if result['success']:
        print(f'充值成功！充值 {amount} 点')
        print(f'新余额: {result["balance"]} 点')
        return True
    else:
        print(f'充值失败: {result.get("error")}')
        return False

if __name__ == '__main__':
    # 给 yanghailin 充值 1000 点
    recharge_user('yanghailin', 1000)
