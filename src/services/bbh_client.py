from typing import List,Dict,Any
import requests
from services.ai_client import ai_client

bbh_url = "http://106.13.161.72:10000/api/"

class BBHClient:
    def __init__(self):
        pass
    async def plaza_cmd(self)->str:
        url = bbh_url + "books/plaza"
        response: Dict[str,Any] = requests.get(url).json()
        if not response['success']:
            return "获取失败"
        books: List[Dict[str,Any]] = response["data"]
        allreads: List[str] = []
        alledits: List[str] = []
        for book in books:
            id_title = f"{book['id']}. {book['title']}"
            if book['scope'] == 'ALLREAD':
                allreads.append(id_title)
            elif book['scope'] == 'ALLEDIT':
                alledits.append(id_title)
        allreads_str = "\n".join(allreads)
        alledits_str = "\n".join(alledits)
        return f"只读:\n{allreads_str}\n\n可编辑:\n{alledits_str}"
    
    async def book_cmd(self, book_id: int)->str:
        book = await self.get_book_by_id(book_id)
        book_str: str = f"{book['id']}. {book['title']}" if book else f"获取{book_id}号书失败"

        paragraphs = await self.get_paragraphs_by_book_id(book_id)
        if paragraphs:
            paras_str = self.paras_to_str(paragraphs)
        else:
            paras_str = "获取段落失败"
        return book_str + "\n" + "-"*10 + "\n" + paras_str
    
    async def paragraph_cmd(self, book_id: int, para_left_index: int, para_right_index: int)->str:
        paras = await self.get_paragraphs_by_book_id(book_id)
        if not paras:
            return "获取段落失败"
        if para_left_index<1 or para_left_index>len(paras) or para_right_index<1 or para_right_index>len(paras) or para_left_index>para_right_index:
            return f"段落索引错误"
        para_contents = [(para['author'],para['content']) for para in paras][para_left_index-1:para_right_index]
        para_str = "\n\n".join([f"{i+para_left_index}. {para[0]}\n{para[1]}" for i,para in enumerate(para_contents)])
        return para_str
    
    async def add_paragraph_cmd(self, book_id: int, author: str, content: str)->str:
        paras = await self.get_paragraphs_by_book_id(book_id)
        if not paras:
            return "获取前段落失败"
        prev_para_id = paras[-1]['id']
        new_para = await self.add_new_paragraph(prev_para_id, author, content)
        if not new_para:
            return "接龙失败"
        return self.paras_to_str(paras) + f"\n接龙成功: \n{len(paras)+1}. {new_para['author']}"

    
    
    async def ai_writing_cmd(self, book_id: int) -> str:
        paras = await self.get_paragraphs_by_book_id(book_id)
        if not paras:
            return "获取前段落失败"
        prev_para_id = paras[-1]['id']
        para_contents = [(para['author'],para['content']) for para in paras]

        prompt = f"""
        这是一篇正在编写中的小说的每一个段落：{para_contents}\n其中author字段含义请自行视情况判断，有时候为作者，有时候为段标题，content字段则是段落正文内容。
        现在请你理解前文，然后往下接一段。输出格式要求为json格式，一个字段\"author\"，一个字段\"content\"，字段值必须为字符串。
        """
        ai_response = await ai_client.summary(prompt)
        if not ai_response:
            return "AI调用失败"
        print(ai_response)
        if ai_response.startswith("```json"):
            ai_response = ai_response[8:-3]
        try:
            ai_response_dict = eval(ai_response)
        except:
            return "AI回答解析失败"
        if not isinstance(ai_response_dict, dict) or "author" not in ai_response_dict or "content" not in ai_response_dict:
            return "AI回答格式错误"
        author = ai_response_dict["author"]
        content = ai_response_dict["content"]

        new_para = await self.add_new_paragraph(prev_para_id, author, content)
        if not new_para:
            return "接龙失败"
        return self.paras_to_str(paras) + f"\n接龙成功: \n{len(paras)+1}. {new_para['author']}"
        





    ####################################
    # Private

    async def get_book_by_id(self, book_id: int) -> Dict[str,Any]|None:
        url_book = bbh_url + f"book/{book_id}"
        response: Dict[str,Any] = requests.get(url_book).json()
        if not response['success']:
            print(f"获取书籍{book_id}失败: {response['errorMsg']}")
            return None
        book: Dict[str,Any] = response["data"]
        return book
    
    async def get_paragraphs_by_book_id(self, book_id: int) -> List[Dict[str,Any]]|None:
        url_paras = bbh_url + f"book/{book_id}/paragraphs"
        response: Dict[str,Any] = requests.get(url_paras).json()
        if not response['success']:
            print(f"获取段落失败: {response['errorMsg']}")
            return None
        paragraphs: List[Dict[str,Any]] = response["data"]
        return paragraphs[1:-1]
    
    async def add_new_paragraph(self, prev_para_id: int, author: str, content: str) -> Dict[str,Any]|None:
        url_add_para = bbh_url + "paragraph"
        data = {"author": author, "content": content, "prevParaId": prev_para_id}
        response: Dict[str,Any] = requests.post(url_add_para, json=data).json()
        if not response['success']:
            print(f"添加段落失败: {response['errorMsg']}")
            return None
        return response['data']
    
    def paras_to_str(self, paras: List[Dict[str,Any]]) -> str:
        return "\n".join([str(i+1) + ". " + para['author'] for i,para in enumerate(paras)])

    
    
        


bbh_client = BBHClient()


