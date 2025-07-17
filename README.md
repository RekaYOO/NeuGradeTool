# NEU 成绩查询系统

东北大学教务系统成绩查询和监控工具，支持一次性查询和自动监控功能。

## 系统要求

- **Python**: 3.8+
- **操作系统**: Windows / macOS / Linux

## 功能特性

- **成绩查询**：一次性获取所有成绩信息
- **GPA计算**：自动计算总平均绩点
- **邮件通知**：成绩更新时自动发送邮件提醒
- **定时监控**：后台持续监控成绩变化
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


## 使用方法

### 一次性查询 (app.py)

获取当前所有成绩并保存到CSV文件：

```bash
python app.py
```

**功能说明：**
- 登录教务系统获取成绩
- 自动计算总平均绩点
- 保存成绩到 `output/grades.csv`
- 显示详细的成绩信息和日志

### 自动监控 (Auto.py)

后台持续监控成绩变化：

windows下
```powershell
pythonw Auto.py
```
linux下
```bash
nohup python -u Auto.py > Auto.out 2>&1 &
```


**功能说明：**
- 定时检查成绩更新（默认1小时）
- 对比成绩变化，发现新增或修改
- 成绩有变化时自动发送邮件通知
- 使用固定文件名保存最新成绩
- 记录监控日志到 `logs/Auto.log`

**邮件通知内容：**
- 平均绩点变化对比
- 新增课程详情
- 成绩更新详情

## 依赖库说明

| 库名 | 版本要求 | 用途 |
|------|----------|------|
| requests | >=2.25.1 | HTTP请求处理 |
| beautifulsoup4 | >=4.9.3 | HTML解析 |
| lxml | >=4.6.3 | XML/HTML解析器 |

## 输出文件

- `output/grades.csv` - 最新成绩数据（Auto.py使用）
- `logs/App.log` - App.py运行日志
- `logs/Auto.log` - Auto.py监控日志

