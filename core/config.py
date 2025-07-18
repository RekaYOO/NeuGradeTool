import json
import os
from typing import Dict, Any, Optional

class Config:
    """配置管理类"""
    
    def __init__(self, config_path: str = "config/config.json"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self._config_data = None
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config_data = json.load(f)
                
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise RuntimeError(f"加载配置文件失败: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键如 'database.host'
            default: 默认值
            
        Returns:
            配置值
        """
        if self._config_data is None:
            return default
        
        keys = key.split('.')
        value = self._config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_credentials(self) -> Dict[str, str]:
        """
        获取登录凭据
        
        Returns:
            包含用户名和密码的字典

        预留为了增加安全防护的修改。
        """
        username = self.get('auth.username')
        password = self.get('auth.password')
        
        if not username or not password:
            raise ValueError("配置文件中缺少用户名或密码")
        
        return {
            'username': username,
            'password': password
        }
    
    def get_output_dir(self) -> str:
        """获取输出目录"""
        return self.get('output.directory', 'output')