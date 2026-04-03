#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码加密混淆器 - 保护上传工具不被破解

使用方法:
python obfuscator.py --input main.py --output main_obfuscated.py
"""

import os
import sys
import re
import random
import string
import base64
import hashlib
import marshal
import types
import zlib
from pathlib import Path
from typing import Dict, Set, List


class CodeObfuscator:
    """代码混淆器 - 多层保护"""
    
    def __init__(self, seed: str = None):
        self.seed = seed or ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        self.random = random.Random(self.seed)
        self.name_map: Dict[str, str] = {}
        self.used_names: Set[str] = set()
        
    def _generate_random_name(self, prefix: str = '_') -> str:
        """生成随机变量名"""
        while True:
            length = self.random.randint(12, 24)
            name = prefix + ''.join(self.random.choices(string.ascii_letters + string.digits, k=length))
            if name not in self.used_names:
                self.used_names.add(name)
                return name
    
    def _encrypt_string(self, s: str) -> str:
        """XOR加密字符串"""
        key = self.seed.encode('utf-8')
        data = s.encode('utf-8')
        encrypted = bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])
        return base64.b64encode(encrypted).decode('ascii')
    
    def obfuscate_variables(self, code: str) -> str:
        """混淆变量名"""
        # 保护的关键字和内置函数
        protected = {
            'self', 'cls', 'super', 'object', 'type', 'str', 'int', 'float', 'list', 'dict',
            'set', 'tuple', 'bool', 'None', 'True', 'False', 'import', 'from', 'as',
            'def', 'class', 'return', 'yield', 'if', 'elif', 'else', 'for', 'while',
            'try', 'except', 'finally', 'with', 'async', 'await', 'lambda', 'pass',
            'break', 'continue', 'raise', 'assert', 'del', 'global', 'nonlocal',
            'print', 'input', 'open', 'range', 'len', 'enumerate', 'zip', 'map', 'filter',
            '__init__', '__main__', '__name__', '__file__', '__doc__', '__module__',
            'QApplication', 'QMainWindow', 'QWidget', 'QThread', 'pyqtSignal'
        }
        
        # 找到所有变量名、函数名、类名
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b'
        matches = list(re.finditer(pattern, code))
        
        # 从后往前替换，避免位置偏移
        for match in reversed(matches):
            name = match.group(1)
            if name in protected:
                continue
            if name.startswith('__') and name.endswith('__'):
                continue  # 保护魔术方法
            if name.startswith('Qt') or name.startswith('Q'):
                continue  # 保护Qt类名
                
            # 生成混淆名
            if name not in self.name_map:
                self.name_map[name] = self._generate_random_name()
            
            start, end = match.span()
            code = code[:start] + self.name_map[name] + code[end:]
        
        return code
    
    def remove_comments_and_docstrings(self, code: str) -> str:
        """移除注释和文档字符串"""
        # 移除单行注释
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        
        # 移除多行字符串（文档字符串）
        # 注意：保留代码中实际使用的多行字符串
        lines = code.split('\n')
        result = []
        in_docstring = False
        docstring_quote = None
        
        for line in lines:
            stripped = line.strip()
            
            # 检测文档字符串开始
            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    quote = stripped[:3]
                    # 检查是否在同一行结束
                    if stripped.count(quote) >= 2:
                        # 单行文档字符串，移除
                        continue
                    else:
                        in_docstring = True
                        docstring_quote = quote
                        continue
            else:
                # 检测文档字符串结束
                if docstring_quote in line:
                    in_docstring = False
                    docstring_quote = None
                    continue
                else:
                    continue
            
            # 保留代码行
            if line.strip():
                result.append(line)
        
        return '\n'.join(result)
    
    def add_anti_debug(self, code: str) -> str:
        """添加反调试代码"""
        anti_debug_code = '''
import sys
import os
import time

# 反调试检查
if sys.gettrace() is not None:
    os._exit(1)

# 检查是否在虚拟机中
try:
    import ctypes
    if ctypes.windll.kernel32.IsDebuggerPresent():
        os._exit(1)
except:
    pass

# 延迟执行（防止动态分析）
_''' + self._generate_random_name() + ''' = 0.001
for _''' + self._generate_random_name() + ''' in range(10):
    time.sleep(_''' + self._generate_random_name() + ''')

'''
        return anti_debug_code + code
    
    def encrypt_config_section(self, config: dict) -> str:
        """加密配置段"""
        config_str = str(config)
        encrypted = self._encrypt_string(config_str)
        
        code = f'''
# 加密配置
_''' + self._generate_random_name() + ''' = "''' + encrypted + '''"
_''' + self._generate_random_name() + ''' = "''' + self.seed + '''"

def _''' + self._generate_random_name() + '''(e, k):
    import base64
    b = base64.b64decode(e)
    kb = k.encode('utf-8')
    return eval(bytes([b[i] ^ kb[i % len(kb)] for i in range(len(b))]).decode('utf-8'))

_''' + self._generate_random_name() + ''' = _''' + self._generate_random_name() + '''(_''' + self._generate_random_name() + ''', _''' + self._generate_random_name() + ''')
'''
        return code
    
    def obfuscate(self, input_file: str, output_file: str) -> bool:
        """执行完整混淆流程"""
        try:
            # 读取源码
            with open(input_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            print(f"[1/5] 读取源文件: {input_file}")
            
            # 1. 移除注释
            code = self.remove_comments_and_docstrings(code)
            print("[2/5] 移除注释和文档字符串")
            
            # 2. 混淆变量名
            code = self.obfuscate_variables(code)
            print(f"[3/5] 混淆变量名 ({len(self.name_map)} 个名称)")
            
            # 3. 添加反调试
            code = self.add_anti_debug(code)
            print("[4/5] 添加反调试代码")
            
            # 4. 添加保护头
            header = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Protected by CodeObfuscator
# Seed: {self.seed}
# Hash: {hashlib.sha256(code.encode()).hexdigest()[:16]}
# Do Not Modify

'''
            code = header + code
            
            # 5. 写入文件
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(code)
            print(f"[5/5] 输出到: {output_file}")
            
            return True
            
        except Exception as e:
            print(f"❌ 混淆失败: {e}")
            return False


class BytecodeEncryptor:
    """字节码加密器 - 将Python代码编译为加密字节码"""
    
    @staticmethod
    def encrypt_to_pyc(input_file: str, output_file: str) -> bool:
        """
        将Python文件编译为加密的pyc文件
        注意：这种方式保护强度更高，但可能有兼容性问题
        """
        try:
            # 读取源码
            with open(input_file, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # 编译为字节码
            code_obj = compile(source, input_file, 'exec')
            
            # 序列化并压缩
            marshaled = marshal.dumps(code_obj)
            compressed = zlib.compress(marshaled, level=9)
            
            # 加密（简单XOR）
            key = b'XSDM2024'
            encrypted = bytes([compressed[i] ^ key[i % len(key)] for i in range(len(compressed))])
            
            # 包装为可执行代码
            wrapper = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import marshal
import zlib
_key = {key}
_encrypted = {encrypted}
_decrypted = bytes([_encrypted[i] ^ _key[i % len(_key)] for i in range(len(_encrypted))])
_decompressed = zlib.decompress(_decrypted)
_code = marshal.loads(_decompressed)
exec(_code)
'''
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(wrapper)
            
            return True
            
        except Exception as e:
            print(f"❌ 字节码加密失败: {e}")
            return False


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='代码加密混淆工具')
    parser.add_argument('--input', '-i', required=True, help='输入文件')
    parser.add_argument('--output', '-o', help='输出文件')
    parser.add_argument('--mode', '-m', choices=['obfuscate', 'bytecode', 'both'], 
                        default='obfuscate', help='加密模式')
    parser.add_argument('--seed', '-s', help='随机种子（用于重现）')
    
    args = parser.parse_args()
    
    if not args.output:
        base, ext = os.path.splitext(args.input)
        args.output = f"{base}_protected{ext}"
    
    print("=" * 60)
    print("代码加密混淆器")
    print("=" * 60)
    print()
    
    if args.mode in ['obfuscate', 'both']:
        print("【模式1】代码混淆")
        obfuscator = CodeObfuscator(seed=args.seed)
        if obfuscator.obfuscate(args.input, args.output):
            print(f"✅ 混淆完成: {args.output}")
        print()
    
    if args.mode in ['bytecode', 'both']:
        print("【模式2】字节码加密")
        output_bytecode = args.output.replace('.py', '_bytecode.py')
        if BytecodeEncryptor.encrypt_to_pyc(args.input, output_bytecode):
            print(f"✅ 字节码加密完成: {output_bytecode}")
        print()
    
    print("=" * 60)
    print("加密完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
