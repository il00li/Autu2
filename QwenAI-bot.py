import telebot,requests,re,html,tempfile,os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from telebot.types import InlineKeyboardMarkup,InlineKeyboardButton,Message
love=telebot.TeleBot("8461163944:AAG692d6NA-4h0O--5GRr9gHEjKNr1P4p1k") # Token
QWEN="https://sii3.moayman.top/api/qwen.php" # API
MODEL="qwen3-coder-plus" # MODEL
SYSTEM_PROMPT=r"""You are QwenAI, a friendly and helpful assistant who can program when needed. Focus on having a natural conversation with the user, responding politely and in a friendly tone. Only provide programming help or code when the user specifically asks for it, and follow their instructions exactly. Do not repeat messages unnecessarily. Avoid multiple greetings—welcome the user only the first time. If the user asks something unclear or says they didn’t understand, explain clearly based on the context. Remember the ongoing conversation and what the user writes."""  # prompt
conversation_context={}
def ask_ai(uid,text):
 try:
  h=conversation_context.get(uid,[])[:]
  h.append({"role":"user","content":text})
  lf=any(len(m['content'])>1000 or "```" in m['content'] for m in h)
  k=len(h)//2 if lf else 10
  if k<2:k=2
  h=h[-k:]
  mt="\n".join([f"{m['role']}: {m['content']}" for m in h])
  p=f"{SYSTEM_PROMPT}\n\n{mt}"
  r=requests.post(QWEN,data={"prompt":p,"model":MODEL},timeout=None).json().get("response","Error")
  h.append({"role":"assistant","content":r})
  lf=any(len(m['content'])>1000 or "```" in m['content'] for m in h)
  k=len(h)//2 if lf else 10
  if k<2:k=2
  conversation_context[uid]=h[-k:]
  return r
 except:return"Error"
def markdown_to_html(t):
 t=html.escape(t)
 t=re.sub(r'```(.*?)```',r'<pre>\1</pre>',t,flags=re.DOTALL)
 t=re.sub(r'`(.*?)`',r'<code>\1</code>',t)
 t=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',t)
 t=re.sub(r'\*(.*?)\*',r'<i>\1</i>',t)
 t=re.sub(r'__(.*?)__',r'<u>\1</u>',t)
 return t
def extract_image(url):
 try:
  if any(url.lower().endswith(ext) for ext in [".jpg",".jpeg",".png",".webp"]):return url
  h={"User-Agent":"Mozilla/5.0"}
  r=requests.get(url,headers=h)
  if r.status_code!=200:return None
  s=BeautifulSoup(r.text,"html.parser")
  for t in ["og:image","twitter:image"]:
   i=s.find("meta",property=t)
   if i and i.get("content"):return i["content"]
  i=s.find("img")
  if i and i.get("src"):return urljoin(url,i["src"])
 except:return None
@love.message_handler(commands=['start'])
def start_message(m:Message):
 t="""<b>Hi! im QwenAI 👋🏻</b>\n<b><blockquote>im here to help you with anything you need from coding tasks to general questions</blockquote></b>\n<b><u>What do you want to do today?</u></b>"""
 img=extract_image("https://pin.it/7u2ab6KnH")  # link image /start
 k=InlineKeyboardMarkup()
 k.add(InlineKeyboardButton("Select model",callback_data="select_model"))
 if img:love.send_photo(m.chat.id,photo=img,caption=t,parse_mode="HTML",reply_markup=k,has_spoiler=True)
 else:love.send_message(m.chat.id,t,parse_mode="HTML",reply_markup=k)
@love.callback_query_handler(func=lambda c:True)
def callback(c):
 global MODEL
 if c.data=="select_model":
  try:
   r=requests.get(QWEN,timeout=10).json()
   ms=r.get("models",[])
   mk=InlineKeyboardMarkup(row_width=2)
   for i in range(0,len(ms),2):
    row=[InlineKeyboardButton(ms[i],callback_data=f"model_{ms[i]}")]
    if i+1<len(ms):row.append(InlineKeyboardButton(ms[i+1],callback_data=f"model_{ms[i+1]}"))
    mk.add(*row)
   mk.add(InlineKeyboardButton("Back",callback_data="back"))
   love.edit_message_reply_markup(c.message.chat.id,c.message.message_id,reply_markup=mk)
  except:pass
 elif c.data=="back":
  k=InlineKeyboardMarkup()
  k.add(InlineKeyboardButton("Select model",callback_data="select_model"))
  love.edit_message_reply_markup(c.message.chat.id,c.message.message_id,reply_markup=k)
 elif c.data.startswith("model_"):
  MODEL=c.data[6:]
  k=InlineKeyboardMarkup()
  k.add(InlineKeyboardButton("Select model",callback_data="select_model"))
  love.edit_message_reply_markup(c.message.chat.id,c.message.message_id,reply_markup=k)
  love.answer_callback_query(c.id,text=f"Model set to {MODEL}")
@love.message_handler(func=lambda m:True)
def chat(m:Message):
 love.send_chat_action(m.chat.id,"typing")
 r=ask_ai(m.from_user.id,m.text)
 p=re.compile(r'```(\w+)?\n(.*?)```',re.DOTALL)
 ms=p.findall(r)
 if ms:
  c=re.sub(r'```(\w+)?\n(.*?)```',"",r,flags=re.DOTALL).strip()
  c=(c[:1000]+"...") if len(c)>1000 else (c if c!="" else " ")
  sent=False
  for idx,(l,code) in enumerate(ms,1):
   code=code.rstrip("\n")
   ext=".txt"
   if l:
    ll=l.lower()
    if ll in ("python","py"):ext=".py"
    elif ll in ("javascript","js","node"):ext=".js"
    elif ll in ("java",):ext=".java"
    elif ll in ("c++","cpp"):ext=".cpp"
    elif ll in ("c#","csharp"):ext=".cs"
    elif ll in ("php",):ext=".php"
    elif ll in ("html",):ext=".html"
    elif ll in ("css",):ext=".css"
    elif ll in ("json",):ext=".json"
    elif ll in ("bash","sh"):ext=".sh"
   else:
    fl=code.splitlines()[0].lower() if code.splitlines() else ""
    if "function" in fl or "console.log" in fl or "var " in fl:ext=".js"
    elif fl.strip().startswith("<"):ext=".html"
   fp=os.path.join(tempfile.gettempdir(),f"code_{idx}{ext}")
   with open(fp,"w",encoding="utf-8") as f:f.write(code)
   love.send_document(m.chat.id,open(fp,"rb"),caption=c if not sent else " ")
   try:os.remove(fp)
   except:pass
   sent=True
  return
 love.send_message(m.chat.id,markdown_to_html(r),parse_mode="HTML")
love.polling()