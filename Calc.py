import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import csv
import os
import logging
from typing import Dict, List, Any
import subprocess
import sys

class NEUGradeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NEU成绩管理系统")
        self.root.geometry("1200x800")
        
        # 数据存储
        self.grades_data = []
        self.plan_data = []
        
        # 创建界面
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # 按钮区域
        button_frame = ttk.LabelFrame(main_frame, text="操作", padding="5")
        button_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 第一行按钮
        ttk.Button(button_frame, text="获取成绩", command=self.fetch_grades).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(button_frame, text="获取计划", command=self.fetch_plan).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(button_frame, text="读取成绩文件", command=self.load_grades_file).grid(row=0, column=2, padx=5, pady=2)
        ttk.Button(button_frame, text="读取计划文件", command=self.load_plan_file).grid(row=0, column=3, padx=5, pady=2)
        
        # 第二行按钮
        ttk.Button(button_frame, text="添加课程", command=self.add_course).grid(row=1, column=0, padx=5, pady=2)
        ttk.Button(button_frame, text="删除选中", command=self.delete_selected).grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(button_frame, text="保存成绩", command=self.save_grades).grid(row=1, column=2, padx=5, pady=2)
        
        # 平均学分绩显示
        self.gpa_var = tk.StringVar(value="平均学分绩: 0.00")
        gpa_label = ttk.Label(main_frame, textvariable=self.gpa_var, font=("Arial", 12, "bold"))
        gpa_label.grid(row=1, column=0, columnspan=2, pady=5)
        
        # 成绩表格
        self.create_grades_table(main_frame)
        
    def create_grades_table(self, parent):
        # 表格框架
        table_frame = ttk.LabelFrame(parent, text="成绩表格", padding="5")
        table_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # 创建Treeview
        columns = ("课程序号", "课程名称", "学分", "成绩", "绩点", "学分绩", "GPA影响")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        # 设置列标题和宽度
        column_widths = {"课程序号": 100, "课程名称": 200, "学分": 80, "成绩": 80, "绩点": 80, "学分绩": 80, "GPA影响": 100}
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=column_widths.get(col, 100), anchor="center")
        
        # 滚动条
        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        
        # 布局
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        scrollbar_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 绑定双击事件编辑绩点
        self.tree.bind("<Double-1>", self.edit_grade_point)
        
        # 排序状态
        self.sort_column = None
        self.sort_reverse = False
        
    def fetch_grades(self):
        """获取成绩"""
        try:
            messagebox.showinfo("提示", "正在获取成绩，请稍候...")
            result = subprocess.run([sys.executable, "Grade.py"], capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                self.load_grades_file()
                messagebox.showinfo("成功", "成绩获取完成！")
            else:
                messagebox.showerror("错误", f"获取成绩失败：{result.stderr}")
        except Exception as e:
            messagebox.showerror("错误", f"获取成绩时发生异常：{str(e)}")
    
    def fetch_plan(self):
        """获取计划"""
        try:
            messagebox.showinfo("提示", "正在获取培养计划，请稍候...")
            result = subprocess.run([sys.executable, "Plan.py"], capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                self.load_plan_file()
                messagebox.showinfo("成功", "培养计划获取完成！")
            else:
                messagebox.showerror("错误", f"获取培养计划失败：{result.stderr}")
        except Exception as e:
            messagebox.showerror("错误", f"获取培养计划时发生异常：{str(e)}")
    
    def load_grades_file(self):
        """读取成绩CSV文件"""
        try:
            # 弹出文件选择对话框
            grades_file = filedialog.askopenfilename(
                title="选择成绩文件",
                initialdir="output",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            
            if not grades_file:
                return
            
            new_grades_data = []
            with open(grades_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 转换数值字段
                    if '学分' in row and row['学分']:
                        try:
                            row['学分'] = float(row['学分'])
                        except ValueError:
                            row['学分'] = 0.0
                    
                    if '绩点' in row and row['绩点']:
                        try:
                            row['绩点'] = float(row['绩点'])
                        except ValueError:
                            row['绩点'] = 0.0
                    
                    new_grades_data.append(row)
            
            # 如果已有成绩数据，进行增量更新
            if self.grades_data:
                # 创建现有成绩的索引（按课程序号和课程名称）
                existing_courses = {}
                for grade in self.grades_data:
                    key = f"{grade.get('课程序号', '')}-{grade.get('课程名称', '')}"
                    existing_courses[key] = grade
                
                # 检查新成绩，只添加不存在的课程
                added_count = 0
                for new_grade in new_grades_data:
                    key = f"{new_grade.get('课程序号', '')}-{new_grade.get('课程名称', '')}"
                    if key not in existing_courses:
                        self.grades_data.append(new_grade)
                        added_count += 1
                
                messagebox.showinfo("成功", 
                    f"增量更新完成\n"
                    f"新增课程: {added_count} 门\n"
                    f"总课程数: {len(self.grades_data)} 门")
            else:
                # 如果没有现有数据，直接加载全部
                self.grades_data = new_grades_data
                messagebox.showinfo("成功", f"成功加载 {len(self.grades_data)} 门课程成绩")
            
            self.refresh_grades_table()
            
        except Exception as e:
            messagebox.showerror("错误", f"读取成绩文件失败：{str(e)}")
    
    def load_plan_file(self):
        """读取计划CSV文件"""
        try:
            plan_file = "output/plan.csv"
            if not os.path.exists(plan_file):
                messagebox.showwarning("警告", "计划文件不存在，请先获取培养计划")
                return
            
            self.plan_data = []
            with open(plan_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 转换数值字段
                    if '学分数' in row and row['学分数']:
                        try:
                            row['学分数'] = float(row['学分数'])
                        except ValueError:
                            row['学分数'] = 0.0
                    
                    self.plan_data.append(row)
            
            # 过滤掉已有成绩的课程（按课程名称匹配）
            if self.grades_data:
                existing_course_names = {grade.get('课程名称', '') for grade in self.grades_data}
                original_count = len(self.plan_data)
                self.plan_data = [course for course in self.plan_data 
                                if course.get('课程名称', '') not in existing_course_names]
                filtered_count = original_count - len(self.plan_data)
                
                if filtered_count > 0:
                    messagebox.showinfo("成功", 
                        f"成功加载 {len(self.plan_data)} 门计划课程\n"
                        f"已过滤 {filtered_count} 门已有成绩的课程")
                else:
                    messagebox.showinfo("成功", f"成功加载 {len(self.plan_data)} 门计划课程")
            else:
                messagebox.showinfo("成功", f"成功加载 {len(self.plan_data)} 门计划课程")
                
        except Exception as e:
            messagebox.showerror("错误", f"读取计划文件失败：{str(e)}")
    
    def refresh_grades_table(self):
        """刷新成绩表格"""
        # 清空表格
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 添加数据
        total_credit_points = 0
        total_credits = 0
        
        for grade in self.grades_data:
            course_id = grade.get('课程序号', '')
            course_name = grade.get('课程名称', '')
            credit = float(grade.get('学分', 0))
            # 成绩可能在不同字段中
            score = grade.get('最终', grade.get('总评成绩', grade.get('成绩', '')))
            grade_point = float(grade.get('绩点', 0))
            credit_point = credit * grade_point
            
            # 计算GPA影响
            gpa_impact = self.calculate_gpa_impact(grade)
            gpa_impact_str = f"{gpa_impact:+.4f}" if gpa_impact != 0 else "0.0000"
            
            self.tree.insert("", "end", values=(
                course_id, course_name, credit, score, grade_point, f"{credit_point:.2f}", gpa_impact_str
            ))
            
            total_credits += credit
            total_credit_points += credit_point
        
        # 更新平均学分绩
        avg_gpa = total_credit_points / total_credits if total_credits > 0 else 0
        self.gpa_var.set(f"平均学分绩: {avg_gpa:.4f} (总学分: {total_credits:.1f})")
        
        # 重置排序状态
        self.sort_column = None
        self.sort_reverse = False
        for col in self.tree['columns']:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))
    
    def edit_grade_point(self, event):
        """编辑绩点"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if not item:
            return
        
        # 获取当前值
        values = self.tree.item(item, 'values')
        current_grade_point = values[4]
        
        # 弹出输入对话框
        new_grade_point = simpledialog.askfloat(
            "编辑绩点", 
            f"课程: {values[1]}\n请输入新的绩点:",
            initialvalue=float(current_grade_point),
            minvalue=0.0,
            maxvalue=5.0
        )
        
        if new_grade_point is not None:
            # 更新数据
            course_id = values[0]
            for grade in self.grades_data:
                if grade.get('课程序号') == course_id:
                    grade['绩点'] = new_grade_point
                    break
            
            # 刷新表格
            self.refresh_grades_table()
    
    def add_course(self):
        """添加课程"""
        # 创建添加课程选择窗口
        self.show_add_course_dialog()
    
    def show_add_course_dialog(self):
        """显示添加课程选择对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("添加课程")
        dialog.geometry("600x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Notebook（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 标签页1：从培养计划选择
        plan_frame = ttk.Frame(notebook, padding="10")
        notebook.add(plan_frame, text="从培养计划选择")
        
        # 标签页2：手动输入
        manual_frame = ttk.Frame(notebook, padding="10")
        notebook.add(manual_frame, text="手动输入")
        
        # === 培养计划选择页面 ===
        self._create_plan_selection_tab(plan_frame, dialog)
        
        # === 手动输入页面 ===
        self._create_manual_input_tab(manual_frame, dialog)
        
        # 关闭按钮
        close_frame = ttk.Frame(main_frame)
        close_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(close_frame, text="关闭", command=dialog.destroy).pack()
    
    def _create_plan_selection_tab(self, parent, dialog):
        """创建培养计划选择标签页"""
        if not self.plan_data:
            ttk.Label(parent, text="请先点击'获取计划'或'读取计划文件'加载培养计划数据", 
                     font=("Arial", 12), foreground="red").pack(pady=50)
            return
        
        # 搜索框
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(search_frame, text="搜索课程:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Arial", 10))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 课程列表
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        columns = ("课程序号", "课程名称", "学分", "成绩记载方式")
        course_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        
        # 设置列宽
        course_tree.column("课程序号", width=120, anchor="center")
        course_tree.column("课程名称", width=200, anchor="w")
        course_tree.column("学分", width=60, anchor="center")
        course_tree.column("成绩记载方式", width=100, anchor="center")
        
        for col in columns:
            course_tree.heading(col, text=col)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=course_tree.yview)
        course_tree.configure(yscrollcommand=scrollbar.set)
        
        course_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 填充数据
        def update_course_list():
            for item in course_tree.get_children():
                course_tree.delete(item)
            
            search_text = search_var.get().lower()
            for course in self.plan_data:
                course_id = course.get('课程序号', '')
                course_name = course.get('课程名称', '')
                credit = course.get('学分数', '')
                grade_type = course.get('成绩记载方式', '')
                
                if not search_text or search_text in course_name.lower() or search_text in course_id.lower():
                    course_tree.insert("", "end", values=(course_id, course_name, credit, grade_type))
        
        update_course_list()
        search_var.trace('w', lambda *args: update_course_list())
        
        # 操作说明
        info_frame = ttk.Frame(parent)
        info_frame.pack(fill=tk.X, pady=(5, 10))
        ttk.Label(info_frame, text="💡 双击课程或点击'添加选中课程'按钮", 
                 font=("Arial", 9), foreground="blue").pack()
        
        # 按钮
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        def add_selected_course():
            selection = course_tree.selection()
            if not selection:
                messagebox.showwarning("提示", "请先选择一门课程")
                return
            
            values = course_tree.item(selection[0], 'values')
            course_id, course_name, default_credit, grade_type = values
            
            # 输入绩点
            grade_point = simpledialog.askfloat(
                "输入绩点", 
                f"课程: {course_name}\n学分: {default_credit}\n成绩记载方式: {grade_type}\n\n请输入绩点 (0.0-5.0):",
                minvalue=0.0,
                maxvalue=5.0
            )
            if grade_point is None:
                return
            
            credit = float(default_credit) if default_credit else 1.0
            self._add_course_to_data(course_id, course_name, credit, grade_point)
            
            # 从计划数据中移除已添加的课程（按课程名称匹配）
            self.plan_data = [course for course in self.plan_data 
                            if course.get('课程名称', '') != course_name]
            
            # 刷新课程列表
            update_course_list()
            
            messagebox.showinfo("成功", f"已添加课程: {course_name}")
        
        # 双击事件
        course_tree.bind("<Double-1>", lambda e: add_selected_course())
        
        ttk.Button(button_frame, text="添加选中课程", command=add_selected_course).pack(side=tk.LEFT)
    
    def _create_manual_input_tab(self, parent, dialog):
        """创建手动输入标签页"""
        # 说明文字
        info_label = ttk.Label(parent, text="手动添加课程信息", font=("Arial", 12, "bold"))
        info_label.pack(pady=(10, 20))
        
        # 输入区域
        input_frame = ttk.LabelFrame(parent, text="课程信息", padding="20")
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 课程名称
        ttk.Label(input_frame, text="课程名称:", font=("Arial", 10)).grid(row=0, column=0, sticky=tk.W, pady=10)
        course_name_var = tk.StringVar()
        name_entry = ttk.Entry(input_frame, textvariable=course_name_var, width=35, font=("Arial", 10))
        name_entry.grid(row=0, column=1, pady=10, padx=(10, 0), sticky=tk.W)
        name_entry.focus()  # 默认焦点
        
        # 学分
        ttk.Label(input_frame, text="学分:", font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=10)
        credit_var = tk.StringVar(value="")  # 默认值
        credit_entry = ttk.Entry(input_frame, textvariable=credit_var, width=35, font=("Arial", 10))
        credit_entry.grid(row=1, column=1, pady=10, padx=(10, 0), sticky=tk.W)
        
        # 绩点
        ttk.Label(input_frame, text="绩点:", font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=10)
        grade_point_var = tk.StringVar()
        grade_entry = ttk.Entry(input_frame, textvariable=grade_point_var, width=35, font=("Arial", 10))
        grade_entry.grid(row=2, column=1, pady=10, padx=(10, 0), sticky=tk.W)
        
        # 提示信息
        tip_frame = ttk.Frame(parent)
        tip_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Label(tip_frame, text="绩点范围0.0-5.0", 
                 font=("Arial", 9), foreground="gray").pack()
        
        # 按钮
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)
        
        def add_manual_course():
            course_name = course_name_var.get().strip()
            credit_str = credit_var.get().strip()
            grade_point_str = grade_point_var.get().strip()
            
            # 验证输入
            if not course_name:
                messagebox.showwarning("输入错误", "请输入课程名称")
                name_entry.focus()
                return
            
            try:
                credit = float(credit_str) if credit_str else 1.0
                grade_point = float(grade_point_str) if grade_point_str else 0.0
                
                if credit <= 0:
                    messagebox.showwarning("输入错误", "学分必须大于0")
                    credit_entry.focus()
                    return
                
                if grade_point < 0 or grade_point > 5:
                    messagebox.showwarning("输入错误", "绩点必须在0.0-5.0之间")
                    grade_entry.focus()
                    return
                
            except ValueError:
                messagebox.showwarning("输入错误", "学分和绩点必须是有效数字")
                return
            
            # 直接添加课程
            self._add_course_to_data("无", course_name, credit, grade_point)
            messagebox.showinfo("成功", f"已添加课程: {course_name}")
            
            # 清空输入框，准备下次输入
            course_name_var.set("")
            credit_var.set("")
            grade_point_var.set("")
            name_entry.focus()  # 焦点回到课程名称输入框
        
        # 回车键绑定
        def on_enter(event):
            add_manual_course()
        
        name_entry.bind("<Return>", lambda e: credit_entry.focus())
        credit_entry.bind("<Return>", lambda e: grade_entry.focus())
        grade_entry.bind("<Return>", on_enter)
        
        ttk.Button(button_frame, text="添加课程", command=add_manual_course).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="清空", command=lambda: [var.set("") for var in [course_name_var, grade_point_var]] + [credit_var.set("1.0")]).pack(side=tk.LEFT, padx=(10, 0))
    
    def _add_course_to_data(self, course_id, course_name, credit, grade_point):
        """添加课程到数据中"""
        # 添加到成绩数据，使用与现有数据相同的字段结构
        if self.grades_data:
            # 复制现有数据的字段结构
            new_grade = dict.fromkeys(self.grades_data[0].keys(), '无')
            new_grade.update({
                '课程序号': course_id,
                '课程名称': course_name,
                '学分': credit,
                '绩点': grade_point
            })
            # 根据现有字段设置成绩为"无"
            if '最终' in new_grade:
                new_grade['最终'] = "无"
            elif '总评成绩' in new_grade:
                new_grade['总评成绩'] = "无"
            else:
                new_grade['成绩'] = "无"
        else:
            # 如果没有现有数据，使用基本结构
            new_grade = {
                '课程序号': course_id,
                '课程名称': course_name,
                '学分': credit,
                '成绩': "无",
                '绩点': grade_point
            }
        
        self.grades_data.append(new_grade)
        
        # 刷新表格
        self.refresh_grades_table()
    
    def delete_selected(self):
        """删除选中的课程"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要删除的课程")
            return
        
        if messagebox.askyesno("确认", "确定要删除选中的课程吗？"):
            for item in selection:
                values = self.tree.item(item, 'values')
                course_id = values[0]
                # 从数据中删除
                self.grades_data = [g for g in self.grades_data if g.get('课程序号') != course_id]
            
            self.refresh_grades_table()
    
    def save_grades(self):
        """保存成绩到CSV文件"""
        try:
            if not os.path.exists('output'):
                os.makedirs('output')
            
            # 确定CSV文件的字段名
            if self.grades_data:
                # 使用现有数据的字段名
                fieldnames = list(self.grades_data[0].keys())
            else:
                # 默认字段名
                fieldnames = ['课程序号', '课程名称', '学分', '成绩', '绩点']
            
            with open('output/DIY_Grade.csv', 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.grades_data)
            
            messagebox.showinfo("成功", "成绩已保存到 output/DIY_Grade.csv")
        except Exception as e:
            messagebox.showerror("错误", f"保存成绩失败：{str(e)}")

    def calculate_gpa_impact(self, target_course):
        """计算某门课程对总GPA的影响"""
        if not self.grades_data or len(self.grades_data) <= 1:
            return 0.0
        
        # 计算不包含该课程的GPA
        other_courses = [course for course in self.grades_data if course != target_course]
        
        total_credits_without = 0
        total_credit_points_without = 0
        
        for course in other_courses:
            credit = float(course.get('学分', 0))
            grade_point = float(course.get('绩点', 0))
            total_credits_without += credit
            total_credit_points_without += credit * grade_point
        
        if total_credits_without == 0:
            return 0.0
        
        gpa_without = total_credit_points_without / total_credits_without
        
        # 计算包含该课程的总GPA
        total_credits = 0
        total_credit_points = 0
        
        for course in self.grades_data:
            credit = float(course.get('学分', 0))
            grade_point = float(course.get('绩点', 0))
            total_credits += credit
            total_credit_points += credit * grade_point
        
        if total_credits == 0:
            return 0.0
        
        gpa_with = total_credit_points / total_credits
        
        # 返回影响值（正值表示提升GPA，负值表示降低GPA）
        return gpa_with - gpa_without

    def sort_by_column(self, column):
        """按列排序"""
        # 获取所有数据
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item, 'values')
            data.append((item, values))
        
        # 确定排序键和是否反向
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = False
        
        # 根据列类型确定排序方式
        def sort_key(item):
            values = item[1]
            col_index = list(self.tree['columns']).index(column)
            value = values[col_index]
            
            # 数值列按数值排序
            if column in ["学分", "绩点", "学分绩", "GPA影响"]:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0
            # 文本列按字符串排序
            else:
                return str(value)
        
        # 排序
        data.sort(key=sort_key, reverse=self.sort_reverse)
        
        # 重新插入数据
        for item, values in data:
            self.tree.delete(item)
        
        for item, values in data:
            self.tree.insert("", "end", values=values)
        
        # 更新列标题显示排序状态
        for col in self.tree['columns']:
            if col == column:
                direction = " ↓" if self.sort_reverse else " ↑"
                self.tree.heading(col, text=col + direction)
            else:
                self.tree.heading(col, text=col, command=lambda c=col: self.sort_by_column(c))

def main():
    root = tk.Tk()
    app = NEUGradeApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()



















