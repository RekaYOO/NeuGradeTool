# NEU 成绩查询系统

东北大学教务系统成绩查询和监控工具，支持一次性查询和自动监控功能。

## 系统要求

- **Python**: 3.8+
- **操作系统**: Windows / macOS / Linux

## 功能特性

- **成绩查询**：一次性获取所有成绩信息
- **邮件通知**：成绩更新时自动发送邮件提醒
- **定时监控**：支持频繁查询和冷查询两个时段
- **数据导出**：成绩数据保存为CSV格式

## 快速开始

### 1. 环境准备

确保已安装 Python 3.8+，然后安装依赖：

```bash
# 使用 pip 安装依赖
pip install -r requirements.txt

# 或者手动安装
pip install requests>=2.25.1 beautifulsoup4>=4.9.3 lxml>=4.6.3
```

### 2. 配置设置

复制配置模板并填入个人信息：

```bash
cp config/config.json.example config/config.json
```

编辑 `config/config.json`：

```json
{
    "auth": {
        "username": "你的学号",
        "password": "你的密码"
    },
    "output": {
        "directory": "output",
        "grades_filename": "grades.csv"
    },
    "neu_login": {
        "service_url": "http://219.216.96.4/eams/homeExt.action",
        "bypass_proxy": false
    },
    "email": {
        "smtp_server": "smtp.qq.com",
        "smtp_port": 587,
        "sender_email": "发送方邮箱@qq.com",
        "sender_password": "邮箱授权码",
        "recipient_email": "接收方邮箱@example.com"
    },
    "auto": {
        "frequent_period": {
            "start_time": "08:00",
            "end_time": "22:00",
            "interval": 1800
        },
        "cold_period": {
            "start_time": "22:00",
            "end_time": "08:00",
            "interval": 7200
        }
    }
}
```

**时段配置说明：**
- `frequent_period`: 频繁查询时段（如白天），默认8:00-22:00，每30分钟检查一次
- `cold_period`: 冷查询时段（如夜间），默认22:00-8:00，每2小时检查一次
- `interval`: 检查间隔，单位为秒

## 使用方法

### 一次性查询成绩 (Grade.py)

获取当前所有成绩并保存到CSV文件：

```bash
python app.py
```

**功能说明：**
- 登录教务系统获取成绩
- 自动计算总平均绩点
- 保存成绩到 `output/grades.csv`
- 显示详细的成绩信息和日志

### 自动监控成绩 (AutoGrade.py)

后台持续监控成绩变化：

```bash
pythow Auto.py
```

或

```bash
nohup python3 Auto.py > Auto.out 2>&1 &
```

**功能说明：**
- 智能定时检查成绩更新（根据时段自动调整频率）
- 对比成绩变化，发现新增或修改
- 成绩有变化时自动发送邮件通知
- 使用固定文件名保存最新成绩
- 记录监控日志到 `logs/Auto.log`

**邮件通知内容：**
- 平均绩点变化对比
- 新增课程详情
- 成绩更新详情

### 获取培养计划 (Plan.py)

获取培养计划并保存到CSV文件：

```bash
python Plan.py
```

**注意你需要提前在教务系统中找到你的专业培养计划的序号：majorPlan.id=XXXX 然后将序号填入config.json中**

### 成绩计算器 (Calc.py)

图形化成绩管理和GPA计算工具：
（需要完整的Core、Grade.py、Plan.py）

```bash
python Calc.py
```

**功能特性：**
- **可视化界面**：直观的图形化操作界面
- **预估和模拟成绩**：快速读取已有成绩、培养计划、快速添加课程信息，自动计算
- **GPA分析**：实时计算总平均学分绩和单科影响
- **数据排序**：支持按绩点、学分、GPA影响等排序
- **文件操作**：读取/保存成绩数据，支持CSV格式

**部分操作说明：**
- **获取数据**：点击"获取成绩"/"获取计划"按钮自动完成，建议先获取成绩再获取培养计划
- **读取文件**：点击"读取成绩文件"/"读取计划文件"加载本地CSV文件

- **编辑成绩**：双击表格中的课程可编辑绩点
- **牌路**：点击列标题进行排序分析


**使用场景：**
- 模拟选课对GPA的影响
- 分析各科成绩贡献度
- 规划学习重点
- ...

## 依赖库说明

| 库名 | 版本要求 | 用途 |
|------|----------|------|
| requests | >=2.25.1 | HTTP请求处理 |
| beautifulsoup4 | >=4.9.3 | HTML解析 |
| lxml | >=4.6.3 | XML/HTML解析器 |

## 输出文件

- `output/grades.csv` - 最新成绩数据（Auto.py使用）
- `output/plan.csv` - 培养计划数据
- `logs/Grade.log` - Grade.py运行日志
- `logs/AutoGrade.log` - AutoGrade.py监控日志
- `logs/Plan.log` -Plan.py日志

## 注意事项

1. **邮箱配置**：使用QQ邮箱需要开启SMTP服务并使用授权码
2. **网络环境**：确保能够访问东北大学教务系统
3. **账号安全**：配置文件包含敏感信息，请妥善保管
4. **监控频率**：建议检查间隔不要设置过短，避免对服务器造成压力

## 故障排除

- **登录失败**：检查用户名密码是否正确
- **邮件发送失败**：检查邮箱配置和网络连接
- **文件权限错误**：确保程序有读写权限
- **依赖库错误**：运行 `pip install -r requirements.txt` 重新安装

## 许可证

本项目仅供学习交流使用，请遵守学校相关规定。

