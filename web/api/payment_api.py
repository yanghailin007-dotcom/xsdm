"""
支付系统API - 易支付（YiiPay）接入
提供充值、订单查询、回调处理等功能
"""
import hashlib
import json
import os
import time
import uuid
import yaml
from flask import Blueprint, request, jsonify, session, redirect
from functools import wraps
from pathlib import Path
import sqlite3
from web.models.point_model import point_model, BASE_DIR
from web.web_config import logger

def get_db_connection():
    """获取数据库连接"""
    db_path = Path(BASE_DIR) / "data" / "users.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

payment_api = Blueprint('payment_api', __name__, url_prefix='/api/payment')

# 加载支付配置
def load_payment_config():
    """加载支付配置"""
    try:
        with open('config/payment.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 从环境变量覆盖敏感配置
        config['yipay']['merchant_id'] = os.environ.get('YIPAY_MERCHANT_ID', config['yipay']['merchant_id'])
        config['yipay']['merchant_key'] = os.environ.get('YIPAY_MERCHANT_KEY', config['yipay']['merchant_key'])
        config['yipay']['api_url'] = os.environ.get('YIPAY_API_URL', config['yipay']['api_url'])
        
        return config
    except Exception as e:
        logger.error(f"加载支付配置失败: {e}")
        return {'enabled': False}

# 登录验证装饰器
def login_required_api(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') and 'user_id' not in session:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


def generate_sign(params, key):
    """
    生成易支付签名
    按照易支付规范：参数按ASCII排序后拼接成字符串，最后加上key进行MD5加密（小写）
    """
    # 过滤空值、sign和sign_type参数
    filtered_params = {k: v for k, v in params.items() if v is not None and k not in ['sign', 'sign_type']}
    
    # 按ASCII排序
    sorted_params = sorted(filtered_params.items())
    
    # 拼接成字符串 (URL键值对格式)
    sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
    
    # 加上商户密钥key（拼接符不是URL参数）
    sign_str += key
    
    # MD5加密并转小写
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest().lower()


def verify_sign(params, key):
    """验证易支付回调签名"""
    sign = params.get('sign', '')
    if not sign:
        return False
    
    calculated_sign = generate_sign(params, key)
    # 易支付返回的签名是小写，直接比较
    return sign.lower() == calculated_sign.lower()


# ==================== 充值API ====================

@payment_api.route('/config', methods=['GET'])
@login_required_api
def get_payment_config():
    """获取支付配置和充值选项"""
    config = load_payment_config()
    
    if not config.get('enabled'):
        return jsonify({
            'success': False,
            'error': '支付功能暂未开启'
        }), 400
    
    return jsonify({
        'success': True,
        'data': {
            'enabled': True,
            'exchange_rate': config.get('exchange_rate', 1),
            'recharge_options': config.get('recharge_options', []),
            'min_amount': config.get('min_amount', 1),
            'max_amount': config.get('max_amount', 5000)
        }
    })


@payment_api.route('/create_order', methods=['POST'])
@login_required_api
def create_order():
    """创建充值订单"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '用户信息不完整'}), 401
    
    config = load_payment_config()
    if not config.get('enabled'):
        return jsonify({'success': False, 'error': '支付功能暂未开启'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求参数错误'}), 400
    
    amount = data.get('amount', 0)
    
    # 验证金额
    min_amount = config.get('min_amount', 1)
    max_amount = config.get('max_amount', 5000)
    
    if not isinstance(amount, (int, float)) or amount < min_amount:
        return jsonify({
            'success': False, 
            'error': f'充值金额不能低于{min_amount}元'
        }), 400
    
    if amount > max_amount:
        return jsonify({
            'success': False, 
            'error': f'充值金额不能超过{max_amount}元'
        }), 400
    
    # 计算赠送点数
    bonus = 0
    for option in config.get('recharge_options', []):
        if option['amount'] == amount:
            bonus = option.get('bonus', 0)
            break
    
    # 🔥 充值比例：1元 = 10创造点
    total_points = amount * 10 + bonus
    
    # 生成订单号
    order_id = f"PAY{int(time.time())}{user_id}{uuid.uuid4().hex[:8]}"
    
    # 保存订单到数据库
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payment_orders 
            (order_id, user_id, amount, bonus, total_points, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (order_id, user_id, amount, bonus, total_points, 'pending', int(time.time())))
        
        conn.commit()
        conn.close()
        
        logger.info(f"创建充值订单: order_id={order_id}, user_id={user_id}, amount={amount}")
        
        return jsonify({
            'success': True,
            'data': {
                'order_id': order_id,
                'amount': amount,
                'bonus': bonus,
                'total_points': total_points,
                'pay_url': f"/api/payment/pay?order_id={order_id}"
            }
        })
        
    except Exception as e:
        logger.error(f"创建订单失败: {e}")
        return jsonify({'success': False, 'error': '创建订单失败，请稍后重试'}), 500


@payment_api.route('/pay', methods=['GET'])
@login_required_api
def go_pay():
    """跳转到支付页面"""
    user_id = session.get('user_id')
    order_id = request.args.get('order_id')
    
    if not order_id:
        return jsonify({'success': False, 'error': '订单号不能为空'}), 400
    
    config = load_payment_config()
    if not config.get('enabled'):
        return jsonify({'success': False, 'error': '支付功能暂未开启'}), 400
    
    try:
        # 查询订单
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM payment_orders 
            WHERE order_id = ? AND user_id = ?
        ''', (order_id, user_id))
        
        order = cursor.fetchone()
        conn.close()
        
        if not order:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        
        if order['status'] != 'pending':
            return jsonify({'success': False, 'error': '订单状态异常'}), 400
        
        # 构建易支付请求参数
        notify_url = request.host_url.rstrip('/') + config['yipay']['notify_url']
        return_url = request.host_url.rstrip('/') + config['yipay']['return_url']
        
        logger.info(f"支付回调地址(notify_url): {notify_url}")
        logger.info(f"支付跳转地址(return_url): {return_url}")
        
        pay_params = {
            'pid': config['yipay']['merchant_id'],
            'type': config['yipay']['pay_type'],
            'out_trade_no': order_id,
            'notify_url': notify_url,
            'return_url': return_url,
            'name': f"充值{order['amount']}点",
            'money': str(order['amount']),
            'param': str(user_id)  # 透传参数，回调时原样返回
        }
        
        # 生成签名
        pay_params['sign'] = generate_sign(pay_params, config['yipay']['merchant_key'])
        pay_params['sign_type'] = 'MD5'
        
        # 构建支付URL
        pay_url = config['yipay']['api_url'] + '/submit.php'
        
        # 返回表单数据，前端自动提交
        return jsonify({
            'success': True,
            'data': {
                'pay_url': pay_url,
                'pay_params': pay_params,
                'method': 'POST'
            }
        })
        
    except Exception as e:
        logger.error(f"构建支付请求失败: {e}")
        return jsonify({'success': False, 'error': '支付请求失败'}), 500


@payment_api.route('/notify', methods=['POST', 'GET'])
def payment_notify():
    """支付异步回调 - 支持POST和GET"""
    logger.info("="*60)
    logger.info("【支付回调】收到请求")
    logger.info(f"请求方法: {request.method}")
    logger.info(f"请求URL: {request.url}")
    logger.info(f"请求头: {dict(request.headers)}")
    
    config = load_payment_config()
    if not config.get('enabled'):
        logger.error("支付功能未开启")
        return 'fail', 400
    
    # 获取回调参数 - 同时支持POST(form/json)和GET
    if request.method == 'POST':
        if request.form:
            params = request.form.to_dict()
            logger.info(f"POST Form参数: {params}")
        elif request.json:
            params = request.json
            logger.info(f"POST JSON参数: {params}")
        else:
            params = {}
            logger.warning("POST请求但没有参数")
    else:  # GET
        params = request.args.to_dict()
        logger.info(f"GET参数: {params}")
    
    if not params:
        logger.error("回调参数为空")
        return 'fail', 400
    
    logger.info(f"处理回调参数: {params}")
    
    # 验证签名
    logger.info(f"准备验证签名，商户密钥: {config['yipay']['merchant_key'][:10]}...")
    sign = params.get('sign', '')
    logger.info(f"回调签名: {sign}")
    
    if not verify_sign(params, config['yipay']['merchant_key']):
        logger.error("支付回调签名验证失败")
        # 打印详细调试信息
        filtered_params = {k: v for k, v in params.items() if v is not None and k not in ['sign', 'sign_type']}
        sorted_params = sorted(filtered_params.items())
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
        sign_str += config['yipay']['merchant_key']
        logger.error(f"签名字符串: {sign_str}")
        logger.error(f"计算签名: {hashlib.md5(sign_str.encode('utf-8')).hexdigest().lower()}")
        logger.error(f"收到签名: {sign}")
        return 'fail', 400
    
    logger.info("签名验证通过")
    
    # 获取订单信息
    order_id = params.get('out_trade_no')
    trade_no = params.get('trade_no')  # 易支付订单号
    trade_status = params.get('trade_status')
    
    logger.info(f"订单号: {order_id}")
    logger.info(f"易支付订单号: {trade_no}")
    logger.info(f"支付状态: {trade_status}")
    
    if trade_status != 'TRADE_SUCCESS':
        logger.warning(f"支付未完成，状态: {trade_status}")
        return 'success'  # 返回success避免重复通知
    
    try:
        logger.info(f"开始处理订单: {order_id}")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询订单
        logger.info(f"查询订单: {order_id}")
        cursor.execute('SELECT * FROM payment_orders WHERE order_id = ?', (order_id,))
        order = cursor.fetchone()
        
        if not order:
            logger.error(f"回调订单不存在: {order_id}")
            return 'fail', 404
        
        logger.info(f"订单信息: {dict(order)}")
        
        if order['status'] == 'completed':
            logger.info(f"订单已处理过: {order_id}")
            return 'success'
        
        if order['status'] != 'pending':
            logger.warning(f"订单状态异常: {order_id}, status={order['status']}")
            return 'fail', 400
        
        user_id = order['user_id']
        total_points = order['total_points']
        logger.info(f"准备处理充值: user_id={user_id}, points={total_points}, trade_no={trade_no}")
        
        # 更新订单状态
        logger.info(f"更新订单状态为completed: {order_id}")
        cursor.execute('''
            UPDATE payment_orders 
            SET status = ?, trade_no = ?, paid_at = ?
            WHERE order_id = ?
        ''', ('completed', trade_no, int(time.time()), order_id))
        
        conn.commit()
        logger.info(f"订单状态已更新: {order_id}")
        conn.close()
        
        # 发放点数
        logger.info(f"开始发放点数: user_id={user_id}, amount={total_points}")
        result = point_model.add_points(
            user_id=user_id,
            amount=total_points,
            source='recharge',
            description=f'支付宝充值: ¥{order["amount"]}，获得{total_points}点'
        )
        
        if result['success']:
            logger.info(f"✅ 充值处理完成: order_id={order_id}, user_id={user_id}, points={total_points}, new_balance={result.get('balance')}")
            logger.info("="*60)
            return 'success'
        else:
            logger.error(f"❌ 发放点数失败: {result}")
            logger.info("="*60)
            return 'fail', 500
            
    except Exception as e:
        logger.error(f"处理支付回调失败: {e}")
        return 'fail', 500


@payment_api.route('/query', methods=['GET'])
@login_required_api
def query_order():
    """查询订单状态 - 同时查询易支付平台实时状态"""
    user_id = session.get('user_id')
    order_id = request.args.get('order_id')
    
    if not order_id:
        return jsonify({'success': False, 'error': '订单号不能为空'}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM payment_orders 
            WHERE order_id = ? AND user_id = ?
        ''', (order_id, user_id))
        
        order = cursor.fetchone()
        conn.close()
        
        if not order:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        
        order_data = dict(order)
        
        # 🔥 如果订单是 pending 状态，主动查询易支付平台
        if order_data['status'] == 'pending':
            logger.info(f"订单 {order_id} 本地状态为 pending，查询易支付平台...")
            yipay_status = query_yipay_order(order_id)
            logger.info(f"易支付查询结果: {yipay_status}")
            
            if yipay_status.get('paid'):
                # 易支付显示已支付，处理订单
                logger.info(f"易支付显示订单 {order_id} 已支付，开始处理...")
                process_payment_callback(order_id, yipay_status.get('trade_no'))
                
                # 重新查询订单状态
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM payment_orders WHERE order_id = ?', (order_id,))
                order = cursor.fetchone()
                conn.close()
                order_data = dict(order) if order else order_data
                order_data['status'] = 'completed'  # 更新状态显示
        
        return jsonify({
            'success': True,
            'data': {
                'order_id': order_data['order_id'],
                'amount': order_data['amount'],
                'bonus': order_data['bonus'],
                'total_points': order_data['total_points'],
                'status': order_data['status'],
                'created_at': order_data['created_at'],
                'paid_at': order_data['paid_at']
            }
        })
        
    except Exception as e:
        logger.error(f"查询订单失败: {e}")
        return jsonify({'success': False, 'error': '查询失败'}), 500


def query_yipay_order(order_id):
    """
    查询易支付平台订单状态
    返回: {'paid': True/False, 'trade_no': 'xxx', 'msg': 'xxx'}
    """
    import requests
    
    config = load_payment_config()
    if not config.get('enabled'):
        return {'paid': False, 'msg': '支付未启用'}
    
    try:
        # 构建查询URL
        query_url = f"{config['yipay']['api_url']}/api.php?act=order"
        query_url += f"&pid={config['yipay']['merchant_id']}"
        query_url += f"&key={config['yipay']['merchant_key']}"
        query_url += f"&out_trade_no={order_id}"
        
        logger.info(f"查询易支付订单: {query_url}")
        
        resp = requests.get(query_url, timeout=10)
        logger.info(f"易支付查询响应: {resp.text}")
        
        result = resp.json()
        
        logger.info(f"解析结果: code={result.get('code')} (type={type(result.get('code'))}), status={result.get('status')} (type={type(result.get('status'))})")
        
        # 同时支持字符串和数字
        code = result.get('code')
        if code == 1 or code == '1':
            # code=1 表示查询成功
            status = result.get('status')
            logger.info(f"查询成功，支付状态: {status}")
            if status == 1 or status == '1':
                # status=1 表示已支付
                logger.info(f"✅ 检测到已支付！trade_no: {result.get('trade_no')}")
                return {
                    'paid': True,
                    'trade_no': result.get('trade_no', ''),
                    'msg': '已支付'
                }
            else:
                logger.info(f"⏳ 未支付，status={status}")
                return {
                    'paid': False,
                    'trade_no': '',
                    'msg': '未支付'
                }
        else:
            logger.warning(f"查询失败: code={code}, msg={result.get('msg')}")
            return {
                'paid': False,
                'msg': result.get('msg', '查询失败')
            }
            
    except Exception as e:
        logger.error(f"查询易支付订单失败: {e}")
        return {'paid': False, 'msg': f'查询异常: {str(e)}'}


def process_payment_callback(order_id, trade_no):
    """
    处理支付完成的订单（与回调逻辑相同）
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询订单
        cursor.execute('SELECT * FROM payment_orders WHERE order_id = ?', (order_id,))
        order = cursor.fetchone()
        
        if not order:
            logger.error(f"处理订单失败，订单不存在: {order_id}")
            conn.close()
            return False
        
        if order['status'] == 'completed':
            logger.info(f"订单已处理过: {order_id}")
            conn.close()
            return True
        
        if order['status'] != 'pending':
            logger.warning(f"订单状态异常: {order_id}, status={order['status']}")
            conn.close()
            return False
        
        user_id = order['user_id']
        total_points = order['total_points']
        
        # 更新订单状态
        cursor.execute('''
            UPDATE payment_orders 
            SET status = ?, trade_no = ?, paid_at = ?
            WHERE order_id = ?
        ''', ('completed', trade_no, int(time.time()), order_id))
        
        conn.commit()
        conn.close()
        
        # 发放点数
        result = point_model.add_points(
            user_id=user_id,
            amount=total_points,
            source='recharge',
            description=f'支付宝充值: ¥{order["amount"]}，获得{total_points}点'
        )
        
        if result['success']:
            logger.info(f"✅ 订单处理完成: order_id={order_id}, user_id={user_id}, points={total_points}")
            return True
        else:
            logger.error(f"❌ 发放点数失败: {result}")
            return False
            
    except Exception as e:
        logger.error(f"处理订单失败: {e}")
        return False


@payment_api.route('/orders', methods=['GET'])
@login_required_api
def get_order_list():
    """获取充值记录"""
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * limit
        
        # 查询总数
        cursor.execute(
            'SELECT COUNT(*) as total FROM payment_orders WHERE user_id = ?',
            (user_id,)
        )
        total = cursor.fetchone()['total']
        
        # 查询记录
        cursor.execute('''
            SELECT * FROM payment_orders 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset))
        
        orders = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'page': page,
                'limit': limit,
                'orders': [dict(order) for order in orders]
            }
        })
        
    except Exception as e:
        logger.error(f"获取充值记录失败: {e}")
        return jsonify({'success': False, 'error': '获取失败'}), 500
