"""
触发器/定时任务模块
支持定时自动发布小红书帖子
"""
import os
import schedule
import time
from datetime import datetime
from typing import Callable, Optional
from dotenv import load_dotenv

load_dotenv()


class TriggerManager:
    """触发器管理器"""
    
    def __init__(self, callback: Callable):
        """
        初始化触发器
        
        Args:
            callback: 触发时调用的函数
        """
        self.callback = callback
        self.enabled = os.getenv("AUTO_POST_ENABLED", "true").lower() == "true"
        self.interval_hours = int(os.getenv("POST_INTERVAL_HOURS", "24"))
    
    def start_scheduler(self):
        """启动定时任务"""
        if not self.enabled:
            print("自动发布功能已禁用")
            return
        
        # 设置定时任务
        schedule.every(self.interval_hours).hours.do(self._execute_callback)
        
        print(f"定时任务已启动，每{self.interval_hours}小时执行一次")
        print(f"下次执行时间: {schedule.next_run()}")
        
        # 立即执行一次（可选）
        # self._execute_callback()
        
        # 运行调度器
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def _execute_callback(self):
        """执行回调函数"""
        try:
            print(f"\n[{datetime.now()}] 触发定时任务...")
            result = self.callback()
            print(f"[{datetime.now()}] 任务完成: {result}")
        except Exception as e:
            print(f"[{datetime.now()}] 任务执行失败: {str(e)}")
    
    def trigger_now(self):
        """立即触发一次"""
        self._execute_callback()
    
    def set_schedule(self, interval_hours: int):
        """设置发布间隔"""
        self.interval_hours = interval_hours
        schedule.clear()
        schedule.every(interval_hours).hours.do(self._execute_callback)
        print(f"已更新发布间隔为每{interval_hours}小时")


class WebhookTrigger:
    """Webhook触发器（用于外部调用）"""
    
    def __init__(self, callback: Callable, port: int = 8080):
        """
        初始化Webhook触发器
        
        Args:
            callback: 触发时调用的函数
            port: 监听端口
        """
        self.callback = callback
        self.port = port
    
    def start_server(self):
        """启动Webhook服务器"""
        from flask import Flask, request, jsonify
        
        app = Flask(__name__)
        
        @app.route('/trigger', methods=['POST'])
        def trigger():
            try:
                data = request.json or {}
                result = self.callback(**data)
                return jsonify({
                    "success": True,
                    "message": "触发成功",
                    "result": result
                })
            except Exception as e:
                return jsonify({
                    "success": False,
                    "message": str(e)
                }), 500
        
        @app.route('/health', methods=['GET'])
        def health():
            return jsonify({"status": "ok"})
        
        print(f"Webhook服务器已启动，监听端口 {self.port}")
        print(f"触发地址: http://localhost:{self.port}/trigger")
        app.run(host='0.0.0.0', port=self.port)
