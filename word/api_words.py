"""
外部API调用模块 - 获取CET单词库
使用免费不需要注册的API，异步并行获取单词和翻译
支持10+个免费翻译API，并行竞速获取最快结果
"""
import requests
from django.core.cache import cache
import concurrent.futures
import time
import hashlib

def format_level(level):
    """格式化级别名称为标准格式"""
    level_lower = level.lower()
    if level_lower == 'cet4' or level_lower == 'cet-4':
        return 'CET-4'
    elif level_lower == 'cet6' or level_lower == 'cet-6':
        return 'CET-6'
    return level.upper()

def get_free_translation(word):
    """使用多个免费API并行获取翻译（不需要注册）- 增强版"""
    
    # 先检查翻译缓存
    cache_key = f"trans_{hashlib.md5(word.lower().encode()).hexdigest()[:8]}"
    cached_trans = cache.get(cache_key)
    if cached_trans:
        return cached_trans
    
    # 检查基础词典（最快）
    basic_trans = get_basic_translation(word)
    if basic_trans:
        return basic_trans
    
    # ========== 免费翻译API列表 ==========
    
    def try_google_free(w):
        """Google翻译免费API - 最稳定"""
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {'client': 'gtx', 'sl': 'en', 'tl': 'zh-CN', 'dt': 't', 'q': w}
            response = requests.get(url, params=params, timeout=2)
            if response.status_code == 200:
                result = response.json()
                if result and result[0] and result[0][0]:
                    trans = result[0][0][0]
                    if trans and trans.lower() != w.lower():
                        return trans
        except:
            pass
        return None
    
    def try_google_free_v2(w):
        """Google翻译免费API - 备用端点"""
        try:
            url = "https://clients5.google.com/translate_a/t"
            params = {'client': 'dict-chrome-ex', 'sl': 'en', 'tl': 'zh-CN', 'q': w}
            response = requests.get(url, params=params, timeout=2)
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], list) and len(result[0]) > 0:
                        trans = result[0][0]
                        if trans and trans.lower() != w.lower():
                            return trans
                    elif isinstance(result[0], str):
                        if result[0].lower() != w.lower():
                            return result[0]
        except:
            pass
        return None
    
    def try_mymemory(w):
        """MyMemory翻译API - 免费，每天1000次"""
        try:
            url = "https://api.mymemory.translated.net/get"
            params = {'q': w, 'langpair': 'en|zh-CN'}
            response = requests.get(url, params=params, timeout=2)
            if response.status_code == 200:
                data = response.json()
                trans = data.get('responseData', {}).get('translatedText', '')
                if trans and trans.lower() != w.lower() and 'MYMEMORY' not in trans.upper():
                    return trans
        except:
            pass
        return None
    
    def try_lingva(w):
        """Lingva翻译API - 开源Google翻译前端"""
        try:
            urls = [
                f"https://lingva.ml/api/v1/en/zh/{w}",
                f"https://lingva.lunar.icu/api/v1/en/zh/{w}",
            ]
            for url in urls:
                try:
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        data = response.json()
                        trans = data.get('translation', '')
                        if trans and trans.lower() != w.lower():
                            return trans
                except:
                    continue
        except:
            pass
        return None
    
    def try_libretranslate(w):
        """LibreTranslate API - 开源翻译"""
        try:
            urls = [
                "https://libretranslate.de/translate",
                "https://translate.argosopentech.com/translate",
                "https://libretranslate.com/translate",
            ]
            for url in urls:
                try:
                    data = {'q': w, 'source': 'en', 'target': 'zh', 'format': 'text'}
                    response = requests.post(url, data=data, timeout=2)
                    if response.status_code == 200:
                        result = response.json()
                        trans = result.get('translatedText', '')
                        if trans and trans.lower() != w.lower():
                            return trans
                except:
                    continue
        except:
            pass
        return None
    
    def try_iciba(w):
        """金山词霸API - 免费词典"""
        try:
            url = "https://dict-co.iciba.com/api/dictionary.php"
            params = {'w': w, 'type': 'json'}
            response = requests.get(url, params=params, timeout=2)
            if response.status_code == 200:
                data = response.json()
                symbols = data.get('symbols', [])
                if symbols:
                    parts = symbols[0].get('parts', [])
                    if parts:
                        means = parts[0].get('means', [])
                        if means:
                            trans = means[0] if isinstance(means[0], str) else str(means[0])
                            if trans and trans.lower() != w.lower():
                                return trans
        except:
            pass
        return None
    
    def try_youdao_free(w):
        """有道词典免费API"""
        try:
            url = f"https://dict.youdao.com/suggest?num=1&doctype=json&q={w}"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                entries = data.get('data', {}).get('entries', [])
                if entries:
                    explain = entries[0].get('explain', '')
                    if explain and explain.lower() != w.lower():
                        return explain
        except:
            pass
        return None
    
    def try_bing_dict(w):
        """必应词典免费API"""
        try:
            url = f"https://cn.bing.com/dict/SerpHoverTrans?q={w}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=2)
            if response.status_code == 200:
                text = response.text
                if text and '<span class="ht_pos">' in text:
                    import re
                    match = re.search(r'<span class="ht_pos">.*?</span>\s*<span>(.*?)</span>', text)
                    if match:
                        trans = match.group(1).strip()
                        if trans and trans.lower() != w.lower():
                            return trans
        except:
            pass
        return None
    
    def try_dict_cn(w):
        """海词词典API"""
        try:
            url = f"https://apii.dict.cn/mini.php?q={w}"
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                text = response.text
                if text and '释义' in text:
                    import re
                    match = re.search(r'<div[^>]*>([^<]+)</div>', text)
                    if match:
                        trans = match.group(1).strip()
                        if trans and len(trans) < 50:
                            return trans
        except:
            pass
        return None
    
    def try_deepl_free(w):
        """DeepL免费API端点"""
        try:
            url = "https://www2.deepl.com/jsonrpc"
            payload = {
                "jsonrpc": "2.0",
                "method": "LMT_handle_jobs",
                "params": {
                    "jobs": [{"kind": "default", "raw_en_sentence": w}],
                    "lang": {"source_lang_computed": "EN", "target_lang": "ZH"},
                    "priority": 1
                },
                "id": 1
            }
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=payload, headers=headers, timeout=2)
            if response.status_code == 200:
                data = response.json()
                translations = data.get('result', {}).get('translations', [])
                if translations:
                    beams = translations[0].get('beams', [])
                    if beams:
                        trans = beams[0].get('postprocessed_sentence', '')
                        if trans and trans.lower() != w.lower():
                            return trans
        except:
            pass
        return None
    
    # 并行调用所有API，取最快返回的结果
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(try_google_free, word),
                executor.submit(try_google_free_v2, word),
                executor.submit(try_mymemory, word),
                executor.submit(try_lingva, word),
                executor.submit(try_libretranslate, word),
                executor.submit(try_iciba, word),
                executor.submit(try_youdao_free, word),
                executor.submit(try_bing_dict, word),
                executor.submit(try_dict_cn, word),
                executor.submit(try_deepl_free, word),
            ]
            
            for future in concurrent.futures.as_completed(futures, timeout=3):
                try:
                    result = future.result(timeout=0.1)
                    if result:
                        # 缓存成功的翻译结果（10分钟）
                        cache.set(cache_key, result, 600)
                        return result
                except:
                    continue
    except:
        pass
    
    return None


def get_batch_translations(words_list):
    """批量获取翻译 - 并行处理多个单词"""
    results = {}
    
    def translate_word(word):
        trans = get_free_translation(word)
        return (word, trans)
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(translate_word, w): w for w in words_list}
            
            for future in concurrent.futures.as_completed(futures, timeout=10):
                try:
                    word, trans = future.result(timeout=0.5)
                    if trans:
                        results[word] = trans
                except:
                    continue
    except:
        pass
    
    return results

def get_cet_words_from_api(level='cet4'):
    """从外部API获取单词库 - 使用免费API，异步并行获取"""
    try:
        cache_key = f"words_{level}_api_v2"
        cached_words = cache.get(cache_key)
        if cached_words:
            print(f"从缓存获取 {format_level(level)} API单词: {len(cached_words)} 个")
            return cached_words
        
        words = []
        formatted_level = format_level(level)
        seen_words = set()
        
        print(f"正在从多个API并行获取{formatted_level}单词...")
        start_time = time.time()
        
        # 使用多个免费单词API并行获取
        def fetch_datamuse(query_url):
            """从DataMuse获取单词"""
            try:
                response = requests.get(query_url, timeout=3)
                if response.status_code == 200:
                    return response.json()
            except:
                pass
            return []
        
        def fetch_random_word_api():
            """从Random Word API获取单词"""
            try:
                url = "https://random-word-api.herokuapp.com/word?number=50"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    return [{'word': w} for w in response.json()]
            except:
                pass
            return []
        
        def fetch_wordnik_random():
            """从Wordnik获取随机单词（免费）"""
            try:
                url = "https://api.wordnik.com/v4/words.json/randomWords?limit=30&minLength=4&maxLength=12"
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    return [{'word': w.get('word', '')} for w in response.json()]
            except:
                pass
            return []
        
        # DataMuse查询列表
        if level == 'cet4':
            datamuse_queries = [
                'https://api.datamuse.com/words?ml=common&max=80',
                'https://api.datamuse.com/words?ml=basic&max=80',
                'https://api.datamuse.com/words?ml=simple&max=60',
                'https://api.datamuse.com/words?ml=important&max=60',
                'https://api.datamuse.com/words?rel_trg=good&max=50',
                'https://api.datamuse.com/words?rel_trg=time&max=50',
                'https://api.datamuse.com/words?rel_trg=work&max=50',
                'https://api.datamuse.com/words?sp=*tion&max=40',
                'https://api.datamuse.com/words?sp=*ment&max=40',
            ]
        else:
            datamuse_queries = [
                'https://api.datamuse.com/words?ml=academic&max=80',
                'https://api.datamuse.com/words?ml=professional&max=80',
                'https://api.datamuse.com/words?ml=sophisticated&max=60',
                'https://api.datamuse.com/words?ml=comprehensive&max=60',
                'https://api.datamuse.com/words?rel_trg=analysis&max=50',
                'https://api.datamuse.com/words?rel_trg=research&max=50',
                'https://api.datamuse.com/words?rel_trg=theory&max=50',
                'https://api.datamuse.com/words?sp=*ology&max=40',
                'https://api.datamuse.com/words?sp=*ization&max=40',
            ]
        
        # 并行获取所有单词列表
        all_raw_words = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(fetch_datamuse, url) for url in datamuse_queries]
            futures.append(executor.submit(fetch_random_word_api))
            futures.append(executor.submit(fetch_wordnik_random))
            
            for future in concurrent.futures.as_completed(futures, timeout=5):
                try:
                    result = future.result(timeout=0.5)
                    if result:
                        all_raw_words.extend(result)
                except:
                    continue
        
        print(f"获取到 {len(all_raw_words)} 个原始单词")
        
        # 过滤和去重单词
        filtered_words = []
        for item in all_raw_words:
            word = item.get('word', '').lower().strip()
            
            if (word and len(word) >= 3 and len(word) <= 15 
                and word.isalpha() and word not in seen_words):
                
                if level == 'cet4' and len(word) > 10:
                    continue
                if level == 'cet6' and len(word) < 4:
                    continue
                
                seen_words.add(word)
                filtered_words.append(word)
                
                if len(filtered_words) >= 200:
                    break
        
        print(f"过滤后 {len(filtered_words)} 个单词，开始并行翻译...")
        
        # 批量并行翻译
        translations = get_batch_translations(filtered_words[:150])
        
        for word in filtered_words:
            if word in translations:
                words.append({
                    'word': word,
                    'translation': translations[word],
                    'meaning': '',
                    'level': formatted_level
                })
        
        elapsed = time.time() - start_time
        print(f"从API获取了 {len(words)} 个{formatted_level}单词，耗时 {elapsed:.1f}秒")
        
        # 添加备用单词
        if len(words) < 50:
            fallback = get_fallback_words(level)
            for fw in fallback:
                if fw['word'].lower() not in seen_words:
                    words.append(fw)
                    seen_words.add(fw['word'].lower())
        
        if words:
            cache.set(cache_key, words, 1800)  # 缓存30分钟
            print(f"最终获取 {len(words)} 个 {formatted_level} 单词")
            return words
            
    except Exception as e:
        print(f"API调用失败: {e}")
    
    return get_fallback_words(level)

def get_basic_translation(word):
    """基础翻译词典 - 常用词快速查询"""
    translations = {
        'hello': '你好', 'world': '世界', 'good': '好的', 'bad': '坏的',
        'yes': '是的', 'no': '不', 'love': '爱', 'like': '喜欢',
        'want': '想要', 'need': '需要', 'know': '知道', 'think': '想',
        'see': '看见', 'look': '看', 'come': '来', 'go': '去',
        'get': '得到', 'make': '制作', 'take': '拿', 'give': '给',
        'put': '放', 'say': '说', 'tell': '告诉', 'ask': '问',
        'work': '工作', 'play': '玩', 'study': '学习', 'learn': '学习',
        'read': '读', 'write': '写', 'listen': '听', 'speak': '说话',
        'eat': '吃', 'drink': '喝', 'sleep': '睡觉', 'walk': '走路',
        'run': '跑', 'stop': '停止', 'start': '开始', 'finish': '完成',
        'open': '打开', 'close': '关闭', 'big': '大的', 'small': '小的',
        'long': '长的', 'short': '短的', 'high': '高的', 'low': '低的',
        'new': '新的', 'old': '老的', 'young': '年轻的', 'hot': '热的',
        'cold': '冷的', 'warm': '温暖的', 'fast': '快的', 'slow': '慢的',
        'easy': '容易的', 'hard': '困难的', 'happy': '快乐的', 'sad': '悲伤的',
        'one': '一', 'two': '二', 'three': '三', 'four': '四', 'five': '五',
        'six': '六', 'seven': '七', 'eight': '八', 'nine': '九', 'ten': '十',
        'the': '这个', 'a': '一个', 'an': '一个', 'and': '和', 'or': '或者',
        'but': '但是', 'in': '在里面', 'on': '在上面', 'at': '在',
        'to': '到', 'for': '为了', 'of': '的', 'with': '和', 'by': '被',
        'from': '从', 'up': '向上', 'about': '关于', 'into': '进入',
        'through': '通过', 'before': '在之前', 'after': '在之后',
        'above': '在上方', 'below': '在下方', 'between': '在之间',
        'i': '我', 'you': '你', 'he': '他', 'she': '她', 'it': '它',
        'we': '我们', 'they': '他们', 'my': '我的', 'your': '你的',
        'be': '是', 'have': '有', 'do': '做', 'will': '将要', 'can': '能够',
        'time': '时间', 'day': '天', 'year': '年', 'people': '人们',
        'way': '方法', 'man': '男人', 'woman': '女人', 'child': '孩子',
        'life': '生活', 'hand': '手', 'part': '部分', 'place': '地方',
        'case': '情况', 'week': '星期', 'company': '公司', 'system': '系统',
        'program': '程序', 'question': '问题', 'government': '政府',
        'number': '数字', 'night': '夜晚', 'point': '点', 'home': '家',
        'water': '水', 'room': '房间', 'mother': '母亲', 'area': '地区',
        'money': '钱', 'story': '故事', 'fact': '事实', 'month': '月',
        'lot': '很多', 'right': '右边', 'book': '书', 'eye': '眼睛',
        'job': '工作', 'word': '单词', 'business': '商业', 'issue': '问题',
        'side': '边', 'kind': '种类', 'head': '头', 'house': '房子',
        'service': '服务', 'friend': '朋友', 'father': '父亲', 'power': '力量',
        'hour': '小时', 'game': '游戏', 'line': '线', 'end': '结束',
        'member': '成员', 'law': '法律', 'car': '汽车', 'city': '城市',
        'community': '社区', 'name': '名字', 'president': '总统',
        'team': '团队', 'minute': '分钟', 'idea': '想法', 'kid': '孩子',
        'body': '身体', 'information': '信息', 'back': '背部', 'parent': '父母',
        'face': '脸', 'level': '水平', 'office': '办公室', 'door': '门',
        'health': '健康', 'art': '艺术', 'war': '战争', 'history': '历史',
        'party': '聚会', 'result': '结果', 'change': '改变', 'morning': '早晨',
        'reason': '原因', 'research': '研究', 'girl': '女孩', 'guy': '家伙',
        'moment': '时刻', 'air': '空气', 'teacher': '教师', 'force': '力量',
        'education': '教育', 'foot': '脚', 'boy': '男孩', 'age': '年龄',
        'policy': '政策', 'process': '过程', 'music': '音乐', 'market': '市场',
        'sense': '感觉', 'nation': '国家', 'plan': '计划', 'college': '大学',
        'interest': '兴趣', 'death': '死亡', 'experience': '经验', 'effect': '效果',
        'use': '使用', 'class': '班级', 'control': '控制', 'care': '关心',
        'field': '领域', 'development': '发展', 'role': '角色', 'effort': '努力',
        'rate': '比率', 'heart': '心', 'drug': '药物', 'show': '展示',
        'leader': '领导', 'light': '光', 'voice': '声音', 'wife': '妻子',
        'police': '警察', 'mind': '思想', 'difference': '差异', 'wall': '墙',
        'paper': '纸', 'need': '需要', 'building': '建筑', 'action': '行动',
        'international': '国际的', 'continue': '继续', 'center': '中心',
        'social': '社会的', 'decision': '决定', 'public': '公共的',
        'necessary': '必要的', 'political': '政治的', 'possible': '可能的',
        'national': '国家的', 'economic': '经济的', 'important': '重要的',
        'different': '不同的', 'local': '当地的', 'available': '可用的',
        'likely': '可能的', 'military': '军事的', 'federal': '联邦的',
        'true': '真的', 'whole': '整个的', 'special': '特殊的', 'free': '自由的',
        'strong': '强壮的', 'human': '人类的', 'clear': '清楚的', 'real': '真实的',
        'simple': '简单的', 'recent': '最近的', 'certain': '确定的',
        'personal': '个人的', 'major': '主要的', 'financial': '金融的',
        'full': '满的', 'serious': '严肃的', 'common': '普通的', 'current': '当前的',
        'natural': '自然的', 'significant': '重要的', 'similar': '相似的',
        'medical': '医学的', 'traditional': '传统的', 'popular': '流行的',
    }
    return translations.get(word.lower())

def get_fallback_words(level='cet4'):
    """备用单词库"""
    if level == 'cet4':
        return [
            {'word': 'hello', 'translation': '你好', 'meaning': '', 'level': 'CET-4'},
            {'word': 'world', 'translation': '世界', 'meaning': '', 'level': 'CET-4'},
            {'word': 'good', 'translation': '好的', 'meaning': '', 'level': 'CET-4'},
            {'word': 'time', 'translation': '时间', 'meaning': '', 'level': 'CET-4'},
            {'word': 'people', 'translation': '人们', 'meaning': '', 'level': 'CET-4'},
            {'word': 'work', 'translation': '工作', 'meaning': '', 'level': 'CET-4'},
            {'word': 'life', 'translation': '生活', 'meaning': '', 'level': 'CET-4'},
            {'word': 'day', 'translation': '天', 'meaning': '', 'level': 'CET-4'},
            {'word': 'way', 'translation': '方法', 'meaning': '', 'level': 'CET-4'},
            {'word': 'thing', 'translation': '事情', 'meaning': '', 'level': 'CET-4'},
            {'word': 'man', 'translation': '男人', 'meaning': '', 'level': 'CET-4'},
            {'word': 'woman', 'translation': '女人', 'meaning': '', 'level': 'CET-4'},
            {'word': 'child', 'translation': '孩子', 'meaning': '', 'level': 'CET-4'},
            {'word': 'year', 'translation': '年', 'meaning': '', 'level': 'CET-4'},
            {'word': 'government', 'translation': '政府', 'meaning': '', 'level': 'CET-4'},
        ]
    else:
        return [
            {'word': 'abandon', 'translation': '放弃', 'meaning': '', 'level': 'CET-6'},
            {'word': 'abstract', 'translation': '抽象的', 'meaning': '', 'level': 'CET-6'},
            {'word': 'academic', 'translation': '学术的', 'meaning': '', 'level': 'CET-6'},
            {'word': 'accelerate', 'translation': '加速', 'meaning': '', 'level': 'CET-6'},
            {'word': 'accomplish', 'translation': '完成', 'meaning': '', 'level': 'CET-6'},
            {'word': 'accumulate', 'translation': '积累', 'meaning': '', 'level': 'CET-6'},
            {'word': 'accurate', 'translation': '准确的', 'meaning': '', 'level': 'CET-6'},
            {'word': 'achieve', 'translation': '实现', 'meaning': '', 'level': 'CET-6'},
            {'word': 'acknowledge', 'translation': '承认', 'meaning': '', 'level': 'CET-6'},
            {'word': 'acquire', 'translation': '获得', 'meaning': '', 'level': 'CET-6'},
            {'word': 'adequate', 'translation': '足够的', 'meaning': '', 'level': 'CET-6'},
            {'word': 'advocate', 'translation': '提倡', 'meaning': '', 'level': 'CET-6'},
            {'word': 'aesthetic', 'translation': '美学的', 'meaning': '', 'level': 'CET-6'},
            {'word': 'aggregate', 'translation': '聚合', 'meaning': '', 'level': 'CET-6'},
            {'word': 'allocate', 'translation': '分配', 'meaning': '', 'level': 'CET-6'},
        ]
