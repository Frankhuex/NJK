import asyncio
from dotenv import load_dotenv
import os
from typing import Any, List, Dict, Pattern, Tuple
from concurrent.futures import ThreadPoolExecutor  # 新增：提前导入线程池
from openai import OpenAI
import random

load_dotenv()
api_key = os.getenv('API_KEY')
base_url = os.getenv('BASE_URL')
paid_model_name = os.getenv('MODEL_NAME')
free_model_name = os.getenv('FREE_MODEL_NAME')
print(api_key is not None, base_url is not None, paid_model_name is not None)


class AIClient:
    def __init__(self, model_name: str|None):
        self.client: OpenAI = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        # 关键修改1：不再提前获取loop，只初始化线程池（全局唯一）
        self.executor = ThreadPoolExecutor(max_workers=5)  # 控制最大并发数
        self.model_name = model_name

    async def summary(self, sys_prompt: Any, prompt: Any, temperature: float = -1) -> str|None:
        print(f"model_name: {self.model_name}")
        # 定义同步执行的AI调用函数
        def _sync_summary():
            try:
                print(f"temperature: {temperature}")
                if not self.model_name:
                    raise ValueError("未设置AI模型")
                if temperature < 0:
                    response = self.client.chat.completions.create(
                        model = self.model_name,
                        messages=[
                            {
                                "role": "system", 
                                "content": sys_prompt
                            },
                            {
                                "role": "user", 
                                "content": prompt
                            }
                        ],
                        stream=False,
                    )
                else:
                    response = self.client.chat.completions.create(
                        model = self.model_name,
                        messages=[
                            {
                                "role": "system", 
                                "content": sys_prompt
                            },
                            {
                                "role": "user", 
                                "content": prompt
                            }
                        ],
                        stream=False,
                        temperature=temperature
                    )
                return response.choices[0].message.content
            except Exception as e:
                print(f"AI调用出错: {str(e)}")
                return f"处理失败：{str(e)}"
        
        # 关键修改2：动态获取当前活跃的事件循环
        loop = asyncio.get_running_loop()
        # 用当前循环执行线程池任务（避免跨循环）
        return await loop.run_in_executor(self.executor, _sync_summary)
    



ai_client = AIClient(paid_model_name)
ai_client_free = AIClient(free_model_name)