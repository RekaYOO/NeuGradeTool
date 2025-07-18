import os
import csv
import json
import time
import smtplib
import logging
from datetime import datetime, time as dt_time, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.neu_login import NEULogin, UnionAuthError, BackendError
from core.neu_get_grade import NEUGradeService
from core.config import Config

def setup_logging():
    """设置日志"""
    # 确保logs目录存在
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/Auto.log', encoding='utf-8'),
        ]
    )

def ensure_output_directory(output_dir: str):
    """确保输出目录存在"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

def calculate_gpa(courses: list) -> float:
    """
    计算总平均绩点
    
    Args:
        courses: 课程列表
        
    Returns:
        总平均绩点
    """
    total_credits = 0.0
    total_grade_points = 0.0
    
    for course in courses:
        try:
            # 获取学分
            credits = course.get('学分')
            if credits is None or credits == '':
                continue
            
            # 转换学分为浮点数
            if isinstance(credits, str):
                credits = float(credits)
            elif not isinstance(credits, (int, float)):
                continue
            
            # 获取绩点
            gpa = course.get('绩点')
            if gpa is None or gpa == '':
                continue
            
            # 转换绩点为浮点数
            if isinstance(gpa, str):
                gpa = float(gpa)
            elif not isinstance(gpa, (int, float)):
                continue
            
            # 累加计算
            total_credits += credits
            total_grade_points += credits * gpa
            
        except (ValueError, TypeError):
            # 跳过无法转换的数据
            continue
    
    # 计算平均绩点
    if total_credits > 0:
        return round(total_grade_points / total_credits, 2)
    else:
        return 0.0

def load_previous_grades(file_path: str) -> dict:
    """加载之前的成绩数据"""
    if not os.path.exists(file_path):
        return {"courses": [], "gpa": 0.0}
    
    try:
        courses = []
        with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # 转换数值字段
                for field in ['学分', '绩点']:
                    if field in row and row[field]:
                        try:
                            row[field] = float(row[field])
                        except ValueError:
                            pass
                courses.append(row)
        
        gpa = calculate_gpa(courses)
        return {"courses": courses, "gpa": gpa}
    except Exception as e:
        print(f"加载之前成绩数据失败: {e}")
        return {"courses": [], "gpa": 0.0}

def save_grades_to_csv(grades_data: dict, output_path: str):
    """将成绩数据保存为CSV文件"""
    if not grades_data.get('courses'):
        print("没有成绩数据可保存")
        return
    
    courses = grades_data['courses']
    headers = grades_data.get('headers', [])
    
    # 如果没有表头，从第一条记录中获取
    if not headers and courses:
        headers = list(courses[0].keys())
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(courses)
        
        print(f"成绩数据已保存到: {output_path}")
        
    except Exception as e:
        print(f"保存CSV文件失败: {e}")
        raise

def find_grade_differences(old_courses: list, new_courses: list) -> list:
    """查找成绩变化"""
    differences = []
    
    # 创建旧成绩的索引
    old_courses_dict = {}
    for course in old_courses:
        key = f"{course.get('课程名称', '')}-{course.get('学年学期', '')}"
        old_courses_dict[key] = course
    
    # 检查新成绩
    for new_course in new_courses:
        key = f"{new_course.get('课程名称', '')}-{new_course.get('学年学期', '')}"
        
        if key not in old_courses_dict:
            # 新增课程
            differences.append({
                "type": "新增课程",
                "course_name": new_course.get('课程名称', '未知'),
                "data": new_course
            })
        else:
            # 检查成绩是否有变化
            old_course = old_courses_dict[key]
            for field in ['最终', '总评成绩', '绩点']:
                if field in new_course and field in old_course:
                    if str(new_course[field]) != str(old_course[field]):
                        differences.append({
                            "type": "成绩更新",
                            "course_name": new_course.get('课程名称', '未知'),
                            "field": field,
                            "old_value": old_course[field],
                            "new_value": new_course[field]
                        })
    
    return differences

def send_email(config: Config, differences: list, old_gpa: float, new_gpa: float):
    """发送邮件通知"""
    try:
        # 获取邮件配置
        smtp_server = config.get('email.smtp_server')
        smtp_port = config.get('email.smtp_port', 587)
        sender_email = config.get('email.sender_email')
        sender_password = config.get('email.sender_password')
        recipient_email = config.get('email.recipient_email')
        
        if not all([smtp_server, sender_email, sender_password, recipient_email]):
            print("邮件配置不完整，跳过发送")
            return
        
        # 创建邮件内容
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"成绩更新通知 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # 构建邮件正文
        body = f"""
成绩更新通知

平均绩点变化: {old_gpa} → {new_gpa}
变化数量: {len(differences)} 项

详细变化:
"""
        
        for diff in differences:
            if diff['type'] == '新增课程':
                course = diff['data']
                body += f"\n【新增课程】{diff['course_name']}\n"
                body += f"  学分: {course.get('学分', '未知')}\n"
                body += f"  成绩: {course.get('最终', course.get('总评成绩', '未知'))}\n"
                body += f"  绩点: {course.get('绩点', '未知')}\n"
            
            elif diff['type'] == '成绩更新':
                body += f"\n【成绩更新】{diff['course_name']}\n"
                body += f"  {diff['field']}: {diff['old_value']} → {diff['new_value']}\n"
        
        body += f"\n\n此邮件由成绩监控系统自动发送"
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 发送邮件
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        print(f"邮件发送成功到: {recipient_email}")
        
    except Exception as e:
        print(f"发送邮件失败: {e}")

def get_current_check_interval(config: Config) -> tuple:
    """获取当前时段的检查间隔"""
    try:
        frequent_start = config.get('auto.frequent_period.start_time', '08:00')
        frequent_end = config.get('auto.frequent_period.end_time', '22:00')
        frequent_interval = config.get('auto.frequent_period.interval', 1800)
        cold_interval = config.get('auto.cold_period.interval', 7200)
        
        # 解析时间
        frequent_start_time = datetime.strptime(frequent_start, '%H:%M').time()
        frequent_end_time = datetime.strptime(frequent_end, '%H:%M').time()
        current_time = datetime.now().time()
        
        # 判断当前时间是否在频繁查询时段
        if frequent_start_time <= current_time <= frequent_end_time:
            return frequent_interval, "频繁查询时段"
        else:
            return cold_interval, "冷查询时段"
            
    except Exception as e:
        print(f"解析时间配置失败: {e}")
        return 1800, "默认时段"

def check_grades():
    """检查成绩更新"""
    try:
        # 加载配置
        config = Config()
        credentials = config.get_credentials()
        output_dir = config.get_output_dir()
        
        # 确保输出目录存在
        ensure_output_directory(output_dir)
        
        # 固定文件名
        filename = config.get('output.grades_filename', 'grades.csv')
        output_path = os.path.join(output_dir, filename)
        
        # 加载之前的成绩数据
        previous_data = load_previous_grades(output_path)
        
        # 创建登录对象
        service_url = config.get('neu_login.service_url')
        bypass_proxy = config.get('neu_login.bypass_proxy', False)
        neu_login = NEULogin(service_url=service_url, bypass_proxy=bypass_proxy)
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始检查成绩...")
        logging.info("开始检查成绩...")
        
        # 执行认证
        auth_result = neu_login.authenticate(
            credentials['username'], 
            credentials['password']
        )
        logging.info("认证成功")
        
        # 访问教务系统
        service_result = neu_login.access_service()
        
        # 创建成绩服务对象
        grade_service = NEUGradeService(neu_login.get_session())
        
        # 获取成绩信息
        grades_result = grade_service.get_grades()
        
        if grades_result['success']:
            current_gpa = calculate_gpa(grades_result['courses'])
            logging.info(f"成绩获取成功: 共{grades_result['course_count']}门课程, 当前GPA: {current_gpa}")
            
            # 检查是否有变化
            differences = find_grade_differences(previous_data['courses'], grades_result['courses'])
            
            if differences or abs(current_gpa - previous_data['gpa']) > 0.01:
                print(f"发现成绩更新! 共{len(differences)}项变化")
                print(f"GPA变化: {previous_data['gpa']} → {current_gpa}")
                logging.info(f"发现成绩更新! 共{len(differences)}项变化, GPA变化: {previous_data['gpa']} → {current_gpa}")
                
                # 保存新的成绩数据
                save_grades_to_csv(grades_result, output_path)
                
                # 发送邮件通知
                send_email(config, differences, previous_data['gpa'], current_gpa)
            else:
                print("成绩无变化")
                logging.info("成绩无变化")
        else:
            print("获取成绩失败")
            logging.error("获取成绩失败")
            
    except UnionAuthError as e:
        print(f"用户名或密码错误: {e}")
        logging.error(f"用户名或密码错误: {e}")
    except BackendError as e:
        print(f"后端错误: {e}")
        logging.error(f"后端错误: {e}")
    except Exception as e:
        print(f"检查成绩时出错: {e}")
        logging.error(f"检查成绩时出错: {e}")

def main():
    """主函数 - 定时检查成绩"""
    setup_logging()
    
    config = Config()
    
    print("成绩自动监控启动")
    logging.info("成绩自动监控启动")
    
    try:
        # 验证配置
        config.get_credentials()
        get_current_check_interval(config)
        
    except Exception as e:
        print(f"配置解析错误: {e}")
        logging.error(f"配置解析错误: {e}")
        return
    
    while True:
        try:
            # 获取当前时段的检查间隔
            current_interval, period_name = get_current_check_interval(config)
            
            print(f"当前处于{period_name}，检查间隔: {current_interval}秒")
            
            # 执行成绩检查
            check_grades()
            
            # 计算下次检查时间
            next_check_time = datetime.now() + timedelta(seconds=current_interval)
            next_check_display = next_check_time.replace(second=0, microsecond=0)
            
            print(f"下次检查时间: {next_check_display.strftime('%Y-%m-%d %H:%M:%S')}")
            
            time.sleep(current_interval)
            
        except KeyboardInterrupt:
            print("\n程序已停止")
            logging.info("程序已停止")
            break
        except Exception as e:
            print(f"程序异常: {e}")
            logging.error(f"程序异常: {e}")
            time.sleep(60)  # 出错后等待1分钟再重试

if __name__ == "__main__":
    main()





