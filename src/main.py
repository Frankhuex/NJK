import asyncio
from datetime import datetime
import json
from websockets import serve
from websockets.asyncio.server import ServerConnection
from websockets.typing import Data
# from pymongo import MongoClient, database, collection
from typing import Any, List, Dict
# from services.msg_handler import MsgHandler
# from services.duplicate_detector import DuplicateDetector
from configs.pgdb import pgdb
from models.message import Message
from models.user import User
from models.group import Group
from services.msg_handler import msg_handler
import traceback

# MongoDB
group_list: List[int] = [897830548,979088841,1050660050,665074632,238872980,876274089]

# client: MongoClient = MongoClient("mongodb://localhost:27017")
# mongodb: database.Database = client["NJK"]
# collections: Dict[int, collection.Collection] = {}
# collections_img: Dict[int, collection.Collection] = {}
# for group_id in group_list:
#     collections[group_id] = mongodb[str(group_id)]
#     collections_img[group_id] = mongodb[f"hash_{group_id}"]




# msg_handler: MsgHandler = MsgHandler()
# duplicate_detector: DuplicateDetector = DuplicateDetector()

self_response_queue: asyncio.Queue[Dict[str,Any]] = asyncio.Queue()


async def handle_websocket(websocket: ServerConnection) -> None:
    client_address = websocket.remote_address
    connect_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n【新连接】 {connect_time} - 客户端地址: {client_address}")

    # 存储当前连接的活跃任务，避免内存泄漏
    active_tasks = set()

    try:
        async for message in websocket:
            # 核心修改：把消息处理逻辑封装成异步任务，立即提交，不等待
            task = asyncio.create_task(
                process_message(message, websocket, client_address)
            )
            active_tasks.add(task)
            # 任务完成后自动从集合中移除
            task.add_done_callback(active_tasks.discard)
            
    except Exception as e:
        print(f"【连接异常】 {client_address} - {str(e)}")
    finally:
        # 可选：等待未完成的任务结束后再关闭连接
        if active_tasks:
            print(f"【等待任务】 {client_address} 还有 {len(active_tasks)} 个任务未完成")
            await asyncio.gather(*active_tasks, return_exceptions=True)
        print(f"【连接关闭】 {client_address}")

# 新增：单独的消息处理函数（封装所有分支逻辑）
async def process_message(message: Data, websocket: ServerConnection, client_address: tuple) -> None:
    try:
        event: Any = json.loads(message)
        
        # 分支1：群消息 + LLM处理
        if event.get("post_type") == "message" and event.get("message_type") == "group":
            if event["group_id"] in group_list:
                print(f"【处理LLM任务】 {client_address} - 消息ID: {event.get('message_id')}")
                response: Dict[str,Any]|None = await msg_handler.handle_summary(event)
                if response: 
                    await websocket.send(json.dumps(response))
                    print(f"【发送LLM响应】 {client_address} - 消息ID: {event.get('message_id')}")
                    response["time"]=datetime.now()
                    await self_response_queue.put(response)
                    print(f"未存储的自己消息数：{self_response_queue.qsize()}")

                # response_img_detect: Dict[str,Any]|None = duplicate_detector.handle_detect(event, collections_img[event["group_id"]])
                # if response_img_detect:
                #     await websocket.send(json.dumps(response_img_detect))
                #     print(f"【发送图片去重响应】 {client_address} - 消息ID: {event.get('message_id')}")
        
        # 分支2：notice通知（纯文本回复，无阻塞）
        elif event.get("post_type") == "notice" and event.get("target_id") == event.get("self_id"):
            group_id = event["group_id"]
            response = {
                "action": "send_group_msg",
                "params": {
                    "group_id": group_id,
                    "message": f"灰色中分已然绽放"
                }
            }
            print(f"【处理Notice】 {client_address} - 群ID: {group_id}")
            await websocket.send(json.dumps(response))
            print(f"【发送Notice响应】 {client_address} - 群ID: {group_id}")
            
            response["time"]=datetime.now()
            await self_response_queue.put(response)
            print(f"未存储的自己消息数：{self_response_queue.qsize()}")

        elif event.get("status")=="ok" and event.get("retcode")==0 and "data" in event and "message_id" in event["data"]:
            print(f"【处理自己消息存储】 {client_address} - 消息ID: {event['data']['message_id']}")
            self_response: Dict[str,Any] = await self_response_queue.get()
            # await save_self_msg(self_response, event, mongodb[str(self_response["params"]["group_id"])])
            await save_self_msg_pg(self_response, event)
            print(f"【完成自己消息存储】 {client_address} - 消息ID: {event['data']['message_id']}")
            print(f"未存储的自己消息数：{self_response_queue.qsize()}")
            
    except Exception as e:
        print(traceback.format_exc())


# async def save_self_msg(response: Dict[str,Any], response_back: Dict[str,Any]|None, collection: collection.Collection) -> bool:
#     if not response_back:
#         print("响应消息为空，未存储自己消息")
#         return False
#     raw_message:str = response["params"]["message"]
#     new_message = {
#         "群友": "你居垦",
#         "群友id": 1558109748,
#         "发言": raw_message,
#         "消息id": response_back["data"]["message_id"],
#         "时间": response["time"]
#     }
#     collection.insert_one(new_message)

#     print("已存储自己消息到mongo")
#     return True


async def save_self_msg_pg(response: Dict[str,Any], response_back: Dict[str,Any]|None) -> bool:
    if not response_back:
        print("响应消息为空，未存储自己消息")
        return False
    message_id=str(response_back["data"]["message_id"])
    user = User.get_or_create(user_id="1558109748", defaults={"nickname": "你居垦"})[0]
    group = Group.get_or_create(group_id=str(response["params"]["group_id"]), defaults={"group_name": str(response["params"]["group_id"])})[0]
    message = Message.create(
        message_id=str(message_id),
        time=response["time"],
        sender=user,
        group=group,
        text=response["params"]["message"],
        raw_json=json.dumps(response["params"]["message"])
    )
    print(f"已存储自己消息{message_id}到pg")
    return True


async def main():
    async with serve(handle_websocket, "0.0.0.0", 11004):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())