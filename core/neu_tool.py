import logging
from typing import Optional, Dict, Any
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag
from requests import Session


class NEULoginError(Exception):
    """NEU登录基础异常"""
    pass


class UnionAuthError(NEULoginError):
    """用户名或密码错误"""
    pass


class BackendError(NEULoginError):
    """后端服务异常"""
    def __init__(self, page_content: str):
        self.page_content = page_content
        super().__init__("后端服务异常")


class NEUTool:
    """工具包"""
    
    def __init__(self, service_url: Optional[str] = None, bypass_proxy: bool = False):
        """
        初始化NEU登录
        
        Args:
            service_url: 目标服务URL
            bypass_proxy: 是否跳过系统代理
        """
        self.service_url = service_url
        self.session = self._prepare_session(bypass_proxy)
        
    def _prepare_session(self, bypass_proxy: bool) -> Session:
        """准备会话"""
        sess = Session()
        sess.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
            "Accept": "application/json",
            "Accept-Language": "zh-CN",
            "Accept-Encoding": "gzip, deflate",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive"
        })
        
        if bypass_proxy:
            sess.trust_env = False
        return sess
    
    def get_session(self) -> Session:
        """获取当前会话对象"""
        return self.session
    
    def authenticate(self, username: str, password: str) -> Dict[str, Any]:
        """
        执行认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            认证结果字典，包含ticket和cookies
        """
        # 使用空服务URL创建认证请求
        auth_url = "https://pass.neu.edu.cn/tpass/login"
        
        try:
            # 获取登录表单数据
            response = self.session.get(auth_url)
            page_soup = BeautifulSoup(response.text, "html.parser")
            form: Tag = page_soup.find("form", {'id': 'loginForm'})
            
            if not form:
                raise BackendError("无法找到登录表单")
                
            form_data = {
                "form_lt_string": form.find("input", {'id': 'lt'}).attrs["value"],
                "form_destination": form.attrs['action'],
                "form_execution": form.find("input", {'name': 'execution'}).attrs["value"]
            }
            
            # 构造登录数据
            login_data = {
                'rsa': username + password + form_data['form_lt_string'],
                'ul': len(username),
                'pl': len(password),
                'lt': form_data['form_lt_string'],
                'execution': form_data['form_execution'],
                '_eventId': 'submit'
            }
            
            # 提交登录请求，但不允许重定向
            response = self.session.post(
                "https://pass.neu.edu.cn" + form_data['form_destination'],
                data=login_data,
                allow_redirects=False
            )
            
            # 检查是否认证成功（通常会返回302重定向）
            if response.status_code == 302:
                location = response.headers.get('Location', '')
                logging.debug(f"认证成功，重定向位置: {location}")
                
                # 检查重定向位置，如果是个人门户说明认证成功
                if "personal.neu.edu.cn" in location or "pass.neu.edu.cn" in location:
                    return {
                        "success": True,
                        "cookies": dict(self.session.cookies),
                        "redirect_url": location
                    }
                
                # 从重定向URL中提取ticket（如果有的话）
                if "ticket=" in location:
                    ticket = location.split("ticket=")[1].split("&")[0]
                    return {
                        "success": True,
                        "ticket": ticket,
                        "cookies": dict(self.session.cookies)
                    }
            
            # 如果没有重定向，检查响应内容
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find("title")
            if title and title.text.strip() == "智慧东大--统一身份认证":
                raise UnionAuthError("用户名或密码错误")
            
            # 其他情况认为认证失败
            raise BackendError("认证失败，未获取到有效响应")
            
        except Exception as e:
            if isinstance(e, NEULoginError):
                raise
            else:
                raise BackendError(f"认证过程中发生异常: {str(e)}")
    
    def access_service(self, service_url: Optional[str] = None) -> Dict[str, Any]:
        """
        使用已认证的会话访问目标服务
        
        Args:
            service_url: 要访问的服务URL，如果不提供则使用初始化时的URL
            
        Returns:
            访问结果字典
        """
        target = service_url or self.service_url
        
        try:
            # 构造带有CAS认证的URL
            cas_url = f"https://pass.neu.edu.cn/tpass/login?service={target}"
            response = self.session.get(cas_url, allow_redirects=True)
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "url": response.url,
                "content": response.text
            }
        except Exception as e:
            raise BackendError(f"访问服务时发生异常: {str(e)}")

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




