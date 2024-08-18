import time
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict, Any, Optional

URL = ''
KEY = ''

MAX_WORKERS = 3  # 默认最大线程数
TIME_OUT = 15  # 默认超时时间
INTERVAL = 0  # 默认间隔时间
OPEN_WEBUI = False  # 默认不使用 Open WebUI
ONLY_OPENAI = True  # 仅测试 OPENAI 模型

models_path = '/v1/models' if not OPEN_WEBUI else '/api/models'
chat_path = '/v1/chat/completions' if not OPEN_WEBUI else '/api/chat/completions'

OPENAI_MODELS = ['gpt-3.5-turbo', 'gpt-3.5-turbo-0301', 'gpt-3.5-turbo-0613', 'gpt-3.5-turbo-1106',
                 'gpt-3.5-turbo-0125', 'gpt-3.5-turbo-16k', 'gpt-3.5-turbo-16k-0613', 'gpt-3.5-turbo-instruct', 'gpt-4',
                 'gpt-4-0314', 'gpt-4-0613', 'gpt-4-1106-preview', 'gpt-4-0125-preview', 'gpt-4-32k', 'gpt-4-32k-0314',
                 'gpt-4o-2024-08-06', 'gpt-4-32k-0613', 'gpt-4-turbo-preview', 'gpt-4-turbo', 'gpt-4-turbo-2024-04-09',
                 'gpt-4o', 'gpt-4o-2024-05-13', 'gpt-4o-mini', 'gpt-4o-mini-2024-07-18', 'gpt-4-vision-preview',
                 'text-embedding-ada-002', 'text-embedding-3-small', 'text-embedding-3-large', 'text-curie-001',
                 'text-babbage-001', 'text-ada-001', 'text-davinci-002', 'text-davinci-003', 'text-moderation-latest',
                 'text-moderation-stable', 'text-davinci-edit-001', 'davinci-002', 'babbage-002', 'dall-e-2',
                 'dall-e-3', 'whisper-1', 'tts-1', 'tts-1-1106', 'tts-1-hd', 'tts-1-hd-1106']

# 颜色常量
RED = "\033[91m"
GREEN = "\033[92m"
ORANGE = "\033[38;5;208m"
GRAY = "\033[37m"
RESET = "\033[0m"


def fetch_models(url: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
    """获取模型列表"""
    try:
        response = requests.get(f"{url}{models_path}", headers=headers, timeout=TIME_OUT)
        response.raise_for_status()
        return response.json().get('data', [])
    except requests.RequestException as e:
        print(f"{RED}Failed to get models: {e}{RESET}")
        return []


def check_model(model: str, url: str, headers: Dict[str, str], data: Dict[str, Any]) -> Tuple[
    str, bool, Optional[str], Optional[float]]:
    """检查单个模型的可用性并计算延迟，带有超时处理"""
    result = {"model": model, "is_available": False, "error": None, "latency": None}

    def model_check():
        nonlocal result
        try:
            data['model'] = model
            start_time = time.time()
            response = requests.post(f"{url}{chat_path}", headers=headers, json=data, timeout=TIME_OUT)
            response.raise_for_status()
            latency = time.time() - start_time
            response_data = response.json()
            if 'error' in response_data:
                result = {"model": model, "is_available": False, "error": response_data['error'], "latency": latency}
            else:
                result = {"model": model, "is_available": True, "error": None, "latency": latency}
        except requests.RequestException as e:
            result = {"model": model, "is_available": False, "error": str(e), "latency": None}

    thread = threading.Thread(target=model_check)
    thread.start()
    thread.join(timeout=TIME_OUT)

    if thread.is_alive():
        return model, False, "Timeout", None

    return result["model"], result["is_available"], result["error"], result["latency"]


def display_result(model: str, is_available: bool, error: Optional[str], latency: Optional[float]) -> None:
    """显示检查结果"""
    if is_available and latency is not None:
        color = GREEN if latency < 4 else (ORANGE if latency < 6 else RED)
        print(f"{color}[{latency:.2f}s]{RESET} {model}")
    else:
        if error == "Timeout":
            print(f"{GRAY}[TIMEOUT]{RESET} {model}")
        else:
            print(f"{RED}[X]{RESET} {model} - {RED}{error or 'Unknown error'}{RESET}")


def check_models_concurrently(models: List[str], url: str, headers: Dict[str, str], data: Dict[str, Any],
                              max_workers: int = 1, interval: float = 0) -> Tuple[List[str], List[str], List[str]]:
    """并行检查多个模型的可用性，包含超时处理和间隔"""
    check_passes, check_failed, check_timeout = [], [], []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(check_model, model, url, headers, data): model for model in models}
        for future in as_completed(futures):
            model, is_available, error, latency = future.result()
            display_result(model, is_available, error, latency)
            if is_available:
                check_passes.append(model)
            elif error == "Timeout":
                check_timeout.append(model)
            else:
                check_failed.append(model)

            time.sleep(interval)

    return check_passes, check_failed, check_timeout


def main():
    headers = {
        'Authorization': f'Bearer {KEY}',
        'Content-Type': 'application/json'
    }
    data = {
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1
    }
    models = fetch_models(URL, headers) if ONLY_OPENAI else OPENAI_MODELS
    model_ids = [model['id'] for model in models]

    print('Start checking...')
    print('------------------')

    start_time = time.time()

    available_models, failed_models, timeout_models = check_models_concurrently(
        model_ids, URL, headers, data, MAX_WORKERS, INTERVAL
    )

    total_time = time.time() - start_time

    print('------------------')
    print(f'Available: {len(available_models)}')
    print(f'Failed: {len(failed_models)}')
    print(f'Timeout: {len(timeout_models)}')
    print(f"Total time: {total_time:.2f}s")
    print('------------------')
    print('Available models: ')
    print(', '.join(available_models))
    print('------------------')
    print('Timeout models: ')
    print(', '.join(timeout_models))


if __name__ == "__main__":
    main()
