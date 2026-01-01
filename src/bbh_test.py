from services.bbh_client import bbh_client
import asyncio
async def test():
    
    print(await bbh_client.plaza_cmd())
    print(await bbh_client.book_cmd(27))
    print(await bbh_client.paragraph_cmd(27, 2, 2))
    print(await bbh_client.paragraph_cmd(27, 16, 17))
    print(await bbh_client.paragraph_cmd(27, 16, 17))
    print(await bbh_client.add_paragraph_cmd(36, "apple", "hello world"))
    print(await bbh_client.ai_writing_cmd(15))

if __name__ == '__main__':
    asyncio.run(test())