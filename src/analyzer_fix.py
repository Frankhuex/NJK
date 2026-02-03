from typing import List
from peewee import fn
from services.msg_analyzer import msg_analyzer
from models.message import Message
from models.msg_word import MsgWord
from models.word import Word
from models.msg_topic import MsgTopic
from models.topic import Topic  # 确保导入了 Topic
import asyncio

async def repair_hallucinated_words():
    """
    修复 AI 幻觉产生的错误分词记录
    1. 查出包含“爷爷”或“你居垦”但在原文中并不存在这些词的消息 ID
    2. 删除这些消息的所有词汇和话题关联
    3. 重新调用分析器
    4. 清除无关联的孤立 Word 和 Topic
    """
    print("正在查找受幻觉影响的错误消息...")

    # 1. 用 Peewee 查出对应的 message_id
    bad_messages_query = (Message
                         .select(Message.message_id)
                         .distinct()
                         .join(MsgWord)
                         .join(Word)
                         .where(
                             ((Word.name == '你居垦') & (~Message.text.contains('你居垦'))) |
                             ((Word.name == '爷爷') & (~Message.text.contains('爷爷')))
                         ))
    
    target_ids = [m.message_id for m in bad_messages_query]
    
    if not target_ids:
        print("未发现匹配的幻觉错误数据，无需修复。")
    else:
        print(f"发现 {len(target_ids)} 条错误消息，准备清理并重新分析...")

        # 2. 删除这些 message_id 关联的所有词汇和话题
        delete_words = MsgWord.delete().where(MsgWord.message << target_ids).execute()
        delete_topics = MsgTopic.delete().where(MsgTopic.message << target_ids).execute()
        
        print(f"已清理旧数据: 删除了 {delete_words} 条词汇关联, {delete_topics} 条话题关联。")

        # 3. 获取 Message 对象并重新分析
        messages_to_fix = list(Message.select().where(Message.message_id << target_ids))
        
        if messages_to_fix:
            success_count = await msg_analyzer.analyze_given_msgs(messages_to_fix, concurrency=10)
            print(f"成功重新分析了 {success_count} 条消息。")

        # 4. 清除没有任何关联记录的孤立 Word 和 Topic
        print("正在清理孤立的词汇和话题...")
    
    # 清理无关联的 Word
    orphan_words_del = Word.delete().where(
        ~fn.EXISTS(MsgWord.select().where(MsgWord.word == Word.id))
    ).execute()
    
    # 清理无关联的 Topic
    orphan_topics_del = Topic.delete().where(
        ~fn.EXISTS(MsgTopic.select().where(MsgTopic.topic == Topic.id))
    ).execute()

    print(f"清理完成: 删除了 {orphan_words_del} 个孤立词汇, {orphan_topics_del} 个孤立话题。")

# 调用示例：
if __name__ == '__main__':
    asyncio.run(repair_hallucinated_words())