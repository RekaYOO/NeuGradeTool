import logging
from typing import Dict, Any
from bs4 import BeautifulSoup
from requests import Session
from .neu_login import NEULoginError, BackendError


class NEUGradeService:
    """NEU成绩获取服务"""
    
    def __init__(self, session: Session):
        """
        初始化成绩获取服务
        
        Args:
            session: 已认证的会话对象
        """
        self.session = session
    
    def get_grades(self, project_type: str = "MAJOR") -> Dict[str, Any]:
        """
        获取学生成绩信息
        
        Args:
            project_type: 项目类型，默认为"MAJOR"（主修）
            
        Returns:
            包含成绩信息的字典，包括总平均绩点和课程列表
        """
        try:
            # 构造成绩查询URL
            grades_url = f"http://219.216.96.4/eams/teach/grade/course/person!historyCourseGrade.action?projectType={project_type}"
            
            # 设置请求头
            headers = {
                "Accept": "*/*",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "http://219.216.96.4",
                "Referer": "http://219.216.96.4/eams/teach/grade/course/person!search.action?semesterId=111&projectType=",
                "Content-Length": "0"
            }
            
            # 发送POST请求获取成绩数据
            response = self.session.post(grades_url, headers=headers)
            
            if response.status_code != 200:
                raise BackendError(f"获取成绩失败，状态码: {response.status_code}")
            
            # 解析HTML响应
            return self._parse_grades_response(response.text)
            
        except Exception as e:
            if isinstance(e, NEULoginError):
                raise
            else:
                raise BackendError(f"获取成绩时发生异常: {str(e)}")

    def _parse_grades_response(self, html_content: str) -> Dict[str, Any]:
        """解析成绩页面响应"""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # 查找成绩表格
            table = soup.find("table", {"class": "gridtable"})
            if not table:
                raise BackendError("未找到成绩表格")
            
            # 解析表头
            header_row = table.find("tr")
            if not header_row:
                raise BackendError("未找到表头")
            
            headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
            
            # 解析数据行
            courses = []
            data_rows = table.find_all("tr")[1:]  # 跳过表头
            
            # 查找总平均绩点
            total_gpa = 0.0
            gpa_text = soup.find(string=lambda text: text and "总平均绩点" in text)
            if gpa_text:
                try:
                    # 提取绩点数值
                    import re
                    gpa_match = re.search(r'总平均绩点[：:]\s*([\d.]+)', gpa_text)
                    if gpa_match:
                        total_gpa = float(gpa_match.group(1))
                except (ValueError, AttributeError):
                    pass
            
            for row in data_rows:
                cells = row.find_all(["td", "th"])
                if len(cells) >= len(headers):
                    course_data = {}
                    for i, header in enumerate(headers):
                        if i < len(cells):
                            cell_text = cells[i].get_text(strip=True)
                            course_data[header] = cell_text
                    
                    # 处理学分数值
                    if "学分" in course_data and course_data["学分"]:
                        try:
                            if course_data["学分"].replace('.', '').isdigit():
                                course_data["学分"] = float(course_data["学分"])
                        except ValueError:
                            pass
                    
                    # 处理绩点数值
                    if "绩点" in course_data and course_data["绩点"]:
                        try:
                            if course_data["绩点"].replace('.', '').isdigit():
                                course_data["绩点"] = float(course_data["绩点"])
                        except ValueError:
                            pass
                    
                    # 处理成绩数值
                    for grade_field in ["平时成绩", "期中成绩", "期末成绩", "总评成绩", "最终"]:
                        if grade_field in course_data and course_data[grade_field]:
                            try:
                                # 尝试转换为数值
                                if course_data[grade_field].replace('.', '').isdigit():
                                    course_data[grade_field] = float(course_data[grade_field])
                            except ValueError:
                                pass
                    
                    courses.append(course_data)
        
            return {
                "success": True,
                "total_gpa": total_gpa,
                "course_count": len(courses),
                "courses": courses,
                "headers": headers
            }
            
        except Exception as e:
            if isinstance(e, NEULoginError):
                raise
            else:
                raise BackendError(f"解析成绩数据时发生异常: {str(e)}")