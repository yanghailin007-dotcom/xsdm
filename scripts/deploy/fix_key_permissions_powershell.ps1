# 强制修复私钥文件权限的PowerShell脚本
# 使用方法: PowerShell -ExecutionPolicy Bypass -File fix_key_permissions_powershell.ps1

$KeyPath = "d:\work6.05\xsdm.pem"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   强制修复私钥文件权限 (PowerShell)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查文件是否存在
if (-not (Test-Path $KeyPath)) {
    Write-Host "❌ 错误: 私钥文件不存在: $KeyPath" -ForegroundColor Red
    Read-Host "按Enter键退出"
    exit 1
}

Write-Host "步骤 1/5: 查看当前权限..." -ForegroundColor Yellow
Write-Host "----------------------------------------"
$acl = Get-Acl $KeyPath
$acl.Access | Format-Table -AutoSize
Write-Host ""

Write-Host "步骤 2/5: 禁用继承并移除所有继承权限..." -ForegroundColor Yellow
Write-Host "----------------------------------------"
try {
    $acl.SetAccessRuleProtection($true, $false)
    Set-Acl $KeyPath $acl
    Write-Host "✓ 继承已禁用" -ForegroundColor Green
} catch {
    Write-Host "❌ 禁用继承失败: $_" -ForegroundColor Red
    Read-Host "按Enter键退出"
    exit 1
}
Write-Host ""

Write-Host "步骤 3/5: 移除所有现有访问规则..." -ForegroundColor Yellow
Write-Host "----------------------------------------"
$acl = Get-Acl $KeyPath
foreach ($access in $acl.Access) {
    try {
        $acl.RemoveAccessRule($access)
    } catch {
        Write-Host "警告: 无法移除规则: $($access.IdentityReference)" -ForegroundColor Yellow
    }
}
Set-Acl $KeyPath $acl
Write-Host "✓ 所有现有规则已移除" -ForegroundColor Green
Write-Host ""

Write-Host "步骤 4/5: 只授予当前用户完全控制权限..." -ForegroundColor Yellow
Write-Host "----------------------------------------"
$acl = Get-Acl $KeyPath
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $currentUser,
    [System.Security.AccessControl.FileSystemRights]::FullControl,
    [System.Security.AccessControl.InheritanceFlags]::None,
    [System.Security.AccessControl.PropagationFlags]::None,
    [System.Security.AccessControl.AccessControlType]::Allow
)
$acl.SetAccessRule($accessRule)
Set-Acl $KeyPath $acl
Write-Host "✓ 已授予 $currentUser 完全控制权限" -ForegroundColor Green
Write-Host ""

Write-Host "步骤 5/5: 验证修复结果..." -ForegroundColor Yellow
Write-Host "----------------------------------------"
$acl = Get-Acl $KeyPath
Write-Host "当前权限:" -ForegroundColor Cyan
$acl.Access | Format-Table -AutoSize
Write-Host ""

# 验证只有当前用户有权限
$accessCount = ($acl.Access | Measure-Object).Count
if ($accessCount -eq 1 -and $acl.Access.IdentityReference.Value -eq $currentUser) {
    Write-Host "✓ 权限配置正确！" -ForegroundColor Green
} else {
    Write-Host "⚠ 警告: 权限配置可能不正确" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   权限修复完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "现在测试SSH连接:" -ForegroundColor Cyan
Write-Host ""
Write-Host "ssh -i '$KeyPath' root@8.163.37.124 'echo 连接成功！'" -ForegroundColor Yellow
Write-Host ""

Read-Host "按Enter键退出"