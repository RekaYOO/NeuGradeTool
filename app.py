import os
import csv
import logging
from datetime import datetime
from core.neu_login import NEULogin, UnionAuthError, BackendError
from core.config import Config

def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def ensure_output_directory(output_dir: str):
    """确保输出目录存在"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"创建输出目录: {output_dir}")

def save_grades_to_csv(grades_data: dict, output_path: str):
    """
    将成绩数据保存为CSV文件
    
    Args:
        grades_data: 成绩数据字典
        output_path: 输出文件路径
    """
    if not grades_data.get('courses'):
        logging.warning("没有成绩数据可保存")
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
        
        logging.info(f"成绩数据已保存到: {output_path}")
        logging.info(f"共保存 {len(courses)} 条记录")
        
    except Exception as e:
        logging.error(f"保存CSV文件失败: {e}")
        raise

def main():
    """主函数"""
    setup_logging()
    
    try:
        # 加载配置
        config = Config()
        credentials = config.get_credentials()
        output_dir = config.get_output_dir()
        
        # 确保输出目录存在
        ensure_output_directory(output_dir)
        
        # 创建登录对象
        service_url = config.get('neu_login.service_url')
        bypass_proxy = config.get('neu_login.bypass_proxy', False)
        neu_login = NEULogin(service_url=service_url, bypass_proxy=bypass_proxy)
        
        logging.info("开始登录认证...")
        
        # 执行认证
        auth_result = neu_login.authenticate(
            credentials['username'], 
            credentials['password']
        )
        logging.info("认证成功")
        
        # 访问教务系统
        logging.info("访问教务系统...")
        service_result = neu_login.access_service()
        logging.info(f"访问教务系统成功: {service_result['url']}")
        
        # 获取成绩信息
        logging.info("获取成绩信息...")
        grades_result = neu_login.get_grades()
        
        if grades_result['success']:
            logging.info(f"成绩获取成功: 共{grades_result['course_count']}门课程")
            if grades_result.get('total_gpa'):
                logging.info(f"总平均绩点: {grades_result['total_gpa']}")
            
            # 生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = config.get('output.grades_filename', 'grades.csv')
            name, ext = os.path.splitext(filename)
            output_filename = f"{name}_{timestamp}{ext}"
            output_path = os.path.join(output_dir, output_filename)
            
            # 保存成绩数据到CSV
            save_grades_to_csv(grades_result, output_path)
            
        else:
            logging.error("获取成绩失败")
            
    except UnionAuthError as e:
        logging.error(f"用户名或密码错误: {e}")
    except BackendError as e:
        logging.error(f"后端错误: {e}")
    except FileNotFoundError as e:
        logging.error(f"文件不存在: {e}")
        logging.info("请确保config/config.json文件存在并配置正确的用户名和密码")
    except ValueError as e:
        logging.error(f"配置错误: {e}")
    except Exception as e:
        logging.error(f"程序执行出错: {e}")
        import traceback
        logging.debug(traceback.format_exc())

if __name__ == "__main__":
    main()