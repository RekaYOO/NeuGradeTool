import logging
import time
from typing import Dict, Any
from bs4 import BeautifulSoup
from requests import Session
from .neu_login import NEULoginError, BackendError


class NEUPlanService:
    """NEU培养计划获取服务"""
    
    def __init__(self, session: Session):
        """
        初始化培养计划获取服务
        
        Args:
            session: 已认证的会话对象
        """
        self.session = session
    
    def get_plan(self, plan_id: str, max_retries: int = 5, wait_time: int = 2) -> Dict[str, Any]:
        """
        获取培养计划信息
        
        Args:
            plan_id: 培养计划ID
            max_retries: 最大重试次数
            wait_time: 每次重试间隔时间（秒）
            
        Returns:
            包含培养计划信息的字典
        """
        try:
            # 构造POST请求URL和数据
            target_url = "http://219.216.96.4/eams/studentMajorPlan!view.action"
            post_data = {"planId": plan_id}
            
            # 设置请求头
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "http://219.216.96.4",
                "Referer": "http://219.216.96.4/eams/studentMajorPlan!search.action",
                "Cache-Control": "max-age=0",
                "Upgrade-Insecure-Requests": "1",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
            }
            
            # 发送POST请求获取页面数据
            response = self.session.post(target_url, data=post_data, headers=headers)
            
            if response.status_code != 200:
                raise BackendError(f"获取培养计划失败，状态码: {response.status_code}")
            
            # 等待页面加载并重试解析
            for attempt in range(max_retries):
                logging.info(f"第 {attempt + 1} 次尝试解析页面...")
                
                if attempt > 0:
                    # 重新请求页面
                    time.sleep(wait_time)
                    response = self.session.post(target_url, data=post_data, headers=headers)
                    if response.status_code != 200:
                        raise BackendError(f"重新获取页面失败，状态码: {response.status_code}")
                
                try:
                    # 尝试解析HTML响应
                    result = self._parse_plan_response(response.text, attempt + 1)
                    if result['success'] and result['course_count'] > 0:
                        logging.info(f"成功解析页面，共找到 {result['course_count']} 门课程")
                        return result
                    else:
                        logging.warning(f"第 {attempt + 1} 次解析未找到课程数据")
                except Exception as parse_error:
                    error_msg = str(parse_error)
                    if ("未找到培养计划表格" in error_msg or "未找到包含'学时种类'的表格" in error_msg) and attempt < max_retries - 1:
                        logging.warning(f"第 {attempt + 1} 次解析失败: {parse_error}，等待 {wait_time} 秒后重试...")
                        continue
                    else:
                        # 如果是最后一次尝试或其他错误，直接抛出
                        raise parse_error
            
            raise BackendError(f"经过 {max_retries} 次尝试仍未能获取到培养计划数据")
            
        except Exception as e:
            if isinstance(e, NEULoginError):
                raise
            else:
                raise BackendError(f"获取培养计划时发生异常: {str(e)}")

    def _parse_plan_response(self, html_content: str, attempt: int = 1) -> Dict[str, Any]:
        """解析培养计划页面响应"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # 查找所有class="planTable"的表格
            plan_tables = soup.find_all("table", {"class": "planTable"})
            
            if not plan_tables:
                raise BackendError("未找到培养计划表格")
            
            # 筛选包含"学时种类"的表格
            target_table = None
            for i, table in enumerate(plan_tables):
                table_text = table.get_text()
                if "学时种类" in table_text:
                    target_table = table
                    break
            
            if not target_table:
                raise BackendError("未找到包含'学时种类'的表格")
            
            # 获取tbody
            tbody = target_table.find("tbody")
            if not tbody:
                raise BackendError("未找到表格tbody")
            
            # 获取所有tr
            all_rows = tbody.find_all("tr")
            
            # 移除包含rowspan参数的td的tr
            filtered_rows = []
            for row in all_rows:
                has_rowspan = False
                for td in row.find_all("td"):
                    if td.get("rowspan"):
                        has_rowspan = True
                        break
                if not has_rowspan:
                    filtered_rows.append(row)
            
            # 解析数据
            courses = []
            for row in filtered_rows:
                cells = row.find_all("td")
                if len(cells) >= 12:  # 确保有足够的列
                    # 移除第1列"序号"，移除5列"学时种类"（假设在第5-9列）
                    course_data = {
                        "课程序号": cells[1].get_text(strip=True),
                        "课程名称": cells[2].get_text(strip=True),
                        "课程学时": cells[3].get_text(strip=True),
                        "学分数": cells[9].get_text(strip=True),
                        "周学时": cells[10].get_text(strip=True),
                        "考试或考查课": cells[11].get_text(strip=True),
                        "课程类型": cells[12].get_text(strip=True) if len(cells) > 12 else "",
                        "课群": cells[13].get_text(strip=True) if len(cells) > 13 else "",
                        "成绩记载方式": cells[14].get_text(strip=True) if len(cells) > 14 else ""
                    }
                    
                    # 处理数值字段
                    for field in ["课程学时", "学分数", "周学时"]:
                        if field in course_data and course_data[field]:
                            try:
                                if course_data[field].replace('.', '').isdigit():
                                    course_data[field] = float(course_data[field])
                            except ValueError:
                                pass
                    
                    courses.append(course_data)
            
            return {
                "success": True,
                "course_count": len(courses),
                "courses": courses,
                "headers": ["课程序号", "课程名称", "课程学时", "学分数", "周学时", "考试或考查课", "课程类型", "课群", "成绩记载方式"]
            }
            
        except Exception as e:
            if isinstance(e, NEULoginError):
                raise
            else:
                raise BackendError(f"解析培养计划数据时发生异常: {str(e)}")

