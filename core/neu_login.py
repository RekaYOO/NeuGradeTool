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


class UnknownPageError(NEULoginError):
    """未知页面错误"""
    def __init__(self, page_soup):
        self.page_soup = page_soup
        super().__init__("遇到未知页面")


class NEULogin:
    """东北大学统一身份认证登录类"""
    
    def __init__(self, service_url: Optional[str] = None, bypass_proxy: bool = False):
        """
        初始化NEU登录
        
        Args:
            service_url: 目标服务URL，如果不提供则使用默认的ipgw服务
            bypass_proxy: 是否跳过系统代理
        """
        self.service_url = service_url or "http://219.216.96.4/eams/homeExt.action"
        self.target_url = f"https://pass.neu.edu.cn/tpass/login?service={self.service_url}"
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
    
    def _get_login_form_data(self) -> Dict[str, str]:
        """获取登录表单数据"""
        try:
            response = self.session.get(self.target_url)
            # logging.debug(f"登录页面状态码: {response.status_code}")
            # logging.debug(f"登录页面URL: {response.url}")
            
            page_soup = BeautifulSoup(response.text, "html.parser")
            form: Tag = page_soup.find("form", {'id': 'loginForm'})
            
            if not form:
                # logging.error(f"页面内容: {response.text[:500]}...")
                raise BackendError(f"无法找到登录表单，页面状态码: {response.status_code}")
                
            lt_input = form.find("input", {'id': 'lt'})
            execution_input = form.find("input", {'name': 'execution'})
            
            if not lt_input or not execution_input:
                # logging.error("缺少必要的表单字段")
                raise BackendError("登录表单缺少必要字段")
                
            return {
                "form_lt_string": lt_input.attrs["value"],
                "form_destination": form.attrs['action'],
                "form_execution": execution_input.attrs["value"]
            }
        except Exception as e:
            if isinstance(e, NEULoginError):
                raise
            logging.error(f"获取登录表单时发生异常: {str(e)}")
            raise BackendError(f"获取登录表单失败: {str(e)}")
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        执行登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            登录结果字典，包含success状态和相关信息
            
        Raises:
            UnionAuthError: 用户名或密码错误
            BackendError: 后端服务异常
            UnknownPageError: 遇到未知页面
        """
        try:
            # 获取登录表单数据
            form_data = self._get_login_form_data()
            
            # 构造登录数据
            login_data = {
                'rsa': username + password + form_data['form_lt_string'],
                'ul': len(username),
                'pl': len(password),
                'lt': form_data['form_lt_string'],
                'execution': form_data['form_execution'],
                '_eventId': 'submit'
            }
            
            # 提交登录请求
            response = self.session.post(
                "https://pass.neu.edu.cn" + form_data['form_destination'],
                data=login_data,
                allow_redirects=True
            )
            
            # 解析登录结果
            return self._parse_login_result(response)
            
        except Exception as e:
            if isinstance(e, NEULoginError):
                raise
            else:
                raise BackendError(f"登录过程中发生异常: {str(e)}")
    
    def _parse_login_result(self, response) -> Dict[str, Any]:
        """解析登录结果"""
        # logging.debug(f"登录响应状态码: {response.status_code}")
        # logging.debug(f"登录响应URL: {response.url}")
        
        soup = BeautifulSoup(response.text, "html.parser")
        title_element = soup.find("title")
        
        # 检查是否包含ticket参数，这是登录成功的重要标志
        if "ticket" in response.url:
            return self._extract_success_info(response)
        
        # 如果没有title标签，但URL包含目标服务域名，可能是登录成功
        if not title_element:
            # 检查是否跳转到了目标服务
            if self.service_url and any(domain in response.url for domain in [
                "219.216.96.4", "eams", "homeExt.action"
            ]):
                # logging.info("目标页面无标题，但URL显示登录成功")
                return self._extract_success_info(response)
            else:
                # logging.error(f"页面内容: {response.text[:500]}...")
                raise BackendError(f"无法获取页面标题，状态码: {response.status_code}")
        
        page_title = title_element.text.strip()
        # logging.debug(f"页面标题: {page_title}")
        
        # 根据页面标题判断登录结果
        if page_title == "智慧东大--统一身份认证":
            raise UnionAuthError("用户名或密码错误")
        else:
            # 对于其他情况，如果URL包含ticket或目标服务，认为登录成功
            if "ticket" in response.url or any(domain in response.url for domain in [
                "219.216.96.4", "eams"
            ]):
                return self._extract_success_info(response)
            else:
                logging.error(f"未知页面标题: {page_title}")
                logging.error(f"页面内容: {response.text}")
                #raise UnknownPageError(soup)
    
    def _extract_success_info(self, response) -> Dict[str, Any]:
        """提取成功登录的信息"""
        result = {
            "success": True,
            "final_url": response.url,
            "cookies": dict(self.session.cookies)
        }
        
        # 尝试提取ticket
        parsed_url = urlparse(response.url)
        query_params = parse_qs(parsed_url.query)
        if 'ticket' in query_params:
            result["ticket"] = query_params['ticket'][0]
        
        return result
    
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
        """
        解析成绩响应HTML内容
        
        Args:
            html_content: HTML响应内容
            
        Returns:
            解析后的成绩数据
        """
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 提取总平均绩点
        gpa_div = soup.find("div", string=lambda text: text and "总平均绩点：" in text)
        total_gpa = None
        if gpa_div:
            gpa_text = gpa_div.get_text().strip()
            # 提取绩点数值
            import re
            gpa_match = re.search(r'总平均绩点：(\d+\.?\d*)', gpa_text)
            if gpa_match:
                total_gpa = float(gpa_match.group(1))
        
        # 查找成绩表格
        table = soup.find("table", {"class": "gridtable"})
        if not table:
            raise BackendError("未找到成绩表格")
        
        # 解析表头
        headers = []
        thead = table.find("thead")
        if thead:
            header_row = thead.find("tr")
            if header_row:
                headers = [th.get_text().strip() for th in header_row.find_all("th")]
        
        # 解析成绩数据
        courses = []
        tbody = table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= len(headers):
                    course_data = {}
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            # 处理课程名称中的特殊标记
                            cell_text = cell.get_text().strip()
                            # 移除多余的空白字符
                            cell_text = re.sub(r'\s+', ' ', cell_text)
                            course_data[headers[i]] = cell_text
                    
                    # 数据类型转换
                    if "学分" in course_data and course_data["学分"]:
                        try:
                            course_data["学分"] = float(course_data["学分"])
                        except ValueError:
                            pass
                    
                    if "绩点" in course_data and course_data["绩点"]:
                        try:
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



