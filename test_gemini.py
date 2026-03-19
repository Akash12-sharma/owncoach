
from config import settings

try:
    resp = settings.supabase.table('user_profiles').select('user_id, name, goal').eq('user_id', '00000000-0000-0000-0000-000000000001').execute()
    print('USER FOUND:', resp.data)
except Exception as e:
    print('USER ERROR:', str(e))

try:
    import google.generativeai as genai
    model = genai.GenerativeModel(model_name='gemini-1.5-flash', system_instruction='You are a fitness coach.')
    chat = model.start_chat(history=[])
    result = chat.send_message('What should I eat to build muscle?')
    print('GEMINI REPLY (first 200 chars):', result.text[:200])
except Exception as e:
    print('GEMINI ERROR:', str(e))

