# 阿里云安全组配置指南 - 开放5000端口

## 问题说明

如果您访问 http://8.163.37.124:5000 时看到 "HTTP ERROR 502" 或无法访问,这是因为阿里云安全组没有开放5000端口。

## 解决方案

### 方法1: 通过阿里云控制台配置(推荐)

1. 登录 [阿里云控制台](https://ecs.console.aliyun.com/)
2. 进入 **云服务器ECS** → **实例与镜像** → **实例**
3. 找到您的实例 (8.163.37.124)
4. 点击实例ID进入详情页
5. 点击 **安全组** 标签
6. 点击 **配置规则** → **入方向** → **手动添加**
7. 添加以下规则:
   - **授权策略**: 允许
   - **优先级**: 1
   - **协议类型**: 自定义TCP
   - **端口范围**: 5000/5000
   - **授权对象**: 0.0.0.0/0 (允许所有IP访问)
   - **描述**: 小说生成系统Web服务
8. 点击 **保存**

### 方法2: 使用阿里云CLI

```bash
# 添加安全组规则
aliyun ecs AuthorizeSecurityGroup \
  --SecurityGroupId sg-xxxxx \
  --IpProtocol tcp \
  --PortRange 5000/5000 \
  --SourceCidrIp 0.0.0.0/0 \
  --Description "小说生成系统Web服务"
```

### 方法3: 使用阿里云OpenAPI

```python
import json
from aliyunsdkcore.client import AcsClient
from aliyunsdkecs.request.v20140526 import AuthorizeSecurityGroupRequest

# 创建客户端
client = AcsClient(
    'your-access-key-id',
    'your-access-key-secret',
    'cn-hangzhou'
)

# 创建请求
request = AuthorizeSecurityGroupRequest.AuthorizeSecurityGroupRequest()
request.set_SecurityGroupId('sg-xxxxx')
request.set_IpProtocol('tcp')
request.set_PortRange('5000/5000')
request.set_SourceCidrIp('0.0.0.0/0')
request.set_Description('小说生成系统Web服务')

# 发送请求
response = client.do_action_with_exception(request)
print(json.dumps(json.loads(response), indent=2))
```

## 验证配置

配置完成后,等待1-2分钟,然后访问:

```
http://8.163.37.124:5000
```

您应该能看到登录页面或系统首页。

## 安全建议

如果您希望限制访问,可以设置特定的授权对象:
- **仅允许特定IP**: 将授权对象改为您的IP地址,例如 `123.45.67.89/32`
- **仅允许特定网段**: 例如 `123.45.67.0/24`
- **使用VPN**: 先配置VPN,然后只允许VPN网段访问

## 服务管理命令

```bash
# 查看服务状态
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "supervisorctl status novel-system"

# 查看日志
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "tail -f /home/novelapp/novel-system/logs/gunicorn-error.log"

# 重启服务
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "supervisorctl restart novel-system"

# 停止服务
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "supervisorctl stop novel-system"
```

## 故障排查

### 1. 检查端口是否监听
```bash
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "netstat -tlnp | grep 5000"
```
应该看到: `tcp  0  0 0.0.0.0:5000  0.0.0.0:*  LISTEN`

### 2. 检查服务状态
```bash
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "supervisorctl status novel-system"
```
应该看到: `novel-system  RUNNING`

### 3. 测试本地访问
```bash
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "curl -I http://localhost:5000"
```
应该返回: `HTTP/1.1 302 FOUND` 或 `HTTP/1.1 200 OK`

### 4. 检查服务器防火墙
```bash
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "ufw status"
```
如果UFW启用,确保5000端口已开放:
```bash
ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124 "ufw allow 5000/tcp"
```

## 常见问题

**Q: 为什么从服务器内部可以访问,但外部不行?**  
A: 这通常是云服务商的安全组或防火墙规则阻止了外部访问。需要在云控制台配置安全组规则。

**Q: 配置了安全组还是无法访问?**  
A: 安全组规则生效需要1-2分钟,请等待后重试。如果仍无法访问,检查是否有其他安全设备(如WAF、防火墙)。

**Q: 如何提高安全性?**  
A: 建议:
1. 使用HTTPS (配置SSL证书)
2. 限制授权对象为特定IP或网段
3. 使用VPN或堡垒机
4. 配置Web应用防火墙(WAF)

## 联系支持

如果以上方法都无法解决问题,请联系:
- 阿里云技术支持: https://help.aliyun.com/
- 本项目GitHub Issues