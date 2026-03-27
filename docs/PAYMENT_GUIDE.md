# 易支付接入指南

## ✅ 接入完成状态

支付系统已完成接入并测试通过！

## 📋 配置信息

| 配置项 | 值 |
|--------|-----|
| 接口地址 | https://zpayz.cn |
| 商户ID (PID) | 2025082311011032 |
| 商户密钥 (PKEY) | H9TEykkzChooxOXMeKX8KRn9e1hnjmPu |

## 🔧 配置文件

### 1. 环境变量 (.env)
```env
YIPAY_MERCHANT_ID=2025082311011032
YIPAY_MERCHANT_KEY=H9TEykkzChooxOXMeKX8KRn9e1hnjmPu
YIPAY_API_URL=https://zpayz.cn
```

### 2. 支付配置 (config/payment.yaml)
```yaml
enabled: true
yipay:
  api_url: "https://zpayz.cn"
  merchant_id: "2025082311011032"
  merchant_key: "H9TEykkzChooxOXMeKX8KRn9e1hnjmPu"
  pay_type: "alipay"
  notify_url: "/api/payment/notify"
  return_url: "/payment/success"
```

## 🧪 测试结果

### ✅ 签名算法测试
```
签名生成: ab289f9161f391cc77530f66ae2b7af8
签名验证: ✅ 通过
```

### ✅ API接口测试
```
订单号: TEST1772853296
响应: {"code":1,"msg":"success","trade_no":"TEST1772853296",...}
支付URL: https://qr.alipay.com/bax00000p9yr2uaqvcqq55e3
二维码: https://zpayz.cn/qrcode/...
```

## 📖 使用说明

### 1. 启动服务器
```bash
python web/app.py
```

### 2. 访问充值页面
在浏览器中打开: http://127.0.0.1:5000/recharge

### 3. 支付流程

#### 用户端流程:
1. 登录账号
2. 进入充值页面 (/recharge)
3. 选择充值金额或输入自定义金额
4. 选择支付方式（支付宝/微信）
5. 点击充值按钮
6. 扫描二维码或点击支付链接完成支付
7. 支付成功后自动跳转到成功页面
8. 点数自动到账

#### 系统端流程:
1. 用户创建订单 → `/api/payment/create_order`
2. 获取支付参数 → `/api/payment/pay`
3. 用户完成支付（在易支付平台）
4. 易支付发送异步通知 → `/api/payment/notify`
5. 系统验证签名并发放点数
6. 用户被重定向到成功页面 → `/payment/success`

## 🔌 API接口

### 获取支付配置
```http
GET /api/payment/config
```

### 创建充值订单
```http
POST /api/payment/create_order
Content-Type: application/json

{
  "amount": 100  // 充值金额（元）
}
```

### 获取支付URL
```http
GET /api/payment/pay?order_id=xxx
```

### 查询订单状态
```http
GET /api/payment/query?order_id=xxx
```

### 支付回调通知
```http
POST /api/payment/notify
Content-Type: application/x-www-form-urlencoded
```

## 📝 测试命令

### 签名算法测试
```bash
python test_payment_sign.py
```

### 易支付API测试
```bash
python test_payment_api.py
```

### 完整流程测试（需启动服务器）
```bash
python test_payment_auto.py
```

## ⚠️ 注意事项

1. **回调URL必须外网可访问**: 支付回调需要外网能访问到你的服务器
2. **签名验证**: 系统已正确实现易支付签名算法（小写MD5）
3. **订单幂等**: 同一订单不会重复发放点数
4. **测试金额**: 测试时建议使用0.01元

## 🔐 安全建议

1. 生产环境请使用HTTPS
2. 妥善保管商户密钥，不要泄露
3. 验证所有回调通知的签名
4. 对订单状态进行幂等处理

## 📞 技术支持

如有问题，请检查:
1. 服务器是否正常启动
2. 配置文件是否正确
3. 网络连接是否正常
4. 查看日志文件排查问题
