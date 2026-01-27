from services.msg_analyzer import msg_analyzer
from models.group import Group
import asyncio


async def main():
    hard_words = ['[face]','我','?','.','[][face][1][33][4]',
                  'jiojf 青春有你居垦你居垦你居垦你居垦jiwofjoi,iwjfo"")(*&^%$#$%^&23f3*(*&^%$[saf32ff你居垦f2n2][][][]}{}{[}23904823904oih}{}{}{}{]}{(*&^&)}]}))',
                  'gemini找到了我的问题：我的提示词给了一个例句：“我 是 你居垦 的 爷爷”',
                  '[]你居垦[[]]'
                  ]
    for w in hard_words:
        words = msg_analyzer.segment_words_jieba(w)
        print(words)

if __name__ == '__main__':
    # asyncio.run(msg_analyzer.get_group_report_with_auto_analyze(Group.get(Group.group_id == '1050660050'),100,5))
    asyncio.run(main())