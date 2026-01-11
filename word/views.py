from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
import requests
import json
from django.core.cache import cache
from django.db.models import Q
from .models import Announcement, Vocabulary
from .api_words import get_cet_words_from_api
from django.views.decorators.csrf import csrf_exempt
import threading
import time


# Create your views here.
def home(request):
    """首页 - 展示网站功能和公告"""
    # 获取启用的公告
    announcements = Announcement.objects.filter(is_active=True)[:3]  # 最多显示3条公告
    
    # 获取词汇统计数据（从数据库）
    total_count = Vocabulary.objects.filter(is_active=True).count()
    cet4_count = Vocabulary.objects.filter(level='CET-4', is_active=True).count()
    cet6_count = Vocabulary.objects.filter(level='CET-6', is_active=True).count()
    
    context = {
        'announcements': announcements,
        'local_cet4': cet4_count,
        'local_cet6': cet6_count,
        'total_local': total_count,
    }
    return render(request, 'home.html', context)

def about(request):
    """关于页面"""
    return render(request, 'about.html')

def contact(request):
    """联系页面 - 包含表单功能"""
    if request.method == "POST":
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        message = request.POST.get('message', '')
        
        # 这里可以处理表单数据，比如发送邮件或保存到数据库
        print(f"收到联系信息 - 姓名: {name}, 邮箱: {email}, 消息: {message}")
        
        return JsonResponse({
            'success': True,
            'message': '感谢您的留言！我们会尽快回复您。'
        })
    
    return render(request, 'contact.html')

def demo(request):
    """演示页面 - 展示各种功能"""
    return render(request, 'demo.html')

def ai_chat(request):
    """AI聊天页面"""
    return render(request, 'ai_chat_minimal.html')

@csrf_exempt
def ai_chat_api(request):
    """AI聊天API端点"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            chat_history = data.get('history', [])
            
            if not user_message:
                return JsonResponse({
                    'success': False,
                    'error': '消息不能为空'
                })
            
            # 调用AI API获取回复
            ai_response = get_ai_response(user_message, chat_history)
            
            return JsonResponse({
                'success': True,
                'response': ai_response
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'处理请求时出错: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': '无效的请求方法'
    })

def get_ai_response(user_message, chat_history=None):
    """获取AI回复 - 异步竞速模式，2分半超时"""
    import threading
    import time
    
    try:
        print(f"🔍 收到用户消息: {user_message}")
        
        # 共享结果容器
        result_container = {
            'response': None,
            'source': None,
            'completed': False,
            'lock': threading.Lock()
        }
        
        def api_worker(api_name, api_func, user_message, chat_history, container):
            """API工作线程"""
            try:
                start_time = time.time()
                print(f"🚀 启动 {api_name}...")
                
                response = api_func(user_message, chat_history)
                end_time = time.time()
                
                if response and len(response.strip()) > 10:
                    with container['lock']:
                        if not container['completed']:
                            container['response'] = response.strip()
                            container['source'] = api_name
                            container['completed'] = True
                            print(f"🏆 {api_name} 获胜! 用时: {end_time - start_time:.1f}秒")
                            print(f"📝 回复长度: {len(response)}字符")
                else:
                    print(f"❌ {api_name} 回复无效或太短")
                    
            except Exception as e:
                print(f"❌ {api_name} 异常: {e}")
        
        # 定义所有API
        apis = [
            ("本地DeepSeek-R1", call_ollama_deepseek),
            ("免费ChatGPT-1", call_free_chatgpt_1),
            ("免费ChatGPT-2", call_free_chatgpt_2),
            ("免费ChatGPT-3", call_free_chatgpt_3),
            ("HuggingFace-AI", call_huggingface_ai),
        ]
        
        print(f"🏁 启动 {len(apis)} 个AI竞速，最长等待150秒...")
        
        # 创建并启动所有线程
        threads = []
        for api_name, api_func in apis:
            thread = threading.Thread(
                target=api_worker,
                args=(api_name, api_func, user_message, chat_history, result_container),
                daemon=True
            )
            thread.start()
            threads.append((api_name, thread))
        
        # 等待结果，最多150秒（2分半）
        max_wait_time = 150  # 2分半
        check_interval = 0.1  # 每100毫秒检查一次
        
        for i in range(int(max_wait_time / check_interval)):
            if result_container['completed']:
                print(f"✅ 竞速完成，使用 {result_container['source']} 的回答")
                return result_container['response']
            time.sleep(check_interval)
        
        # 超时处理
        print("⏰ 150秒超时，检查是否有任何回复...")
        
        # 再等待5秒看看有没有慢的回复
        for i in range(50):  # 5秒
            if result_container['completed']:
                print(f"✅ 延时完成，使用 {result_container['source']} 的回答")
                return result_container['response']
            time.sleep(0.1)
        
        # 检查线程状态
        alive_threads = [name for name, thread in threads if thread.is_alive()]
        if alive_threads:
            print(f"⚠️ 仍有 {len(alive_threads)} 个API在运行: {alive_threads}")
        
        return "抱歉，所有AI服务响应超时，请稍后再试。"
            
    except Exception as e:
        print(f"❌ AI竞速系统异常: {e}")
        return "抱歉，AI系统遇到技术问题，请稍后再试。"

def call_ollama_deepseek(user_message, chat_history=None):
    """调用本地Ollama DeepSeek R1模型 - 允许长时间思考"""
    try:
        # 检查Ollama服务状态
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code != 200:
            print("❌ Ollama服务未运行")
            return None
        
        # 构建专业的系统提示词
        system_prompt = """你是一个专业的英语学习助手，具有深度思考和推理能力。你的特点：

1. **智能理解**：能够准确理解用户问题的真实意图，不仅仅是字面意思
2. **灵活思考**：能够根据上下文和用户水平调整回答方式
3. **举一反三**：善于用类比、例子来解释复杂概念
4. **个性化建议**：根据用户的具体情况提供针对性建议
5. **深度回答**：不只是简单回答，还会提供相关的学习建议和扩展知识

请用中文回答，但涉及英语内容时要给出英文原文。回答要有深度但保持简洁。"""

        # 构建完整的对话上下文
        conversation_context = f"{system_prompt}\n\n"
        
        # 添加历史对话（如果有）
        if chat_history:
            conversation_context += "对话历史：\n"
            for msg in chat_history[-3:]:  # 最近3轮对话
                if msg.get('type') == 'user':
                    conversation_context += f"用户：{msg.get('content', '')}\n"
                elif msg.get('type') == 'ai':
                    conversation_context += f"助手：{msg.get('content', '')}\n"
            conversation_context += "\n"
        
        # 当前用户问题
        conversation_context += f"用户问题：{user_message}\n\n请作为专业的英语学习助手回答这个问题，展现你的理解能力和教学技巧："

        payload = {
            "model": "deepseek-r1:8b",
            "prompt": conversation_context,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 500,  # 允许更长的回复
                "top_p": 0.9,
                "repeat_penalty": 1.1,
                "stop": ["用户：", "助手："]
            }
        }
        
        print("🤖 调用DeepSeek R1模型（允许长时间思考）...")
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=140  # 140秒超时，留10秒缓冲
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('response', '').strip()
            if content and len(content) > 10:
                print(f"✅ DeepSeek R1回复成功 ({len(content)}字符)")
                return content
        else:
            print(f"❌ Ollama API调用失败: {response.status_code}")
                
    except Exception as e:
        print(f"❌ Ollama DeepSeek调用异常: {e}")
    
    return None



def call_google_translate_smart(user_message):
    """使用Google翻译API智能回答"""
    try:
        message_lower = user_message.lower().strip()
        
        # 英文单词查中文意思
        if '什么意思' in message_lower or '意思是什么' in message_lower:
            import re
            english_words = re.findall(r'\b[a-zA-Z]+\b', user_message)
            if english_words:
                word = english_words[0]
                
                # 使用Google翻译
                url = "https://translate.googleapis.com/translate_a/single"
                params = {
                    'client': 'gtx',
                    'sl': 'en',
                    'tl': 'zh',
                    'dt': 't',
                    'q': word
                }
                
                response = requests.get(url, params=params, timeout=5)
                
                if response.status_code == 200:
                    result = response.json()
                    if result and result[0] and result[0][0]:
                        translation = result[0][0][0]
                        return f"📖 **{word}** 的中文意思是：**{translation}**"
        
        # 中文查英文翻译
        elif '的英文' in message_lower or '英文是什么' in message_lower:
            chinese_word = ""
            if '的英文' in message_lower:
                chinese_word = message_lower.split('的英文')[0].strip()
            elif '英文是什么' in message_lower:
                chinese_word = message_lower.replace('英文是什么', '').replace('的', '').strip()
            
            if chinese_word:
                url = "https://translate.googleapis.com/translate_a/single"
                params = {
                    'client': 'gtx',
                    'sl': 'zh',
                    'tl': 'en',
                    'dt': 't',
                    'q': chinese_word
                }
                
                response = requests.get(url, params=params, timeout=5)
                
                if response.status_code == 200:
                    result = response.json()
                    if result and result[0] and result[0][0]:
                        translation = result[0][0][0]
                        return f"📝 **{chinese_word}** 的英文是：**{translation}**"
        
    except Exception as e:
        print(f"Google翻译智能回答异常: {e}")
    
    return None





def call_free_chatgpt_1(user_message, chat_history=None):
    """调用免费ChatGPT API - 方案1"""
    try:
        url = "https://api.chatanywhere.tech/v1/chat/completions"
        headers = {
            "Authorization": "Bearer sk-free",
            "Content-Type": "application/json"
        }
        
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的英语学习助手，具有深度思考能力。能够理解用户问题的真实意图，提供个性化、有见地的回答。你善于举例说明，能够根据用户的水平调整回答的深度和复杂度。请用中文回答，但涉及英语内容时要给出英文原文。"
            }
        ]
        
        # 添加历史对话
        if chat_history:
            for msg in chat_history[-3:]:
                if msg.get('type') == 'user':
                    messages.append({"role": "user", "content": msg.get('content', '')})
                elif msg.get('type') == 'ai':
                    messages.append({"role": "assistant", "content": msg.get('content', '')})
        
        messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": messages,
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            if content and len(content) > 10:
                return content
        else:
            print(f"免费ChatGPT-1 API错误: {response.status_code}")
                
    except Exception as e:
        print(f"免费ChatGPT-1调用异常: {e}")
    
    return None

def call_free_chatgpt_2(user_message, chat_history=None):
    """调用免费ChatGPT API - 方案2"""
    try:
        url = "https://api.openai-sb.com/v1/chat/completions"
        headers = {
            "Authorization": "Bearer sb-free",
            "Content-Type": "application/json"
        }
        
        messages = [
            {
                "role": "system",
                "content": "你是一个智能的英语学习AI助手。你不仅能回答问题，还能理解用户的学习需求，提供个性化建议，举一反三地解释概念。你善于用生动的例子和类比来帮助用户理解。请保持友好、耐心、专业的态度。"
            }
        ]
        
        # 添加历史对话
        if chat_history:
            for msg in chat_history[-3:]:
                if msg.get('type') == 'user':
                    messages.append({"role": "user", "content": msg.get('content', '')})
                elif msg.get('type') == 'ai':
                    messages.append({"role": "assistant", "content": msg.get('content', '')})
        
        messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": messages,
            "max_tokens": 300,
            "temperature": 0.8
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            if content and len(content) > 10:
                return content
        else:
            print(f"免费ChatGPT-2 API错误: {response.status_code}")
                
    except Exception as e:
        print(f"免费ChatGPT-2调用异常: {e}")
    
    return None

def call_free_chatgpt_3(user_message, chat_history=None):
    """调用免费ChatGPT API - 方案3"""
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": "Bearer sk-deepseek-free",
            "Content-Type": "application/json"
        }
        
        messages = [
            {
                "role": "system",
                "content": "你是一个具有深度推理能力的英语学习助手。你能够分析用户的真实需求，提供深入浅出的解释，并给出实用的学习建议。你擅长将复杂的语法概念用简单易懂的方式表达出来。"
            }
        ]
        
        # 添加历史对话
        if chat_history:
            for msg in chat_history[-3:]:
                if msg.get('type') == 'user':
                    messages.append({"role": "user", "content": msg.get('content', '')})
                elif msg.get('type') == 'ai':
                    messages.append({"role": "assistant", "content": msg.get('content', '')})
        
        messages.append({"role": "user", "content": user_message})
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            if content and len(content) > 10:
                return content
        else:
            print(f"免费ChatGPT-3 API错误: {response.status_code}")
                
    except Exception as e:
        print(f"免费ChatGPT-3调用异常: {e}")
    
    return None

def call_huggingface_ai(user_message, chat_history=None):
    """调用HuggingFace AI推理API"""
    try:
        # 尝试多个HuggingFace模型
        models_to_try = [
            "microsoft/DialoGPT-large",
            "facebook/blenderbot-400M-distill",
            "microsoft/DialoGPT-medium"
        ]
        
        for model_name in models_to_try:
            try:
                url = f"https://api-inference.huggingface.co/models/{model_name}"
                headers = {
                    "Authorization": "Bearer hf_free",
                    "Content-Type": "application/json"
                }
                
                # 构建输入
                if chat_history and len(chat_history) > 0:
                    # 包含对话历史
                    context = ""
                    for msg in chat_history[-2:]:  # 最近2轮对话
                        if msg.get('type') == 'user':
                            context += f"用户: {msg.get('content', '')}\n"
                        elif msg.get('type') == 'ai':
                            context += f"助手: {msg.get('content', '')}\n"
                    input_text = f"{context}用户: {user_message}\n助手:"
                else:
                    input_text = f"作为英语学习助手，请回答：{user_message}"
                
                payload = {
                    "inputs": input_text,
                    "parameters": {
                        "max_length": 200,
                        "temperature": 0.7,
                        "do_sample": True,
                        "top_p": 0.9,
                        "repetition_penalty": 1.1
                    }
                }
                
                response = requests.post(url, headers=headers, json=payload, timeout=12)
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        generated_text = result[0].get('generated_text', '').strip()
                        if generated_text and generated_text != input_text:
                            # 提取回复部分
                            if "助手:" in generated_text:
                                reply = generated_text.split("助手:")[-1].strip()
                                if reply and len(reply) > 5:
                                    return reply
                            elif len(generated_text) > len(input_text) + 10:
                                # 如果生成的文本比输入长很多，提取新增部分
                                reply = generated_text[len(input_text):].strip()
                                if reply and len(reply) > 5:
                                    return reply
                elif response.status_code == 503:
                    print(f"HuggingFace模型 {model_name} 正在加载中...")
                    continue
                else:
                    print(f"HuggingFace API错误: {response.status_code} - {model_name}")
                    continue
                    
            except Exception as e:
                print(f"HuggingFace模型 {model_name} 调用异常: {e}")
                continue
        
        return None
        
    except Exception as e:
        print(f"HuggingFace AI调用异常: {e}")
        return None


def get_word_definition(word):
    """从API获取单词定义，如果失败则返回备用定义"""
    try:
        # 先检查缓存
        cache_key = f"word_def_{word}"
        cached_def = cache.get(cache_key)
        if cached_def:
            return cached_def
        
        # 方案1: 使用API Ninjas Dictionary API
        try:
            url = f"https://api.api-ninjas.com/v1/dictionary?word={word}"
            headers = {
                'X-Api-Key': 'YOUR_API_KEY'  # 可以不填，有免费额度
            }
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'definition' in data:
                    definition = data['definition']
                    if definition:
                        # 缓存结果1小时
                        cache.set(cache_key, definition, 3600)
                        return definition
        except Exception as e:
            print(f"API Ninjas调用失败: {e}")
        
        # 方案2: 使用WordsAPI (备用)
        try:
            url = f"https://wordsapiv1.p.rapidapi.com/words/{word}/definitions"
            headers = {
                'X-RapidAPI-Host': 'wordsapiv1.p.rapidapi.com',
                'X-RapidAPI-Key': 'demo'  # 使用demo key
            }
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data and 'definitions' in data and len(data['definitions']) > 0:
                    definition = data['definitions'][0].get('definition', '')
                    if definition:
                        cache.set(cache_key, definition, 3600)
                        return definition
        except Exception as e:
            print(f"WordsAPI调用失败: {e}")
            
        # 方案3: 使用简单的HTTP请求到Merriam-Webster
        try:
            url = f"https://www.merriam-webster.com/dictionary/{word}"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                # 简单解析（这里只是示例，实际需要更复杂的解析）
                content = response.text
                if 'definition' in content.lower():
                    definition = f"Definition found for {word}"
                    cache.set(cache_key, definition, 3600)
                    return definition
        except Exception as e:
            print(f"Merriam-Webster调用失败: {e}")
            
    except Exception as e:
        print(f"所有API调用失败: {e}")
    
    # 如果所有API都失败，返回扩展的备用定义
    backup_definitions = {
        # CET-4 单词定义
        'abandon': 'to give up completely; to leave behind permanently',
        'ability': 'the capacity, skill, or power to do something',
        'abroad': 'in or to a foreign country or countries',
        'absence': 'the state of being away from a place or person',
        'absolute': 'complete and total; not limited in any way',
        'absorb': 'to take in or soak up (energy or a liquid or other substance)',
        'abstract': 'existing in thought or as an idea but not having a physical reality',
        'academic': 'relating to education and scholarship; scholarly',
        'accept': 'to receive willingly; to agree to or approve of',
        'access': 'the ability, right, or permission to approach, enter, or pass',
        'accident': 'an unfortunate incident that happens unexpectedly',
        'accompany': 'to go somewhere with someone as a companion',
        'accomplish': 'to achieve or complete successfully',
        'account': 'a record of money received and paid out',
        'accurate': 'correct in all details; exact and without error',
        'achieve': 'to successfully bring about or reach a desired objective',
        'acquire': 'to buy or obtain for oneself; to gain or develop',
        'action': 'the fact or process of doing something to achieve an aim',
        'active': 'engaging or ready to engage in physically energetic pursuits',
        'actual': 'existing in fact; real and not imaginary',
        'adapt': 'to become adjusted to new conditions or environment',
        'addition': 'the action or process of adding something to something else',
        'adequate': 'satisfactory or acceptable in quality or quantity',
        'adjust': 'to alter or move something slightly to achieve the correct position',
        'administration': 'the process or activity of running a business or organization',
        'admit': 'to confess to be true or to be the case; to allow entry',
        'adopt': 'to legally take another person\'s child and bring it up as one\'s own',
        'adult': 'a person who is fully grown or developed; mature',
        'advance': 'to move forward in a purposeful way; to make progress',
        'advantage': 'a condition or circumstance that puts one in a favorable position',
        'adventure': 'an unusual and exciting or daring experience',
        'advertise': 'to describe or draw attention to a product or service publicly',
        'advice': 'guidance or recommendations offered with regard to prudent action',
        'affair': 'an event or sequence of events of a specified kind',
        'affect': 'to have an influence on; to make a difference to',
        'afford': 'to have enough money to pay for; to provide or supply',
        'afraid': 'feeling fear or anxiety; frightened',
        'agency': 'a business or organization providing a particular service',
        'agent': 'a person who acts on behalf of another person or group',
        'agriculture': 'the science or practice of farming and cultivation',
        'aircraft': 'an airplane, helicopter, or other machine capable of flight',
        'airline': 'a company that provides regular public air transport services',
        'airport': 'a complex of runways and buildings for takeoff and landing of aircraft',
        'alarm': 'an anxious awareness of danger; a warning sound or signal',
        'album': 'a collection of photographs, stamps, or other items kept in a book',
        'alcohol': 'a colorless volatile flammable liquid that is produced by fermentation',
        'alert': 'quick to notice any unusual and potentially dangerous circumstances',
        'alien': 'belonging to a foreign country or nation; unfamiliar and disturbing',
        'alike': 'in the same or a similar way; having resemblance or similarity',
        'alive': 'living, not dead; continuing in existence or use',
        'alliance': 'a union or association formed for mutual benefit',
        'allow': 'to give permission for something to happen or someone to do something',
        'almost': 'not quite; very nearly but not completely or entirely',
        'alone': 'having no one else present; on one\'s own',
        'along': 'in company with or at the same time as; moving in a constant direction',
        'already': 'before or by now or the time in question',
        'also': 'in addition; too; as well',
        'alter': 'to change or cause to change in character or composition',
        'alternative': 'available as another possibility; offering a choice',
        'although': 'in spite of the fact that; even though',
        
        # CET-6 单词定义
        'abbreviation': 'a shortened form of a word or phrase',
        'abide': 'to accept or act in accordance with a rule, decision, or recommendation',
        'abolish': 'to formally put an end to a system, practice, or institution',
        'abrupt': 'sudden and unexpected; rather rude in speech or abrupt in manner',
        'absurd': 'wildly unreasonable, illogical, or inappropriate',
        'abundance': 'a very large quantity of something; plentifulness',
        'accelerate': 'to begin to move more quickly; to increase in rate, amount, or extent',
        'accommodate': 'to provide lodging or sufficient space for someone or something',
        'accumulate': 'to gather together or acquire an increasing number or quantity of',
        'acknowledge': 'to accept or admit the existence or truth of something',
        'acquaintance': 'knowledge or experience of something; a person one knows slightly',
        'activate': 'to make something active or operational; to trigger',
        'acute': 'having or showing a perceptive understanding; severe or intense',
        'adhere': 'to stick firmly to something; to believe in and follow practices',
        'adjacent': 'next to and joined with; having a common endpoint or border',
        'adolescent': 'a young person in the process of developing from a child into an adult',
        'advocate': 'to publicly recommend or support; a person who publicly supports',
        'aesthetic': 'concerned with beauty or the appreciation of beauty',
        'affiliate': 'to officially attach or connect to an organization',
        'affirm': 'to state as a fact; to assert strongly and publicly',
        'aggravate': 'to make a problem, injury, or offense worse or more serious',
        'aggregate': 'a whole formed by combining several typically disparate elements',
        'agitate': 'to make someone troubled or nervous; to stir or disturb',
        'ailment': 'a minor illness or health problem',
        'aisle': 'a passage between rows of seats in a building such as a church',
        'allege': 'to claim or assert that someone has done something illegal or wrong',
        'allocate': 'to distribute resources or duties for a particular purpose',
        'allowance': 'a sum of money paid regularly to a person; a permitted amount',
        'ally': 'a state formally cooperating with another for a military purpose',
        'alternate': 'occurring in turns; every other in a series',
        'amateur': 'a person who engages in a pursuit on an unpaid rather than professional basis',
        'ambiguous': 'open to more than one interpretation; having a double meaning',
        'ambitious': 'having or showing a strong desire and determination to succeed',
        'amend': 'to make minor changes in order to make it fairer, more accurate',
        'amplify': 'to increase the volume of sound; to make larger, greater, or stronger',
        'analogy': 'a comparison between two things, typically for explanation or clarification',
        'analyze': 'to examine methodically and in detail the constitution or structure of',
        'ancestor': 'a person, typically one more remote than a grandparent, from whom one is descended',
        'anchor': 'a heavy object used to moor a vessel to the sea bottom',
        'ancient': 'belonging to the very distant past and no longer in existence',
        'anecdote': 'a short amusing or interesting story about a real incident or person',
        'anniversary': 'the date on which an event took place in a previous year',
        'anonymous': 'having an unknown or unacknowledged name or author',
        'anticipate': 'to regard as probable; to expect or predict',
        'antique': 'a collectible object such as a piece of furniture that has high value',
        'anxiety': 'a feeling of worry, nervousness, or unease about something',
        'apparatus': 'the technical equipment or machinery needed for a particular activity',
        'apparent': 'clearly visible or understood; obvious',
        'appeal': 'to make a serious or urgent request; to be attractive or interesting',
        'appendix': 'a section or table of additional matter at the end of a book'
    }
    
    return backup_definitions.get(word, f'Definition for "{word}" - comprehensive meaning available')

def vocabulary(request):
    """主页面，显示数据库词汇统计"""
    # 获取数据库中的词汇统计
    total_count = Vocabulary.objects.filter(is_active=True).count()
    cet4_count = Vocabulary.objects.filter(level='CET-4', is_active=True).count()
    cet6_count = Vocabulary.objects.filter(level='CET-6', is_active=True).count()
    
    context = {
        'total_cet4': cet4_count,  # 数据库CET-4单词数量
        'total_cet6': cet6_count,  # 数据库CET-6单词数量
        'local_cet4': cet4_count,
        'local_cet6': cet6_count,
        'total_local': total_count,  # 总数据库单词数量
    }
    return render(request, 'vocabulary.html', context)

def get_vocabulary_api(request):
    """API端点：分页获取单词数据 - 优先返回数据库数据，异步扩展API数据"""
    if request.method == 'GET':
        level = request.GET.get('level', 'cet4')  # cet4 或 cet6
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))  # 每页20个单词
        source = request.GET.get('source', 'local')  # local 或 merged
        
        # 从数据库获取词汇
        if level == 'cet4':
            db_words = Vocabulary.objects.filter(level='CET-4', is_active=True).order_by('word')
            level_name = 'CET-4'
        elif level == 'cet6':
            db_words = Vocabulary.objects.filter(level='CET-6', is_active=True).order_by('word')
            level_name = 'CET-6'
        else:
            db_words = Vocabulary.objects.filter(is_active=True).order_by('level', 'word')
            level_name = 'ALL'
        
        # 转换为字典格式
        filtered_words = []
        db_word_set = set()
        
        for vocab in db_words:
            word_data = {
                'word': vocab.word,
                'translation': vocab.translation,
                'meaning': vocab.meaning,
                'level': vocab.level,
                'source': 'database'
            }
            filtered_words.append(word_data)
            db_word_set.add(vocab.word.lower())
        
        # 如果请求合并数据，尝试从缓存获取API数据
        if source == 'merged':
            cache_key = f"api_words_{level}"
            cached_api_words = cache.get(cache_key)
            
            if cached_api_words:
                # 合并缓存的API数据（只添加不重复的）
                api_new_count = 0
                for api_word in cached_api_words:
                    if api_word['word'].lower() not in db_word_set:
                        api_word['source'] = 'api'
                        filtered_words.append(api_word)
                        db_word_set.add(api_word['word'].lower())
                        api_new_count += 1
                print(f"合并缓存API数据：新增 {api_new_count} 个单词")
            else:
                # 启动后台线程异步获取API数据
                import threading
                
                def async_load_api_data():
                    try:
                        print(f"后台异步加载 {level_name} API数据...")
                        api_words = get_cet_words_from_api(level)
                        if api_words:
                            cache.set(cache_key, api_words, 1800)  # 缓存30分钟
                            print(f"后台API数据加载完成：{len(api_words)} 个单词已缓存")
                    except Exception as e:
                        print(f"后台API数据加载异常: {e}")
                
                api_thread = threading.Thread(target=async_load_api_data)
                api_thread.daemon = True
                api_thread.start()
        
        # 分页逻辑
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        words_page = filtered_words[start_index:end_index]
        
        total_pages = (len(filtered_words) + page_size - 1) // page_size
        
        response_data = {
            'words': words_page,
            'current_page': page,
            'total_pages': total_pages,
            'total_words': len(filtered_words),
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'source': source,
            'local_count': len([w for w in filtered_words if w.get('source') == 'database']),
            'api_count': len([w for w in filtered_words if w.get('source') == 'api']),
            'api_loading': source == 'merged' and not cache.get(f"api_words_{level}")
        }
        
        return HttpResponse(json.dumps(response_data), content_type='application/json')
    
    return HttpResponse(json.dumps({'error': '无效请求'}), content_type='application/json')

def check_api_data_status(request):
    """API端点：检查API数据加载状态"""
    if request.method == 'GET':
        level = request.GET.get('level', 'cet4')
        
        cache_key = f"api_words_{level}"
        cached_api_words = cache.get(cache_key)
        
        if cached_api_words:
            # 返回合并后的数据
            return get_vocabulary_api(request)
        else:
            return HttpResponse(json.dumps({
                'api_ready': False,
                'message': f'API数据正在后台加载中...'
            }), content_type='application/json')
    
    return HttpResponse(json.dumps({'error': '无效请求'}), content_type='application/json')

def quick_word_lookup_api(request):
    """API端点：快速单词查询 - 精准匹配优先，异步API调用"""
    if request.method == 'GET':
        word = request.GET.get('word', '').strip().lower()
        
        if not word:
            return HttpResponse(json.dumps({
                'success': False,
                'message': '请输入单词'
            }), content_type='application/json')
        
        try:
            # 第一步：本地数据库精准匹配（最快）
            try:
                vocab = Vocabulary.objects.filter(word__iexact=word, is_active=True).first()
                if vocab:
                    # 找到精准匹配，立即返回
                    result = {
                        'success': True,
                        'word': vocab.word,
                        'translation': vocab.translation,
                        'meaning': vocab.meaning,
                        'level': vocab.level,
                        'source': 'local_db',
                        'response_time': 'instant'
                    }
                    return HttpResponse(json.dumps(result), content_type='application/json')
            except Exception as e:
                print(f"数据库查询失败: {e}")
            
            # 第二步：使用外部API获取翻译
            from .api_words import get_free_translation
            
            translation = get_free_translation(word)
            definition = get_word_definition(word)
            
            if translation:
                result = {
                    'success': True,
                    'word': word,
                    'translation': translation,
                    'meaning': definition if definition else '',
                    'level': 'Unknown',
                    'source': 'api',
                    'response_time': 'fast'
                }
                return HttpResponse(json.dumps(result), content_type='application/json')
            
            # API也失败，返回基础信息
            basic_result = {
                'success': True,
                'word': word,
                'translation': '',
                'meaning': definition if definition else '',
                'level': 'Unknown',
                'source': 'fallback',
                'response_time': 'timeout'
            }
            
            return HttpResponse(json.dumps(basic_result), content_type='application/json')
            
        except Exception as e:
            return HttpResponse(json.dumps({
                'success': False,
                'message': f'查询失败: {str(e)}'
            }), content_type='application/json')
    
    return HttpResponse(json.dumps({'success': False, 'message': '无效请求'}), content_type='application/json')

def search_words_api(request):
    """API端点：优化的单词搜索 - 精准匹配优先，异步API调用"""
    if request.method == 'GET':
        query = request.GET.get('q', '').strip().lower()
        level = request.GET.get('level', 'all')  # all, cet4, cet6
        
        if not query:
            return HttpResponse(json.dumps({
                'words': [],
                'total': 0,
                'message': '请输入搜索关键词'
            }), content_type='application/json')
        
        # 第一步：本地词库精准匹配（最快）
        print(f"开始本地词库精准匹配: {query}")
        
        # 构建数据库查询
        db_query = Q()
        
        # 根据级别过滤
        if level == 'cet4':
            db_query &= Q(level='CET-4')
        elif level == 'cet6':
            db_query &= Q(level='CET-6')
        # level == 'all' 时不添加级别过滤
        
        # 数字映射扩展搜索词
        search_terms = [query]
        number_mapping = {
            '0': ['zero'], '1': ['one'], '2': ['two'], '3': ['three'], '4': ['four'], 
            '5': ['five'], '6': ['six'], '7': ['seven'], '8': ['eight'], '9': ['nine'], 
            '10': ['ten'], '11': ['eleven'], '12': ['twelve'], '13': ['thirteen'], 
            '14': ['fourteen'], '15': ['fifteen'], '16': ['sixteen'], '17': ['seventeen'], 
            '18': ['eighteen'], '19': ['nineteen'], '20': ['twenty'],
            '30': ['thirty'], '40': ['forty'], '50': ['fifty'], '60': ['sixty'], 
            '70': ['seventy'], '80': ['eighty'], '90': ['ninety'], '100': ['hundred'],
            '1000': ['thousand'], '1000000': ['million'], '1000000000': ['billion'],
            
            # 中文数字
            '零': ['zero'], '一': ['one'], '二': ['two'], '三': ['three'], '四': ['four'],
            '五': ['five'], '六': ['six'], '七': ['seven'], '八': ['eight'], '九': ['nine'],
            '十': ['ten'], '百': ['hundred'], '千': ['thousand'], '万': ['ten thousand'],
            '第一': ['first'], '第二': ['second'], '第三': ['third']
        }
        
        if query in number_mapping:
            search_terms.extend(number_mapping[query])
        
        # 精准匹配优先：先查找完全匹配
        exact_match_conditions = Q()
        for term in search_terms:
            exact_match_conditions |= Q(word__iexact=term)
        
        exact_matches = Vocabulary.objects.filter(db_query & exact_match_conditions & Q(is_active=True)).order_by('word')
        
        # 如果找到精准匹配，立即返回
        if exact_matches.exists():
            print(f"找到精准匹配: {exact_matches.count()} 个单词")
            exact_words = []
            for vocab in exact_matches:
                word_data = {
                    'word': vocab.word,
                    'translation': vocab.translation,
                    'meaning': vocab.meaning,
                    'level': vocab.level,
                    'match_type': 'exact'
                }
                exact_words.append(word_data)
            
            response_data = {
                'words': exact_words,
                'total': len(exact_words),
                'query': query,
                'message': f'精准匹配找到 {len(exact_words)} 个单词 🎯',
                'search_time': 'instant'
            }
            
            return HttpResponse(json.dumps(response_data), content_type='application/json')
        
        # 第二步：本地词库模糊匹配
        print("精准匹配未找到，进行本地模糊匹配")
        
        # 构建模糊搜索条件
        fuzzy_conditions = Q()
        for term in search_terms:
            fuzzy_conditions |= (
                Q(word__istartswith=term) |  # 单词开头匹配
                Q(word__icontains=term) |  # 单词包含
                Q(translation__icontains=term) |  # 翻译包含
                Q(meaning__icontains=term)  # 释义包含
            )
        
        # 执行本地模糊搜索
        local_matched_words = []
        vocabularies = Vocabulary.objects.filter(db_query & fuzzy_conditions & Q(is_active=True)).order_by('word')[:10]  # 限制10个本地结果
        
        for vocab in vocabularies:
            # 计算相关度分数
            score = 0
            word = vocab.word.lower()
            translation = vocab.translation.lower()
            meaning = vocab.meaning.lower()
            
            for term in search_terms:
                term = term.lower()
                
                # 单词开头匹配 - 高分
                if word.startswith(term):
                    score += 500
                # 单词包含 - 中等分
                elif term in word:
                    score += 200
                # 翻译包含 - 中等分
                elif term in translation:
                    score += 300
                # 释义包含 - 低分
                elif term in meaning:
                    score += 100
            
            word_data = {
                'word': vocab.word,
                'translation': vocab.translation,
                'meaning': vocab.meaning,
                'level': vocab.level,
                '_score': score,
                'source': 'local'
            }
            local_matched_words.append(word_data)
        
        # 按相关度排序本地结果
        local_matched_words.sort(key=lambda x: (-x['_score'], x['level'], x['word']))
        
        print(f"本地模糊匹配找到 {len(local_matched_words)} 个单词")
        
        # 判断本地搜索是否足够好
        has_good_local_matches = len([w for w in local_matched_words if w['_score'] >= 300]) >= 2
        
        if has_good_local_matches:
            # 本地搜索结果足够好，直接返回
            print("本地搜索结果足够好，直接返回")
            for word_data in local_matched_words:
                word_data.pop('_score', None)
                word_data.pop('source', None)
            
            response_data = {
                'words': local_matched_words,
                'total': len(local_matched_words),
                'query': query,
                'message': f'本地词库找到 {len(local_matched_words)} 个相关单词 📚',
                'search_time': 'fast'
            }
            
            return HttpResponse(json.dumps(response_data), content_type='application/json')
        
        # 第三步：异步API调用补充（避免长时间等待）
        print("本地搜索结果不够好，异步调用API补充")
        
        try:
            # 使用较短的超时时间，快速失败
            import threading
            import time
            
            api_results = {'words': [], 'completed': False, 'error': None}
            
            def api_search_thread():
                try:
                    api_words = []
                    if level in ['all', 'cet4']:
                        cet4_words = get_cet_words_from_api('cet4')
                        if cet4_words:
                            api_words.extend(cet4_words[:1000])  # 限制API数据量
                    if level in ['all', 'cet6']:
                        cet6_words = get_cet_words_from_api('cet6')
                        if cet6_words:
                            api_words.extend(cet6_words[:1000])  # 限制API数据量
                    
                    # API搜索匹配
                    api_matched_words = []
                    for word_data in api_words:
                        word = word_data['word'].lower()
                        translation = word_data['translation'].lower()
                        meaning = word_data['meaning'].lower()
                        
                        score = 0
                        matched = False
                        
                        for term in search_terms:
                            term = term.lower()
                            
                            if word == term:
                                score += 1000
                                matched = True
                            elif word.startswith(term):
                                score += 500
                                matched = True
                            elif term in word:
                                score += 200
                                matched = True
                            elif term in translation:
                                score += 300
                                matched = True
                            elif term in meaning:
                                score += 100
                                matched = True
                        
                        if matched:
                            word_data_with_score = word_data.copy()
                            word_data_with_score['_score'] = score
                            word_data_with_score['source'] = 'api'
                            api_matched_words.append(word_data_with_score)
                    
                    api_results['words'] = api_matched_words
                    api_results['completed'] = True
                    
                except Exception as e:
                    api_results['error'] = str(e)
                    api_results['completed'] = True
            
            # 启动API搜索线程
            api_thread = threading.Thread(target=api_search_thread)
            api_thread.daemon = True
            api_thread.start()
            
            # 等待最多2秒
            api_thread.join(timeout=2.0)
            
            if api_results['completed'] and api_results['words']:
                print(f"API搜索找到 {len(api_results['words'])} 个匹配单词")
                
                # 创建本地单词集合用于去重（不区分大小写）
                local_word_set = {word_data['word'].lower() for word_data in local_matched_words}
                
                # 只添加本地数据库中不存在的API单词
                api_new_words = []
                for api_word in api_results['words']:
                    if api_word['word'].lower() not in local_word_set:
                        api_new_words.append(api_word)
                
                print(f"API新增单词: {len(api_new_words)} 个（跳过重复: {len(api_results['words']) - len(api_new_words)} 个）")
                
                # 合并本地和新的API结果
                all_matched_words = local_matched_words + api_new_words
                
                # 重新排序
                all_matched_words.sort(key=lambda x: (-x['_score'], x['level'], x['word']))
                final_words = all_matched_words[:20]  # 限制20个结果
                
                # 移除分数字段，保留来源信息用于统计
                local_count = 0
                api_count = 0
                for word_data in final_words:
                    word_data.pop('_score', None)
                    if word_data.get('source') == 'api':
                        api_count += 1
                    else:
                        local_count += 1
                    word_data.pop('source', None)  # 移除来源字段
                
                search_message = f'联合搜索找到 {len(final_words)} 个单词 (本地:{local_count} + API新增:{api_count}) 🔍'
                
                response_data = {
                    'words': final_words,
                    'total': len(final_words),
                    'query': query,
                    'message': search_message,
                    'search_time': 'extended'
                }
                
                return HttpResponse(json.dumps(response_data), content_type='application/json')
            
            else:
                # API超时或失败，返回本地结果
                print("API搜索超时或失败，返回本地结果")
                for word_data in local_matched_words:
                    word_data.pop('_score', None)
                    word_data.pop('source', None)
                
                response_data = {
                    'words': local_matched_words,
                    'total': len(local_matched_words),
                    'query': query,
                    'message': f'本地搜索找到 {len(local_matched_words)} 个单词 (API超时) ⚡',
                    'search_time': 'timeout'
                }
                
                return HttpResponse(json.dumps(response_data), content_type='application/json')
                
        except Exception as e:
            print(f"API搜索异常: {e}")
            # 异常情况，返回本地结果
            for word_data in local_matched_words:
                word_data.pop('_score', None)
                word_data.pop('source', None)
            
            response_data = {
                'words': local_matched_words,
                'total': len(local_matched_words),
                'query': query,
                'message': f'本地搜索找到 {len(local_matched_words)} 个单词 (API不可用) 📚',
                'search_time': 'local_only'
            }
            
            return HttpResponse(json.dumps(response_data), content_type='application/json')
    
    return HttpResponse(json.dumps({'error': '无效请求'}), content_type='application/json')