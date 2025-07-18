import os
import csv
import logging
from datetime import datetime
from core.neu_login import NEULogin, UnionAuthError, BackendError
from core.neu_get_plan import NEUPlanService
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
            logging.FileHandler('logs/Plan.log', encoding='utf-8'),
        ]
    )

def ensure_output_directory(output_dir: str):
    """确保输出目录存在"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logging.info(f"创建输出目录: {output_dir}")

def save_plan_to_csv(plan_data: dict, output_path: str):
    """
    将培养计划数据保存为CSV文件
    
    Args:
        plan_data: 培养计划数据字典
        output_path: 输出文件路径
    """
    if not plan_data.get('courses'):
        logging.warning("没有培养计划数据可保存")
        return
    
    courses = plan_data['courses']
    headers = plan_data.get('headers', [])
    
    # 如果没有表头，从第一条记录中获取
    if not headers and courses:
        headers = list(courses[0].keys())
    
    try:
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(courses)
        
        logging.info(f"培养计划数据已保存到: {output_path}")
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
        service_url = config.get('service_data.JiaoWuURL')
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
        
        # 创建培养计划服务对象
        plan_service = NEUPlanService(neu_login.get_session())
        
        # 获取培养计划ID（从配置或用户输入）
        plan_id = config.get("service_data.plan_id", "4068")  # 默认使用4068
        
        # 获取培养计划信息
        logging.info("获取培养计划信息...")
        logging.info(f"培养计划ID: {plan_id}")
        plan_result = plan_service.get_plan(plan_id, max_retries=8, wait_time=3)
        
        if plan_result['success']:
            logging.info(f"培养计划获取成功: 共{plan_result['course_count']}门课程")
            
            # 生成输出文件名
            output_path = os.path.join(output_dir, "plan.csv")
            
            # 保存培养计划数据到CSV
            save_plan_to_csv(plan_result, output_path)
            
        else:
            logging.error("获取培养计划失败")
            
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




