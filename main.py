#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IntraceX 自动登录和续期脚本
"""

import asyncio
import os
import random
import re
from datetime import datetime
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

# =====================================================================
#                          配置区域
# =====================================================================

# IntraceX 登录信息配置 (支持环境变量)
LOGIN_EMAIL = os.getenv("INTRACEX_EMAIL", "kamanfaizintx@2925.com")  # 请替换为您的邮箱
LOGIN_PASSWORD = os.getenv("INTRACEX_PASSWORD", "faiz555!!")         # 请替换为您的密码

# 网站配置
TARGET_URL = "https://intracex.de/minecraft"

# 浏览器配置 (GitHub Actions中自动启用无头模式)
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
USE_HEADLESS = IS_GITHUB_ACTIONS or os.getenv("USE_HEADLESS", "false").lower() == "true"
WAIT_TIMEOUT = 10000  # 页面元素等待超时时间（毫秒）

# =====================================================================
#                        IntraceX 自动登录类
# =====================================================================

class IntraceXAutoLogin:
    """IntraceX 自动登录主类 - Playwright版本"""
    
    def __init__(self):
        """初始化 IntraceX 自动登录器"""
        self.browser = None
        self.context = None
        self.page = None
        self.headless = USE_HEADLESS
        self.email = LOGIN_EMAIL
        self.password = LOGIN_PASSWORD
        self.target_url = TARGET_URL
        self.wait_timeout = WAIT_TIMEOUT
        self.screenshot_count = 0  # 截图计数器
        
        # 状态跟踪
        self.server_id = None        # 存储服务器ID
        self.old_expiry_date = None  # 存储旧的到期时间
        self.new_expiry_date = None  # 存储新的到期时间
        self.can_extend = None       # 存储是否可以续期的状态
        self.renewal_result = None   # 存储续期结果：success/failed/unexpired
    
    # =================================================================
    #                       1. 浏览器管理模块
    # =================================================================
        
    async def setup_browser(self):
        """设置并启动 Playwright 浏览器"""
        try:
            playwright = await async_playwright().start()
            
            # 配置浏览器选项
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
            
            # 启动浏览器
            self.browser = await playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )
            
            # 创建浏览器上下文
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='de-DE',  # 设置德语本地化
                timezone_id='Europe/Berlin',  # 设置德国时区
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # 创建页面
            self.page = await self.context.new_page()
            
            # 应用stealth插件
            await stealth_async(self.page)
            print("✅ Stealth 插件已应用")
            
            print("✅ Playwright 浏览器初始化成功")
            return True
            
        except Exception as e:
            print(f"❌ Playwright 浏览器初始化失败: {e}")
            return False
    
    async def take_screenshot(self, filename: str, description: str = ""):
        """截图功能 - 用于可视化调试"""
        try:
            if self.page:
                self.screenshot_count += 1
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # 直接保存在根目录
                screenshot_path = f"{timestamp}_{filename}"
                await self.page.screenshot(path=screenshot_path, full_page=True)
                print(f"📸 {description}截图已保存: {screenshot_path}")
                
        except Exception as e:
            print(f"❌ 截图失败: {str(e)}")
    
    def validate_config(self):
        """验证配置信息"""
        if not self.email or not self.password:
            print("❌ 邮箱或密码未设置！")
            return False
        
        print("✅ 配置信息验证通过")
        return True
    
    async def cleanup(self):
        """清理资源"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            print("🧹 浏览器已关闭")
        except Exception as e:
            print(f"⚠️ 清理资源时出错: {e}")
    
    # =================================================================
    #                       2. 页面导航模块
    # =================================================================
    
    async def navigate_to_login(self):
        """导航到登录页面"""
        try:
            print(f"🌐 正在访问: {self.target_url}")
            await self.page.goto(self.target_url, wait_until='networkidle')
            
            # 等待页面加载完成
            await self.page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(8)  # 额外等待确保页面完全加载
            
            print("✅ 页面加载成功")
            return True
            
        except Exception as e:
            print(f"❌ 导航失败: {e}")
            return False
    
    async def verify_page(self, expected_url: str, expected_text: str, page_name: str):
        """验证页面URL和内容"""
        try:
            current_url = self.page.url
            print(f"🔍 当前页面URL: {current_url}")
            
            # 验证URL
            url_match = expected_url in current_url or current_url.startswith(expected_url)
            if url_match:
                print(f"✅ URL验证成功: {page_name}")
            else:
                print(f"❌ URL验证失败: 期望包含 {expected_url}, 实际为 {current_url}")
                return False
            
            # 验证页面内容
            try:
                page_content = await self.page.content()
                if expected_text in page_content:
                    print(f"✅ 页面内容验证成功: 找到文字 '{expected_text}'")
                    return True
                else:
                    print(f"❌ 页面内容验证失败: 未找到文字 '{expected_text}'")
                    return False
            except Exception as content_error:
                print(f"⚠️  页面内容验证异常: {str(content_error)}")
                return url_match  # 如果内容验证失败，至少URL是对的
                
        except Exception as e:
            print(f"❌ 页面验证异常: {str(e)}")
            return False
    
    # =================================================================
    #                       3. 登录表单处理模块
    # =================================================================
    
    async def human_type(self, element, text: str):
        """模拟人类打字的方式逐字输入文本"""
        # 点击输入框聚焦
        await element.click()
        await asyncio.sleep(0.1)  # 短暂等待聚焦
        
        print(f"开始逐字符输入: {text[:3]}***")  # 只显示前3个字符保护隐私
        
        # 逐字符输入
        for char in text:
            # 输入当前字符
            await element.type(char)
            
            # 计算延迟时间
            delay = random.randint(50, 150)  # 50-150ms延迟
            
            # 如果是空格或特殊字符，增加额外停顿
            if char in [' ', '@', '.', '_', '-']:
                delay += 200
            
            # 随机在某些位置增加更长的停顿（模拟思考）
            if random.random() < 0.1:  # 10% 概率
                delay += random.randint(100, 300)
            
            # 等待
            await asyncio.sleep(delay / 1000)  # 转换为秒
            
        print("✅ 输入完成")
    
    async def perform_login(self):
        """执行登录操作"""
        try:
            print("\n📝 第二步：填写登录表单")
            
            # 查找邮箱输入框
            print("正在查找邮箱输入框...")
            username_selectors = ['#email']  # 最有效的选择器
            
            username_input = None
            for selector in username_selectors:
                try:
                    username_input = await self.page.wait_for_selector(selector, timeout=2000)
                    if username_input:
                        break
                except:
                    continue
            
            if username_input:
                print("✅ 找到邮箱输入框")
            else:
                print("❌ 未找到邮箱输入框")
                return False
            
            if username_input:
                print("找到邮箱输入框，正在模拟人类打字输入...")
                await self.human_type(username_input, self.email)
            else:
                raise Exception("无法找到邮箱输入框")
            
            # 查找密码输入框
            print("正在查找密码输入框...")
            password_selectors = ['#password']  # 最有效的选择器
            
            password_input = None
            for selector in password_selectors:
                try:
                    password_input = await self.page.wait_for_selector(selector, timeout=2000)
                    if password_input:
                        break
                except:
                    continue
            
            if password_input:
                print("✅ 找到密码输入框")
            else:
                print("❌ 未找到密码输入框")
            
            if password_input:
                print("找到密码输入框，正在模拟人类打字输入...")
                await self.human_type(password_input, self.password)
            else:
                raise Exception("无法找到密码输入框")
            
            # 查找登录按钮
            print("正在查找登录按钮...")
            login_button_selectors = ['input[type="submit"][value="Anmelden"]']  # 最有效的选择器
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = await self.page.wait_for_selector(selector, timeout=2000)
                    if login_button:
                        break
                except:
                    continue
            
            if login_button:
                print("✅ 找到登录按钮")
            else:
                print("❌ 未找到登录按钮")
            
            # 提交登录表单
            print("\n🔐 第三步：提交登录表单")
            if login_button:
                print("找到登录按钮，正在点击...")
                # 模拟人类检查输入内容的停顿
                await asyncio.sleep(random.uniform(0.5, 1.5))
                await login_button.click()
            else:
                # 如果找不到按钮，尝试按回车键提交表单
                print("未找到登录按钮，尝试按回车键提交...")
                await asyncio.sleep(random.uniform(0.3, 0.8))
                await self.page.keyboard.press('Enter')
            
            print("✅ 登录表单已提交")
            
            # 等待页面跳转
            print("⏳ 等待登录处理和页面跳转...")
            await asyncio.sleep(3)
            return True
            
        except Exception as e:
            print(f"❌ 登录操作失败: {e}")
            return False
    
    # =================================================================
    #                       4. 服务器信息获取模块
    # =================================================================
    
    async def get_server_id(self):
        """获取服务器ID"""
        try:
            print("\n🔢 获取服务器ID...")
            
            # 等待表格加载
            await self.page.wait_for_selector('table', timeout=10000)
            await asyncio.sleep(5)  # 确保数据加载完成
            
            # 直接查找第一列的服务器ID
            element = await self.page.query_selector('table tbody tr td:nth-child(1)')
            
            if element:
                server_id = await element.text_content()
                if server_id and server_id.strip().isdigit():
                    server_id = server_id.strip()
                    print(f"✅ 找到服务器ID: {server_id}")
                    return server_id
            
            print("❌ 未找到服务器ID")
            return None
                
        except Exception as e:
            print(f"❌ 获取服务器ID失败: {str(e)}")
            return None
    
    async def get_expiry_date(self):
        """获取服务器到期时间"""
        try:
            print("\n📅 获取服务器到期时间...")
            
            # 等待表格加载
            await self.page.wait_for_selector('table', timeout=10000)
            await asyncio.sleep(5)  # 确保数据加载完成
            
            # 查找"Läuft ab"列的到期时间
            expiry_selectors = ['table tbody tr td:nth-child(5)']  # 最有效的选择器
            
            expiry_date = None
            
            # 尝试不同的选择器
            for selector in expiry_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    
                    for element in elements:
                        text = await element.text_content()
                        if text and re.match(r'\d{2}\.\d{2}\.\d{4}', text.strip()):
                            expiry_date = text.strip()
                            break
                    
                    if expiry_date:
                        break
                        
                except:
                    continue
            
            if expiry_date:
                print(f"✅ 找到到期时间: {expiry_date}")
            else:
                print("❌ 未找到到期时间")
            
            # 如果上面的方法都失败，尝试查找整个页面中的日期
            if not expiry_date:
                print("🔍 在整个页面中搜索日期格式...")
                page_content = await self.page.content()
                date_matches = re.findall(r'\d{2}\.\d{2}\.\d{4}', page_content)
                if date_matches:
                    # 取最后一个匹配的日期（通常是到期时间）
                    expiry_date = date_matches[-1]
                    print(f"✅ 在页面中找到日期: {expiry_date}")
            
            if expiry_date:
                # 转换日期格式 DD.MM.YYYY -> YYYY-MM-DD
                try:
                    day, month, year = expiry_date.split('.')
                    formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    print(f"📅 旧到期时间: {expiry_date} -> {formatted_date}")
                    return formatted_date
                except Exception as format_error:
                    print(f"❌ 日期格式转换失败: {str(format_error)}")
                    return expiry_date  # 返回原始格式
            else:
                print("❌ 未找到到期时间")
                return None
                
        except Exception as e:
            print(f"❌ 获取到期时间失败: {str(e)}")
            return None
    
    async def check_extend_button(self):
        """检查续期按钮的可点击性，如果可点击则执行续期操作"""
        try:
            print("\n🔄 检查续期按钮状态...")
            
            # 等待表格加载
            await self.page.wait_for_selector('table', timeout=10000)
            await asyncio.sleep(5)  # 确保数据加载完成
            
            # 查找续期按钮的选择器
            extend_button_selectors = ['td a:has-text("Verlängern")']  # 最有效的选择器
            
            extend_button = None
            
            # 尝试不同的选择器
            for selector in extend_button_selectors:
                try:
                    extend_button = await self.page.query_selector(selector)
                    if extend_button:
                        break
                except:
                    continue
            
            if extend_button:
                print("✅ 找到续期按钮")
            else:
                print("❌ 未找到续期按钮")
                return False
            
            # 检查按钮class是否包含disabled
            try:
                button_class = await extend_button.get_attribute('class') or ''
                print(f"📋 按钮class: {button_class}")
                
                # 简化判断逻辑：只要class中包含disabled就是不可点击
                if 'disabled' in button_class.lower():
                    print("❌ 续期按钮不可点击 - 当前不可续期")
                    return False
                else:
                    print("✅ 续期按钮可点击 - 可以进行续期")
                    
                    # 执行续期操作
                    print("\n🚀 开始执行续期操作...")
                    await self.perform_extend_action(extend_button)
                    return True
                    
            except Exception as attr_error:
                print(f"❌ 检查按钮class失败: {str(attr_error)}")
                return False
                
        except Exception as e:
            print(f"❌ 检查续期按钮失败: {str(e)}")
            return False
    
    async def perform_extend_action(self, extend_button):
        """执行续期操作"""
        try:
            print("🔄 正在点击续期按钮...")
            
            # 点击续期按钮
            await extend_button.click()
            print("✅ 续期按钮点击成功")
            
            # 等待页面响应
            print("⏳ 等待页面响应...")
            await asyncio.sleep(2)
            
            # 截图记录点击后的状态
            await self.take_screenshot("04_after_extend_click", "续期按钮点击后")
            
            # 等待页面内容刷新
            try:
                # 等待页面内容更新
                await self.page.wait_for_load_state('networkidle', timeout=10000)
                print("✅ 页面内容刷新完成")
            except:
                print("⚠️  页面刷新超时，但操作可能已完成")
            
            # 额外等待确保内容完全更新
            await asyncio.sleep(3)
            
            # 验证续期结果
            print("\n🔍 验证续期结果...")
            success = await self.verify_renewal_success()
            
            # 验证完成后再截图记录最终状态
            await self.take_screenshot("05_extend_final", "续期验证完成后的最终状态")
            
            if success:
                print("🎉 续期操作执行完成！续期成功！")
            else:
                print("⚠️  续期操作执行完成，但续期结果需要进一步确认")
            
        except Exception as e:
            print(f"❌ 续期操作失败: {str(e)}")
            # 即使失败也要截图记录
            await self.take_screenshot("04_extend_error", "续期操作失败")
            raise
    
    async def verify_renewal_success(self):
        """验证续期是否成功"""
        try:
            print("📅 第九步：验证续期结果")
            
            # 1. 获取新的到期时间
            print("🔄 获取新的到期时间...")
            new_expiry_date = await self.get_expiry_date(self.page)
            
            if new_expiry_date:
                print(f"📅 新到期时间: {new_expiry_date}")
                self.new_expiry_date = new_expiry_date
            else:
                print("❌ 未能获取新的到期时间")
                self.new_expiry_date = None
            
            # 2. 检查续期按钮状态
            print("🔄 检查续期按钮新状态...")
            button_disabled = await self.check_button_disabled_status()
            
            # 3. 综合判断续期是否成功
            success = self.evaluate_renewal_success(new_expiry_date, button_disabled)
            
            if success:
                print("🎉 续期成功确认！")
                print(f"   📊 旧到期时间: {self.old_expiry_date}")
                print(f"   📊 新到期时间: {new_expiry_date}")
                print(f"   📊 按钮状态: 已禁用")
                # 设置续期成功状态
                self.renewal_result = "success"
            else:
                print("❌ 续期可能失败")
                print(f"   📊 旧到期时间: {self.old_expiry_date}")
                print(f"   📊 新到期时间: {new_expiry_date or '未获取到'}")
                print(f"   📊 按钮状态: {'已禁用' if button_disabled else '仍可点击'}")
                # 设置续期失败状态
                self.renewal_result = "failed"
                
            return success
            
        except Exception as e:
            print(f"❌ 验证续期结果失败: {str(e)}")
            return False
    
    async def check_button_disabled_status(self):
        """检查续期按钮是否变成disabled状态"""
        try:
            # 等待表格加载
            await self.page.wait_for_selector('table', timeout=10000)
            await asyncio.sleep(5)
            
            # 查找续期按钮
            extend_button = await self.page.query_selector('td a:has-text("Verlängern")')
            
            if extend_button:
                # 检查按钮class
                button_class = await extend_button.get_attribute('class') or ''
                print(f"📋 续期后按钮class: {button_class}")
                
                # 判断是否包含disabled
                is_disabled = 'disabled' in button_class.lower()
                if is_disabled:
                    print("✅ 续期按钮已变成disabled状态")
                else:
                    print("⚠️  续期按钮仍然可点击")
                
                return is_disabled
            else:
                print("❌ 未找到续期按钮")
                return False
                
        except Exception as e:
            print(f"❌ 检查按钮状态失败: {str(e)}")
            return False
    
    def evaluate_renewal_success(self, new_expiry_date, button_disabled):
        """综合评估续期是否成功"""
        try:
            # 检查条件1：新到期时间是否有变化
            date_changed = False
            if self.old_expiry_date and new_expiry_date:
                if new_expiry_date != self.old_expiry_date:
                    print("✅ 到期时间已更新")
                    date_changed = True
                else:
                    print("⚠️  到期时间未变化")
            else:
                print("⚠️  无法比较到期时间（缺少数据）")
            
            # 检查条件2：按钮是否变成disabled
            if button_disabled:
                print("✅ 续期按钮已禁用")
            else:
                print("⚠️  续期按钮仍可点击")
            
            # 综合判断：两个条件都满足才算成功
            success = date_changed and button_disabled
            
            return success
            
        except Exception as e:
            print(f"❌ 评估续期结果失败: {str(e)}")
            return False
    
    def get_old_expiry_date(self):
        """获取已记录的旧到期时间"""
        return self.old_expiry_date
    
    # =================================================================
    #                       5. README生成模块
    # =================================================================
    
    def generate_readme(self):
        """生成README.md文件"""
        try:
            print("\n📝 生成README.md文件...")
            
            # 获取北京时间（UTC+8）
            from datetime import datetime, timezone, timedelta
            beijing_tz = timezone(timedelta(hours=8))
            current_time = datetime.now(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")
            
            # 构建README内容
            readme_content = f"**最后运行时间**: `{current_time}`\n\n"
            readme_content += "**运行结果**: <br>\n"
            
            # 添加服务器ID
            server_id_display = f"#{self.server_id}" if self.server_id else "#未知"
            readme_content += f"🖥️服务器ID：`{server_id_display}`<br>"
            
            # 根据续期结果添加不同内容
            if self.renewal_result == "success":
                readme_content += "📊续期结果：✅Success<br>"
                readme_content += f"🕛️旧到期时间：`{self.old_expiry_date or '未知'}`<br>"
                readme_content += f"🕡️新到期时间：`{self.new_expiry_date or '未知'}`"
            elif self.renewal_result == "unexpired":
                readme_content += "📊续期结果：ℹ️Unexpired<br>"
                readme_content += f"🕛️旧到期时间：`{self.old_expiry_date or '未知'}`"
            elif self.renewal_result == "failed":
                readme_content += "📊续期结果：❌Failed<br>"
                readme_content += f"🕛️旧到期时间：`{self.old_expiry_date or '未知'}`"
            else:
                # 默认情况
                readme_content += "📊续期结果：⚠️Unknown<br>"
                readme_content += f"🕛️旧到期时间：`{self.old_expiry_date or '未知'}`"
            
            # 写入README.md文件
            with open("README.md", "w", encoding="utf-8") as f:
                f.write(readme_content)
            
            print("✅ README.md文件生成成功")
            print(f"📄 内容预览:")
            print(readme_content)
            
        except Exception as e:
            print(f"❌ 生成README.md失败: {str(e)}")
    
    # =================================================================
    #                       6. 主流程控制模块
    # =================================================================
    
    async def run(self):
        """运行自动登录流程"""
        try:
            print("🚀 开始 IntraceX 自动登录流程...")
            
            # 步骤1：验证配置
            if not self.validate_config():
                return False
            
            # 步骤2：设置浏览器
            if not await self.setup_browser():
                return False
            
            # 步骤3：导航到登录页面并验证
            if not await self.navigate_to_login():
                return False
            
            # 第一步：验证登录页面
            print("\n📋 第一步：验证登录页面")
            login_page_verified = await self.verify_page(
                "https://intracex.de/auth/login", 
                "Einloggen", 
                "登录页面"
            )
            
            if login_page_verified:
                await self.take_screenshot("01_login_page.png", "登录页面")
            else:
                print("⚠️  未能正确跳转到登录页面，继续尝试登录...")
                await self.take_screenshot("01_login_page_error.png", "登录页面错误")
            
            # 步骤4：执行登录操作
            if not await self.perform_login():
                return False
            
            # 第四步：验证登录成功并到达首页
            print("\n🏠 第四步：验证首页")
            await self.page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(8)  # 确保页面完全加载
            
            # 验证首页
            home_page_verified = await self.verify_page(
                "https://intracex.de/",
                "Willkommen bei IntraceX",
                "首页"
            )
            
            if home_page_verified:
                print("✅ 登录成功！已到达首页")
                await self.take_screenshot("02_home_page.png", "登录成功首页")
                
                # 第五步：跳转到Minecraft页面
                print("\n🎮 第五步：跳转到Minecraft页面")
                print(f"正在跳转到目标页面: {self.target_url}")
                
                await self.page.goto(self.target_url, wait_until='networkidle')
                await self.page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(8)  # 等待页面完全加载
                
                # 第六步：验证Minecraft页面
                print("\n🎯 第六步：验证Minecraft页面")
                minecraft_page_verified = await self.verify_page(
                    "https://intracex.de/minecraft",
                    "Meine Minecraft Server",
                    "Minecraft服务器页面"
                )
                
                if minecraft_page_verified:
                    print("🎉 完美！成功进入 Minecraft 服务器页面！")
                    await self.take_screenshot("03_minecraft_page.png", "Minecraft页面成功")
                    
                    # 第七步：获取服务器信息
                    print("\n📊 第七步：获取服务器信息")
                    
                    # 获取服务器ID
                    server_id = await self.get_server_id()
                    if server_id:
                        print(f"✅ 成功获取服务器ID: {server_id}")
                        self.server_id = server_id
                    else:
                        print("⚠️  未能获取服务器ID，请检查页面结构")
                    
                    # 获取服务器到期时间
                    old_expiry_date = await self.get_expiry_date()
                    
                    if old_expiry_date:
                        print(f"✅ 成功获取旧到期时间: {old_expiry_date}")
                        # 保存到期时间到实例变量，供后续使用
                        self.old_expiry_date = old_expiry_date
                    else:
                        print("⚠️  未能获取到期时间，请检查页面结构")
                    
                    # 第八步：检查续期按钮状态
                    print("\n🔄 第八步：检查续期按钮状态")
                    can_extend = await self.check_extend_button()
                    
                    # 保存续期状态到实例变量
                    self.can_extend = can_extend
                    
                    if can_extend:
                        print("🎉 服务器可以续期！")
                        # 续期结果将在续期验证后设置
                    else:
                        print("⏳ 服务器暂时不可续期")
                        self.renewal_result = "unexpired"
                    
                    print("\n✅ 登录流程完全成功！")
                else:
                    print("⚠️  到达了目标页面，但内容验证失败")
                    await self.take_screenshot("03_minecraft_page_error.png", "Minecraft页面验证失败")
                    
            else:
                print("❌ 登录失败或未能到达首页")
                await self.take_screenshot("02_login_failed.png", "登录失败")
                
                # 检查是否有错误消息
                error_selectors = [
                    '.error',
                    '.alert-danger',
                    '.error-message',
                    '[class*="error"]'
                ]
                
                for selector in error_selectors:
                    try:
                        error_element = await self.page.query_selector(selector)
                        if error_element:
                            error_text = await error_element.text_content()
                            if error_text and error_text.strip():
                                print(f"❌ 发现错误消息: {error_text}")
                                break
                    except:
                        continue
            
            # 保持浏览器打开一段时间以便查看结果
            if not self.headless:
                print(f"浏览器将保持打开状态 10 秒...")
                await asyncio.sleep(10)
            
            print("🎉 IntraceX 自动登录流程完成！")
            return True
            
        except Exception as e:
            print(f"❌ 自动登录流程出错: {e}")
            # 尝试截图保存现场
            try:
                await self.take_screenshot("login_error.png", "登录错误")
            except:
                pass
            return False
        
        finally:
            await self.cleanup()


# =====================================================================
#                          主程序入口
# =====================================================================

async def main():
    """主函数"""
    print("=" * 60)
    print("IntraceX 自动登录脚本 - Playwright版本")
    print("基于 Playwright + stealth")
    print("=" * 60)
    print()
    
    # 显示当前配置
    print("📋 当前配置:")
    print(f"   IntraceX邮箱: {LOGIN_EMAIL}")
    print(f"   IntraceX密码: {'*' * len(LOGIN_PASSWORD)}")
    print(f"   目标网站: {TARGET_URL}")
    print(f"   无头模式: {'是' if USE_HEADLESS else '否'}")
    if IS_GITHUB_ACTIONS:
        print(f"   运行环境: GitHub Actions")
    else:
        print(f"   运行环境: 本地")
    print()
    
    # 确认配置
    if not LOGIN_EMAIL or not LOGIN_PASSWORD:
        print("❌ 请在配置变量中填写用户名和密码！")
        return
    
    print("🚀 配置验证通过，自动开始登录...")
    
    # 创建并运行自动登录器
    auto_login = IntraceXAutoLogin()
    success = await auto_login.run()
    
    if success:
        print("✅ 登录流程执行成功！")
    else:
        print("❌ 登录流程执行失败！")
    
    # 生成README文件
    auto_login.generate_readme()


if __name__ == "__main__":
    asyncio.run(main())